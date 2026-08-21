---
id: embedded-const-volatile-static-define
domain: systems
title: const / volatile / static / #define — 四個關鍵字，四種「限制」
tags: [embedded, c, compiler, linkage, mmio, isr]
mastery: 0
source:
visibility: private
---

## Idea

這四個是嵌入式 C 面試必考的一組，但它們作用在**完全不同的階段**——
搞清楚「誰在什麼時候管什麼」，就不會混淆。

| 關鍵字 | 作用階段 | 管什麼 | 一句話 |
|---|---|---|---|
| **`#define`** | **前置處理**（編譯前） | 純文字替換 | 「編譯器還沒看到就被換掉了」 |
| **`const`** | **編譯期** | 我不能改 | 「唯讀承諾，編譯器幫我把關」 |
| **`volatile`** | **編譯期**（禁止優化） | 值可能被別人改 | 「每次都真的去記憶體讀」 |
| **`static`** | **編譯＋連結** | 存活時間 / 誰看得到 | 「藏起來，或活久一點」 |

---

## 1 · `#define` —— 前置處理器的文字替換

**是什麼**：在真正編譯之前，前置處理器把所有出現的地方**原封不動替換成文字**。
編譯器根本沒看過那個名字。

```c
#define MAX_SIZE 100
int buf[MAX_SIZE];        // 編譯器實際看到的是 int buf[100];
```

### ⚠️ 三個經典陷阱

**(1) 沒有型別、沒有作用域**
```c
#define MAX 100          // 純文字，不是變數，除錯器看不到這個名字
const int MAX = 100;     // ✅ 有型別、有作用域、除錯看得到
```

**(2) 括號不夠會被運算子優先權咬**
```c
#define SQUARE(x) x * x
SQUARE(2 + 3)            // 展開成 2 + 3 * 2 + 3 = 11，不是 25 ❌

#define SQUARE(x) ((x) * (x))    // ✅ 每個參數、整體都要括號
```

**(3) 參數有副作用會被求值多次**
```c
#define MIN(a,b) ((a) < (b) ? (a) : (b))
MIN(x++, y)   // 展開成 ((x++)<(y)?(x++):(y)) → x 可能被 ++ 兩次！
```

### ⚠️ 什麼時候**必須**用 `#define`（`const` 做不到）

- **條件編譯**：`#ifdef DEBUG` —— `const` 完全做不到
- **含括保護**：`#ifndef CONFIG_H`
- **⭐ 陣列大小、`case` 標籤、位元欄位寬度** —— 這些需要**編譯期常數運算式**

**最後一條是 C 和 C++ 的真實差異，很容易踩：**

```c
const int SIZE = 256;
static uint8_t buf[SIZE];     // ❌ 在 C 裡編譯錯誤！
                              // ✅ 在 C++ 裡可以

#define SIZE 256              // ✅ C/C++ 都可以
enum { SIZE = 256 };          // ✅ enum 是真正的編譯期常數
```

**為什麼**：C 的 `const` 只是「**唯讀變數**」，不是編譯期常數 —— 它有記憶體位址、值在執行期才確定。
C++ 的 `const int` 才被當成 constant expression。

> ⚠️ C99 有 VLA（可變長度陣列）可以用變數當大小，但 **VLA 不能是 `static`、不能在檔案層級**，
> 所以韌體的靜態緩衝區還是只能用 `#define` 或 `enum`。

> **現代建議**：常數優先用 `const`（有型別、有作用域、除錯看得到），
> 函式優先用 `static inline`；**但陣列大小這類需要編譯期常數的地方，用 `#define` 或 `enum`**。

---

## 2 · `const` —— 唯讀承諾

**是什麼**：這個變數宣告後不能再改，**編譯期**檢查。可以修飾任何型別。

```c
const int MAX = 100;
MAX = 200;              // ❌ assignment of read-only variable
```

⚠️ **被 `const` 鎖住的東西，宣告當下是唯一給值的機會**：
```c
const int x;             // ❌ 沒意義 —— 之後永遠不能賦值
char * const p = buf;    // ✅ 指標本身是 const → 一定要現在給
```

### 用在四個地方

**(1) 取代 `#define` 定義常數** —— 見上一節。

**(2) 函式參數 —— 最常用、最有價值**
```c
void print_buffer(const char *buf, size_t len);   // 保證：我只讀不改
size_t strlen(const char *s);                     // 標準庫用它溝通
char*  strcpy(char *dest, const char *src);       // dest 會改，src 不會
```

**(3) 指標 —— 兩個東西可以被鎖**
```c
const char *p;               // 內容不能改；p 可以改指向別處
char * const p = buf;        // p 不能改（鎖死指向）；內容可以改
const char * const p = buf;  // 兩個都不能改
```
**口訣**：`const` 在 `*` **左邊**管內容，在 `*` **右邊**管指標本身。

**(4) 結構成員 / 回傳值**

### ⭐ 韌體重點：`const` 決定資料放哪裡

