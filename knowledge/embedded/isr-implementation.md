---
id: embedded-isr-implementation
domain: systems
title: ISR 實作 — 怎麼真的寫出一個中斷處理常式
tags: [embedded, isr, interrupt, firmware, mcu]
mastery: 0
source:
visibility: private
---

## Idea

**IRQ = 硬體發出的訊號（「鈴響了」）；ISR = 妳寫的處理函式（「去開門」）。**

概念不難，難的是實作細節 —— 尤其**清中斷旗標**，忘了就無限重入、系統卡死。
這份講的是「怎麼真的寫出一個 ISR」。

---

## 1 · 框架版 vs 真實硬體版

面試題常給一個包裝過的 API：

```c
int timer_isr(void* data) { ... }              // 有參數、有回傳值
set_irq_handler(31, timer_isr, NULL);          // 用函式登記
```

真實硬體上沒有這麼好的事：

```c
void TIM2_IRQHandler(void) { ... }             // 沒參數、沒回傳值、名字不能亂取
```

| | 框架版 | 真實硬體版 |
|---|---|---|
| **怎麼登記** | 呼叫 `set_irq_handler()` | **名字對上中斷向量表**就自動生效 |
| **參數** | 有 `void* data` | ❌ 沒有 —— 硬體無法傳參數 |
| **回傳值** | 有 `int` | ❌ 沒有 —— 沒人接 |
| **清旗標** | 框架幫妳做了 | ⚠️ **妳自己要做** |

> 所以框架版的 handler 其實是**第二層** —— 底層有一個真正的 ISR 幫妳清旗標、
> 查表取出 `data`，再呼叫妳登記的普通函式。

---

## 2 · 中斷向量表：名字為什麼不能亂取

記憶體開頭有一張表，第 N 格存「IRQ N 發生時跳到哪個位址」：

```
向量表
┌────┬────────────────────┐
│  0 │ 堆疊起始位址         │
│  1 │ Reset_Handler      │ ← 開機跳這裡
│ ⋮  │        ⋮           │
│ 28 │ TIM2_IRQHandler    │ ← 名字必須完全對上
│ 37 │ USART1_IRQHandler  │
└────┴────────────────────┘
```

原廠的啟動檔（`startup.s`）已經把這些名字填進表裡，而且宣告成 **weak symbol**：

```c
void TIM2_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
```

意思是「**預設指向一個空的處理常式；但如果妳自己定義了同名函式，就用妳的**」。

**所以妳只要寫一個叫 `TIM2_IRQHandler` 的函式，它就自動被掛上去** ——
不用註冊，但⚠️ **名字打錯一個字母就完全不會被呼叫，而且編譯不報錯**，極難除錯。

---

## 3 · ⭐ 通用骨架（所有 ISR 都長這樣）

```c
void XXX_IRQHandler(void) {
    // ① 確認來源（一條 IRQ 可能對應多個事件）
    if (!(PERIPH->SR & FLAG)) return;

    // ② 清中斷旗標 ← 忘了會無限重入
    PERIPH->SR = FLAG;

    // ③ 做最短的事：搬資料 / 設旗標

    // ④ 通知 bottom half
}
```

### ① 為什麼要確認來源

一條 IRQ 常對應**多個事件**。例如 UART 的中斷可能是「收到資料」也可能是「送完了」，
共用同一條 IRQ 線 —— 所以要先讀狀態暫存器判斷是哪一個。

### ⚠️ ② 清旗標 —— 最容易忘、後果最嚴重

硬體觸發中斷時會**豎起一個旗標**。ISR 返回時中斷控制器會看那個旗標：

```
旗標還在 → 「還有事沒處理完」→ 立刻再進 ISR 一次
        → 又沒清 → 又進來 → 無限迴圈 → 系統卡死
```

**症狀：程式看起來完全停住，主迴圈一行都跑不到。**

而且**通常是 write-1-to-clear**：

```c
PERIPH->SR = FLAG;          // ✅ 只寫要清的那一位
PERIPH->SR |= FLAG;         // ❌ read-modify-write！讀到的其他 1 會被寫回去，
                            //    連帶清掉別的旗標
```

### 兩種清旗標的機制

| 機制 | 怎麼清 | 例子 |
|---|---|---|
| **W1C（寫 1 清除）** | 明確寫入 `SR = FLAG` | Timer 的 update flag |
| **讀取即清除** | **讀資料暫存器就自動清掉** | UART 的 RXNE ← 讀 `DR` 就清了 |

第二種要特別小心：**「讀」本身有副作用**，不能隨便多讀一次，也不能讓編譯器優化掉
（`volatile` 的深層理由）。

---

## 4 · 場景一：Timer（週期性做一件小事）

```c
volatile uint32_t g_ticks = 0;      // ISR 會改 → 一定要 volatile

void TIM2_IRQHandler(void) {
    if (!(TIM2->SR & TIM_SR_UIF)) return;   // ① 確認是更新事件
    TIM2->SR = ~TIM_SR_UIF;                  // ② 清旗標（W1C）
    g_ticks++;                               // ③ 最短的事
}
```

