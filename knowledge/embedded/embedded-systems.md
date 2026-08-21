---
id: systems-embedded-sensor-fusion
domain: systems
title: Embedded Systems — A Sensor-Fusion MCU Pipeline 感測器融合韌體管線
tags: [embedded, firmware, rtos, c, cpp, real-time]
mastery: 0
source: Notion — "Embedded System" (2026-04)
visibility: private
---

一份圍繞**一個具體專案**的嵌入式筆記：一顆 MCU 同時收 1000Hz IMU 與相機事件，
做時間對齊後批次送給 AP。整個系統從「低階 C 記憶體語意」一路到「多處理器感測器融合」，
下面用 6 個角度拆開，每個都是「概念 → 為什麼 → 程式碼」。

---

## 1. Memory Management & Hardware Constraints 記憶體與硬體限制

**Static vs. Dynamic Allocation（`static` vs. `malloc`/`new`）**
在硬即時（hard real-time）系統裡，動態配置基本上是禁止的。`malloc` 會造成 **heap fragmentation**、
潛在 memory leak，以及**執行時間不確定（jitter）**。改用 `static` 實體化，編譯器在編譯期就把記憶體
劃在 `.bss`／`.data` 區段，換來 **100% 確定的記憶體足跡**、零 OOM 風險。

**Function-scoped `static`（狀態快取）**
函式內的 `static` 變數同時有兩個好處：像全域變數一樣**跨呼叫保留值**，又保有區域變數的封裝，
避免 **namespace pollution**。

```cpp
// 宣告具體物件，記憶體在編譯期就分配在 .bss/.data 區段
static Imu_Bosch_BMI270      system_imu(PIN_SPI_CS);
static Camera_Strobe_VirtualSensor system_camera;

// 建立抽象指標陣列，達成多型與依賴反轉（見 §2）
ISensor* active_sensors[2] = { &system_imu, &system_camera };
```

---

## 2. Object-Oriented Architecture in Embedded C++ 嵌入式 C++ 的物件導向架構

**Dependency Inversion & Extensibility（依賴反轉與可擴充）**
核心框架（`SensorReaderTask`）只跟一排抽象的 `ISensor*` 打交道，完全跟硬體細節（SPI/I2C/GPIO）解耦。
這滿足 **Open-Closed Principle**：加一顆新感測器**不用動核心管線**，只要實體化一個新 driver、
把指標塞進註冊陣列即可。

**Dynamic Dispatch vs. Switch-Cases（動態分派取代 switch）**
用 `active_sensors[id]->readRawData()` 取代寫死的 `if-else`／`switch` 判斷感測器型別——
新增型別時不必回頭改一長串條件分支。

---

## 3. Real-Time OS (RTOS) Mechanics 即時作業系統機制

**Blocking vs. Non-blocking API（阻塞 vs. 非阻塞，這是硬即時的核心紀律）**

| 角色 | 用哪種 API | 佇列滿了怎麼辦 | 為什麼 |
|---|---|---|---|
| **Producer / ISR**（`SensorReaderTask`、硬體中斷） | **非阻塞**（timeout = 0） | 丟掉 payload、回報錯誤、立刻往下走 | 守住 hard real-time deadline，絕不能卡住 |
| **Consumer**（`IPC_Task`、`Telemetry_Task`） | **阻塞**（timeout = `portMAX_DELAY`） | 進入 suspend、讓出 CPU | 省電、避免 busy-waiting |

**Lock-Free SPSC Ring Buffer（免鎖的單生產者單消費者環形緩衝）**
head/tail 用 `volatile`，索引環繞用位元遮罩 `& (SIZE - 1)` 取代耗時的模除 `%`——
單生產單消費時，head 和 tail 各自只有一方會改，所以**免鎖**。