```c
const int lookup[256] = { ... };    // → .rodata，留在 Flash
int       buffer[256];              // → .bss，佔 RAM
```

MCU 的 RAM 通常只有幾十 KB、Flash 有幾百 KB。**大查表、字串、字型檔加上 `const`
會留在 Flash 不複製到 RAM**，省下大量 RAM。這就是韌體常見
`static const uint8_t font_table[] = {...}` 的原因。

### ⚠️ `const` 不等於「不會變」

它是**編譯器的檢查**，不是硬體保護：
```c
const int x = 5;
int *p = (int*)&x;
*p = 10;              // ⚠️ 未定義行為，但編譯器不一定擋得住
```
而且值還是可能被**別人**改 —— 這正是 `const volatile` 存在的理由。

---

## 3 · `volatile` —— 告訴編譯器「這個值背後有你不知道的手」

**是什麼**：每次都**真的去記憶體讀/寫**，不准快取到 CPU 暫存器、不准優化掉、
不准跟其他 volatile 存取重排。

### 為什麼需要它：一段會壞掉的程式

```c
uint32_t *status = (uint32_t *)0x40000000;
while (*status == 0) { }        // 等硬體 → 永遠卡住 ❌
```

編譯器的推論很合理：「迴圈裡沒人改 `*status`，那我讀一次存進暫存器就好。」

```asm
    load  r1, [0x40000000]    ; 只讀這一次！
loop:
    cmp   r1, #0              ; 之後都在比對 CPU 暫存器裡的舊值
    beq   loop                ; 永遠相等 → 死迴圈
```

加上 `volatile` 才會每圈重讀：
```c
volatile uint32_t *status = (volatile uint32_t *)0x40000000;
```

> ⚠️ **術語陷阱**：上面出現兩種「暫存器」——編譯器快取進去的是 **CPU 暫存器（register）**，
> 要讀的硬體狀態在 **周邊暫存器（peripheral register）**。中文同名，是不同東西。

### 三種「看不見的手」

| 情況 | 誰在背後改 | 例子 |
|---|---|---|
| **硬體暫存器（MMIO）** | 硬體 | UART 的 TX_READY 旗標 |
| **ISR 改的全域變數** | 中斷 | `volatile int flag;` ISR 設 1、主迴圈等它 |
| **多執行緒共享** | 別的 thread | 停止旗標 |

```c
volatile int timer_fired = 0;          // ← 沒有 volatile 就死迴圈
void timer_isr(void* d) { timer_fired = 1; }
void main_loop(void) {
    while (!timer_fired) { }
    handle_timeout();
}
```

### ⚠️ volatile **不能**做什麼（面試分水嶺）

| `volatile` 保證 | `volatile` **不**保證 |
|---|---|
| 每次都真的存取記憶體 | ❌ **原子性**（`i++` 還是讀-改-寫三步，照樣 race） |
| 編譯器不省略、不快取 | ❌ **CPU 亂序執行**（要 memory barrier） |
| volatile 存取之間不被重排 | ❌ **多核 cache 一致性** |

**一句話：`volatile` 只管編譯器，不管 CPU 和快取。**

```c
volatile int counter;
counter++;        // ❌ 還是 race condition，volatile 救不了
                  //    要原子性得用 atomic、關中斷，或鎖
```

---

## 4 · `static` —— 同一個字，位置不同意思完全不同

| # | 放哪裡 | 作用 | 影響什麼 |
|---|---|---|---|
| 1 | 函式**內**的變數 | 生命週期變成整個程式 | **存活時間** |
| 2 | 函式**外**的變數 | 只有本檔可見 | **連結性 linkage** |
| 3 | 函式 | 只有本檔可呼叫 | **連結性 linkage** |

### 1️⃣ 函式內：跨呼叫保留值

```c
void count(void) {
    static int n = 0;    // ★ 只初始化一次，之後保留
    n++;
    printf("%d\n", n);
}
count();  // 1
count();  // 2
count();  // 3
```
拿掉 `static` → 每次重新歸零，永遠印 1。

**差別在記憶體位置**：普通區域變數在 **stack**，函式返回就消失；
`static` 在 **`.data` / `.bss`**，活到程式結束。但**作用域沒變**，出了函式還是看不到。

### 2️⃣ 檔案層級變數：只有本檔看得到

```c
// sensor.c
static int calibration = 100;
```
```c
// main.c
extern int calibration;     // ❌ 連結錯誤：找不到這個符號
```

### 3️⃣ static 函式：切出公開介面 vs 內部實作

```c
// sensor.c
static int raw_to_celsius(int raw) { ... }   // 內部工具，不對外
int sensor_read_temp(void) {                 // 公開 API
    return raw_to_celsius(read_adc());
}
```

### 背後機制：編譯 → 連結

C 是**分離編譯**的，每個 `.c` 獨立編譯，最後才拼起來：