**三個設計點：**
1. `g_ticks` 一定要 `volatile` —— 主程式讀它時編譯器不能快取
2. ISR 裡只有一個 `++` —— 沒有 `printf`、沒有計算，符合三戒
3. 不需要 re-arm —— timer 設成 auto-reload 的話硬體自己重載

⚠️ 如果 `g_ticks` 是 64-bit 而 CPU 是 32-bit，**讀取不是原子操作** ——
可能讀到一半被 ISR 打斷造成高低位不一致。要關中斷讀，或用「讀兩次比對」。

---

## 5 · 場景二：UART 接收 ✍️ 填空

**情境**：UART 每收到一個 byte 就觸發中斷，要把它存進 ring buffer，主程式之後再處理。

**已知：**
- 狀態暫存器 `USART1->SR`，收到資料的旗標是 `USART_SR_RXNE`
- 資料暫存器 `USART1->DR`，**讀它就會自動清掉 RXNE 旗標**
- ring buffer 已經有了：`int rb_push(uint8_t c);`（滿了回傳 0）

```c
volatile uint32_t g_rx_overflow = 0;

void USART1_IRQHandler(void) {
    if (!(USART1->SR & USART_SR_RXNE)) return;   // ① 確認是「收到資料」

    uint8_t c = USART1->DR;                       // ② 讀走 → 旗標自動清除

    if (!rb_push(c)) {                            // ③ 滿了：只記錄，不做重事
        g_rx_overflow++;                          //    絕不能在這裡 printf 或阻塞等
    }
}
```

**1. 清旗標機制不同**
Timer 是 **W1C**（要明確寫 `SR = FLAG`）；UART 的 RXNE 是**讀 `DR` 就自動清**。
所以這裡沒有「清旗標」那一行 —— 讀取動作本身就完成了。

**2. 為什麼要立刻讀走**
UART 的接收暫存器只有一格（或很淺的 FIFO）。下一個 byte 到達時若前一個還沒被讀走，
就會發生 **overrun**，舊資料被覆蓋、資料永久遺失。

**3. ring buffer 滿了怎麼辦**
只能**記錄錯誤然後立刻返回** —— 遞增一個計數器、設個旗標。
❌ 不能 `printf`（慢、可能阻塞）
❌ 不能等主程式清空（ISR 不能阻塞）
❌ 不能 `malloc` 擴充緩衝區
主程式之後檢查 `g_rx_overflow` 再決定怎麼處理。

</details>

---

## 6 · 把資料送出 ISR 的三種管道

| 管道 | 適合 | 注意 |
|---|---|---|
| **`volatile` 全域 ＋ 旗標** | 單一事件通知 | 多位元組讀取不是原子的 |
| **ring buffer** | 連續資料流（UART、ADC） | 單生產單消費可免鎖 |
| **RTOS 的 `...FromISR` API** | 有 RTOS 時通知任務 | ⚠️ **必須用 FromISR 版本** |

### ⭐ 等一下 —— semaphore 不是鎖嗎？ISR 不是不能阻塞？

**Semaphore 本質是「計數器 ＋ 等待佇列」，不是鎖。** 它只做兩件事：

| 操作 | 做什麼 | 會阻塞嗎 | ISR 能用嗎 |
|---|---|---|---|
| **give / signal** | 計數 +1，叫醒一個等待者 | **❌ 從不阻塞** | ✅ **可以** |
| **take / wait** | 計數 −1；是 0 就睡著等 | ⚠️ **會阻塞** | ❌ 不行 |

**ISR 只 give，從不 take** —— 所以合法。

```c
// ISR 端
xSemaphoreGiveFromISR(rx_sem, &hp_woken);   // give，放完就走 ✅

// Task 端
xSemaphoreTake(rx_sem, portMAX_DELAY);      // take，會睡；task 可以睡 ✅
```

> 比喻：**give 是把鑰匙放到桌上**（放完就走）；**take 是去桌上拿鑰匙**（沒有就得等）。

### 同一個 semaphore，兩種完全相反的用法

| | **當鎖**（互斥） | **當信號**（通知） |
|---|---|---|
| 初始計數 | **1** | **0** |
| 誰 take | 要進臨界區的人 | **消費者** |
| 誰 give | **同一個人**，用完還回去 | **生產者**（常是 ISR） |
| 方向 | 一來一回 | **單向** |
| 比喻 | 廁所鑰匙（自己還） | 餐廳叫號器（廚房按、客人領） |

**ISR 用的是右邊那種。**

### ⚠️ 但不要拿 semaphore 當鎖用

技術上可以（初始計數設 1），實務上不建議：
- **沒有所有權** → 任何 thread 都能 give，容易破壞不變量
- **沒有 priority inheritance** → 會踩到 **priority inversion**

所以 FreeRTOS 分兩個 API：
```c
xSemaphoreCreateMutex();     // 要互斥 → 用這個（有 priority inheritance）
xSemaphoreCreateBinary();    // 要通知 → 用這個
```