```cpp
// push 內部：用 & (BUFFER_SIZE - 1) 環繞（BUFFER_SIZE 必須是 2 的冪）
uint32_t next_head = (head + 1) & (BUFFER_SIZE - 1);

// 消費端：一定要檢查 push 回傳值，overflow 就丟給 telemetry
if (g_sensor_buffer.push(outgoing_event)) {
    TelemetryEvent error = { /* ... */ ERR_BUFFER_OVERFLOW };
    RTOS_QueueSend_NonBlocking(TelemetryQueue, &error);
}
```

**ISR 只設事件、把重活丟給任務**
中斷服務常式（ISR）裡只做最少的事——取共同時間戳、把事件推進 RTOS 佇列，馬上返回。

```cpp
void Camera_Exposure_ISR() {
    WakeupEvent event;
    event.sensor_id    = SENSOR_CAMERA_STROBE;
    event.timestamp_us = HW_Timer_GetMicroseconds();   // 與 IMU 同一個時間基準
    RTOS_QueueSendFromISR(ReaderTaskQueue, &event);    // 在 ISR 裡用 FromISR 版本
}
```

---

## 4. System-Level Architecture & Sensor Fusion 系統級架構與感測器融合

**Microsecond Time-Sync for SLAM（微秒級時間同步——這是整個系統的皇冠）**
MCU **不搬影像像素**（MIPI 直接把大頻寬資料送到 AP 的 DSP），MCU 只提供一個**共同時間基準**。
做法：把相機的實體 **hardware strobe pin** 接到 MCU 的 GPIO 中斷，MCU 用**跟 IMU 同一顆硬體計時器**
在快門開啟的那一微秒打上時間戳，再把這個「virtual frame marker」注入 IMU 資料流——
AP 就能把視覺特徵和運動學完美對齊，達成 **zero-jitter** 追蹤。

**Out-of-Band Signaling（把重資料路徑和關鍵時序路徑分開）**
重資料走 Camera → MIPI → AP；關鍵時序走 Camera → GPIO strobe → MCU。兩條路分開，時序不被大流量拖累。

**Power Optimization via Batching / Watermarks（用批次與水位省電）**
MCU 把 1000Hz 的高頻 IMU 樣本累積在 ring buffer，只有到達 **FIFO watermark**（例如 11 筆）
才透過專屬 GPIO 叫醒 AP，而不是每筆都吵醒它。

```cpp
// 達到 V-Sync 要求的門檻才非同步通知 consumer，避免阻塞 1000Hz 迴圈
if (g_sensor_buffer.getUnreadCount() >= FIFO_WATERMARK) {
    RTOS_GiveSemaphore(Wakeup_AP_IPC_Semaphore);
}
```

**Ping-Pong (Double Buffer) DMA（雙緩衝 DMA）**
兩塊實體緩衝：一塊正在被寫入（`write_ptr`），另一塊正被 DMA 送出（`dma_ptr`）。集滿一批就交換兩個指標、
啟動 DMA，寫入端立刻可以繼續填另一塊，不必等傳輸完成。DMA 完成中斷只做一件事：把 `dma_is_busy` 清掉。

```cpp
if (current_write_index >= BATCH_SIZE && !dma_is_busy) {
    dma_is_busy = true;
    SensorEvent* temp = write_ptr;   // ping-pong swap
    write_ptr = dma_ptr;
    dma_ptr   = temp;
    DMA_Start_SPI_Transfer(dma_ptr, BATCH_SIZE);
    current_write_index = 0;
}
// DMA 完成 ISR：極簡但極重要
void DMA_Tx_Complete_ISR() { dma_is_busy = false; }
```

---

## 5. Fault Tolerance & Observability「黑盒子」容錯與可觀測性

**Asynchronous Logging（非同步日誌／事後除錯）**
寫非揮發性記憶體（SPI Flash）非常慢，高優先權任務**絕不能直接寫 Flash**。它們只推一個輕量的
`TelemetryEvent` 進佇列，由**最低優先權**的 `Telemetry_Task` 負責真正的 I/O。