```
sensor.c ──編譯──→ sensor.o  （含 calibration 的實體）
main.c   ──編譯──→ main.o    （只有「我要用它」的記號，位址留白）
                        ↓
                   linker：把記號接到實體
```

`static` 的作用是：**編譯時不把這個名字登記進對外符號表** → linker 找不到 →
這就是 **internal linkage（內部連結）**。

> 💡 **編譯 `main.c` 不需要 `sensor.o`**，只需要 header 裡的宣告。
> 所以 `.c` 可以並行編譯（`make -j` 加速的原理），只有連結階段才需要湊齊所有 `.o`。

### 檔案層級 static 的三個效果

1. **`extern` 連不到** ✅
2. **避免跨檔案命名衝突** —— 兩個檔案都能有自己的 `static int counter;`。
   沒有 `static` 會 multiple definition 連結錯誤。
3. **編譯器能做更多優化** —— 確定沒有外部程式碼會碰它。

### ⚠️ 但它**不擋**指標

```c
// sensor.c
static int calibration = 100;
int* get_cal_ptr(void) { return &calibration; }
```
```c
// main.c
int* p = get_cal_ptr();
*p = 50;          // ✅ 改到了！static 完全沒擋
```

**`static` 藏的是「名字」不是「記憶體」** —— 提供封裝，不是保護。

### ⚠️ 不要在標頭檔宣告 static 變數

每個 `#include` 它的 `.c` 都會**各自產生一份獨立副本**，改了互相看不到。
正確做法是 header 放 `extern` 宣告、定義放某一個 `.c`。

---

## 5 · 組合用法（韌體天天在用）

### `const volatile` —— 唯讀的硬體狀態暫存器

```c
const volatile uint32_t *TEMP_REG;   // 我只能讀，但硬體一直在改
```

| 修飾 | 意思 | 誰不能改 |
|---|---|---|
| `const` | 唯讀 | **我的程式**（編譯期擋） |
| `volatile` | 值會自己變 | 沒人被擋，是叫編譯器**別優化** |
| `const volatile` | 唯讀但會自己變 | 我不能寫，但**硬體**會改 |

### `volatile ... * const` —— MMIO 的標準寫法

```c
volatile uint32_t * const REG = (volatile uint32_t *)0x40010000;
//  ↑                    ↑
//  內容會自己變          指標鎖死，不會亂飄
```

### `static const` —— 藏起來 ＋ 放 Flash

```c
static const uint8_t font_table[] = { ... };
//  ↑            ↑
//  別的檔看不到   放 .rodata，不佔 RAM
```

---

## 6 · 資料放哪個區段（`.bss` vs `.data` vs `.rodata`）

**判斷標準是「初值是不是 0」，不是「有沒有初始化」：**

| 宣告 | 區段 | 佔映像空間嗎 | 為什麼 |
|---|---|---|---|
| `static int n = 0;` | **`.bss`** | ❌ 不佔 | 全是 0，只要記大小，開機清零就好 |
| `static int n;`（不給） | **`.bss`** | ❌ 不佔 | C 規定預設為 0 |
| `static int n = 5;` | **`.data`** | ✅ 佔 | 非零初值必須實際存在 Flash |
| `const int n = 5;` | **`.rodata`** | ✅ 佔（在 Flash） | 唯讀，**不複製到 RAM** |
| `int arr[1000];`（區域） | **stack** | ❌ | 函式返回就消失 |

```
高位址  ┌──────────┐
        │  stack   │ ↓ 區域變數、呼叫框
        │    ⋮     │
        │  heap    │ ↑ malloc
        ├──────────┤
        │  .bss    │ 初值為 0 的全域/static → 開機清零
        │  .data   │ 有非零初值 → 初值存 Flash，開機複製到 RAM
        │ .rodata  │ const 資料、字串字面值 → 留在 Flash
低位址  │  .text   │ 程式碼
        └──────────┘
```

> 💡 **實際影響**：`static uint8_t buf[4096] = {0};` 放 `.bss`，韌體映像不變大；
> 初始化成非零值就多 4KB。而 `const` 大表留在 Flash，省下的是寶貴的 RAM。

---

## Recall prompt

> 1. 這四個關鍵字各自作用在哪個階段？（前置處理 / 編譯 / 連結）
> 2. 沒加 `volatile` 的等待迴圈為什麼會死？編譯器做了什麼「合理」的推論？
> 3. `volatile int counter; counter++;` 為什麼還是有 race condition？
> 4. `static` 放函式內和放函式外，各改變了什麼？
> 5. 檔案層級的 `static` 能不能防止別的檔案透過指標修改那個變數？
> 6. `static int n = 0;` 和 `static int n = 5;` 分別放哪個區段？差在哪？
> 7. `const volatile` 什麼時候用？兩個修飾各在講誰？
> 8. `#define SQUARE(x) x * x` 呼叫 `SQUARE(2+3)` 會得到什麼？為什麼？

相關：[[c-typedef-function-pointers]] · [[embedded-systems]]