### 對照：為什麼 mutex 整個都不能在 ISR 用

Mutex 的規則是「**誰 take 誰才能 give**」——妳必須先 `take` 才能 `give`，
而 `take` 會阻塞 → ISR 用不了 → **ISR 根本無法合法持有一把 mutex**。
所以連 `FromISR` 版本都不提供。

| | ISR 能 give | ISR 能 take | 結論 |
|---|---|---|---|
| **Semaphore** | ✅ | ❌ | **可以用**（只 give） |
| **Mutex** | ❌（要先 take） | ❌ | **完全不能用** |

### ⚠️ 為什麼 give 還要 `FromISR` 版本

```c
xSemaphoreGive(sem);              // ❌ 在 ISR 裡用會出事
xSemaphoreGiveFromISR(sem, &hp);  // ✅ ISR 專用版本
```

**不是因為阻塞，是因為 context switch 的時機。** 一般版本若喚醒了更高優先權的 task
會**立刻切換過去** —— 在中斷處理到一半時切換會把狀態搞爛。

`FromISR` 版本把「要不要切換」的決定**延後**：透過 `hp_woken` 回報，
由 `portYIELD_FROM_ISR()` 在 **ISR 返回時**才切。

```c
BaseType_t hp_woken = pdFALSE;              // ★ 一定要初始化
xSemaphoreGiveFromISR(rx_sem, &hp_woken);
portYIELD_FROM_ISR(hp_woken);               // ★ 忘了寫不會壞，但反應變慢
```

---

## 7 · 中斷優先權與巢狀中斷

- **高優先權的中斷可以打斷低優先權的 ISR** —— 所以 ISR 也可能被插隊
- ARM Cortex-M 用 **NVIC** 管理優先權，數字**愈小優先權愈高**
- 同優先權的中斷不會互相打斷，會排隊

**實務影響**：如果一份資料被兩個不同優先權的 ISR 碰，光靠「進了 ISR 就安全」是錯的 ——
高優先權那個還是會插進來。

---

## 8 · 關中斷：臨界區怎麼寫才不會漏開

```c
__disable_irq();
// 臨界區（要極短！）
__enable_irq();
```

⚠️ **問題**：如果這段程式碼被呼叫時中斷**本來就是關的**，`__enable_irq()` 會把它
**意外打開** —— 破壞了呼叫者的臨界區。

**正確做法是存回原本的狀態：**

```c
uint32_t state = __get_PRIMASK();   // 存下目前的中斷狀態
__disable_irq();
// 臨界區
__set_PRIMASK(state);               // 還原（本來關著就繼續關著）
```

Linux 的 `spin_lock_irqsave()` 名字裡的 **save** 就是在講這件事。

---

## ⚠️ 常犯錯誤

1. **忘記清中斷旗標** → 無限重入，系統卡死。**症狀是主迴圈完全跑不到。**
2. **用 `|=` 清 W1C 旗標** → 連帶清掉別的旗標。要用 `SR = FLAG`。
3. **ISR 名字打錯** → 編譯過、但永遠不會被呼叫（weak symbol 沒被覆寫）。
4. **在 ISR 裡用一般版的 RTOS API** → 沒用 `FromISR`，可能阻塞或當機。
5. **臨界區直接 `__enable_irq()`** → 沒還原原本狀態，破壞呼叫者的臨界區。
6. **ISR 裡做慢事**（`printf`、`malloc`、等鎖）→ 拉高 interrupt latency。
7. **用 `SR != FLAG` 測旗標** → 狀態暫存器裡不只一個位元，多個旗標同時成立時會誤判、漏資料。
   **測單一位元一律用 `&` 遮罩**：`if (!(SR & FLAG)) return;`
8. **⭐ 在 ISR 裡「重試到成功」** → 死鎖。
   ```c
   while (rb_push(c) == 0) { }    // ❌ buffer 滿了就永遠出不去
   ```
   只有主程式會清空 buffer，但主程式被這個 ISR 卡住 → buffer 永遠不會空。
   **「失敗就重試」是一般程式的好習慣，在中斷情境是 bug** —— 失敗只能記錄後返回：
   ```c
   if (!rb_push(c)) g_rx_overflow++;   // ✅ 寧可丟一筆資料，不能卡住系統
   ```

---

## Recall prompt

> 1. ISR 的通用骨架四步是什麼？
> 2. 忘記清中斷旗標會發生什麼事？症狀長什麼樣？
> 3. Timer 和 UART 的清旗標機制差在哪？
> 4. 為什麼真實 ISR 沒有參數也沒有回傳值？那怎麼跟主程式溝通？
> 5. 為什麼 ISR 名字打錯不會編譯錯誤？（weak symbol）
> 6. 臨界區為什麼不能直接 `__enable_irq()`？正確寫法是什麼？
> 7. RTOS 的 `...FromISR` 版本在解決什麼問題？

相關：[[const-volatile-static-define]] · [[c-pointers-padding-bits]] · [[embedded-systems]]