**Wear Leveling & RAM Buffering（磨損平均與批次沖刷）**
Flash 以 **page**（例如 256 bytes）為單位寫、壽命有限。`Telemetry_Task` 先在 RAM buffer 累積，
對齊 page 邊界才寫進 Flash。

**Emergency Flush（緊急沖刷）**
遇到 `LOG_FATAL`：無視批次上限、立刻強制寫 Flash，再觸發 watchdog reset，把當機現場保留給工程分析。

```cpp
flash_buffer[buffer_count++] = log_event;
// 致命錯誤，或 RAM buffer 滿了 → 強制沖刷
if (log_event.level == LOG_FATAL || buffer_count >= BUFFER_SIZE) {
    Flash_WritePage(flash_buffer, buffer_count);
    if (log_event.level == LOG_FATAL) System_TriggerWatchdogReset();
}
```

**Software Watchdog（用 bitmask 收各任務簽到）**
一個最高優先權的 monitor task，用一個 bitmask 收集各任務的「簽到」。所有任務都簽到才餵硬體看門狗；
少了誰就觸發重啟。簽到寫入是多任務共享狀態，要進 critical section 防 race condition。

```cpp
static uint32_t checkin_mask = 0;
const uint32_t ALL_TASKS_MASK = (1 << MAX_TASKS) - 1;

void System_Health_CheckIn(TaskID id) {
    taskENTER_CRITICAL();
    checkin_mask |= (1 << id);      // 共享狀態 → 進臨界區
    taskEXIT_CRITICAL();
}
// monitor：讀完就清零，全簽到才餵狗，否則回報是誰卡住
```

---

## 6. C/C++ Specific Pitfalls C/C++ 專屬陷阱

**The Pointer `sizeof` Trap（指標的 sizeof 陷阱）**
對「以指標形式傳進來的陣列」用 `sizeof(buffer)`，只會拿到**位址大小**（4 或 8 bytes），
不是資料量。要明確算 `element_count * sizeof(Struct)`。

**Zero-Copy Pointer Casting（零複製指標轉型）**
把結構化 payload 陣列指標直接 `(uint8_t*)` 轉成原始 byte 指標交給 DMA/SPI 送出，
省掉多餘的 `memcpy` 迴圈。

```cpp
uint32_t total_bytes = popped_count * sizeof(SensorEvent);   // 不是 sizeof(buffer)！
SPI_Transmit_To_Ap((uint8_t*)local_buffer, total_bytes);     // zero-copy 轉型
```

---

## 附錄 · Thread-Safe LRU Cache（同一份筆記裡的經典題）

`std::list<pair>` 存資料、`unordered_map` 存 list 的 iterator 達成 O(1) 尋找；
命中時用 `list::splice` 把節點 O(1) 搬到最前面。**陷阱**：`get()` 也會改動 list，
所以連讀取都要用**排他鎖**，不能用讀寫鎖的讀鎖。

```cpp
bool get(int key, int& out_value) {
    std::lock_guard<std::mutex> lock(m_lock);   // get 也改 list → 排他鎖
    auto it = cache_map.find(key);
    if (it == cache_map.end()) return false;    // miss
    lru_list.splice(lru_list.begin(), lru_list, it->second);  // O(1) 搬到最前
    out_value = it->second->second;
    return true;
}
```

---

## Recall prompt

> 1. 為什麼 hard real-time 系統禁止 `malloc`？`static` 換到的是什麼保證？
> 2. SPSC ring buffer 為什麼能免鎖？`& (SIZE-1)` 取代了什麼、前提是什麼？
> 3. Producer/ISR 和 Consumer 分別該用阻塞還是非阻塞 API？為什麼？
> 4. 相機和 IMU 怎麼做到微秒級對齊——MCU 到底搬不搬像素？
> 5. 高優先權任務為什麼不能直接寫 Flash？黑盒子怎麼繞過這件事？

相關：[[mutex-spinlock-semaphore]] · [[race-condition]] · [[deadlock]] · [[memory-leak]]
