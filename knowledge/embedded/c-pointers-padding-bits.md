---
id: embedded-c-pointers-padding-bits
domain: systems
title: 指標宣告 / struct padding / endianness / 位元操作 / inline
tags: [embedded, c, pointers, alignment, endianness, bitwise, inline]
mastery: 0
source:
visibility: private
---

## Idea

這幾個主題有一條共同的線：**「一塊記憶體裡到底放了什麼、怎麼被讀出來」**。
指標型別決定讀幾個 byte、padding 決定欄位擺哪、endianness 決定 byte 的順序、
位元操作決定怎麼改其中幾個 bit。

---

## 1 · 指標宣告 —— 由內往外念

```c
int a;              // 一個整數
int *a;             // 指向整數的指標
int **a;            // 指向「整數指標」的指標
int a[10];          // 10 個整數的陣列
int *a[10];         // 10 個「整數指標」的陣列          ← a 先跟 [] 結合
int (*a)[10];       // 指向「10 個整數的陣列」的指標    ← 括號讓 a 先跟 * 結合
int (*a)(int);      // 指向「吃 int 回傳 int 的函式」的指標
int (*a[10])(int);  // 10 個「函式指標」的陣列
```

**念法**：從**名字**開始，先看右邊（`[]`、`()`），再看左邊（`*`），有括號就先念括號內。

**關鍵是那對括號**：`()` 和 `[]` 的優先權比 `*` 高，
所以 `int *a[10]` 是「陣列裡放指標」，`int (*a)[10]` 才是「指向陣列的指標」。

### const 放哪裡

```c
const char *p;               // 內容不能改；p 可以改指向別處
char * const p = buf;        // p 不能改（鎖死指向）；內容可以改
const char * const p = buf;  // 兩個都不能改
volatile uint32_t * const REG = (volatile uint32_t *)0x40010000;   // MMIO 標準寫法
```

⚠️ **`* const` 的那些一定要在宣告時給初值** —— `const` 鎖的是指標本身，
宣告當下是唯一能賦值的機會。

---

## 2 · struct padding 與 alignment

**為什麼有 padding**：CPU 讀 4-byte 值時，若位址不是 4 的倍數，可能要多一次匯流排存取，
有些架構甚至直接 fault。編譯器就自動插入 padding 讓每個欄位對齊。

### 兩條規則

1. **每個成員的 offset 必須是它對齊需求的倍數**（通常 = 該型別的大小）
2. **struct 的總大小必須是「最大對齊需求」的倍數** ← ⚠️ 這條會產生**尾端填充**，最常被忘記

### 完整算一次

```c
struct S {
    char  a;    // 1
    int   b;    // 4
    short c;    // 2
    char  d;    // 1
};
```

```
offset  0: [a]                 char
offset  1: [pad][pad][pad]     ← ① 3 bytes，讓 b 對齊到 4
offset  4: [b][b][b][b]        int
offset  8: [c][c]              short（8 是 2 的倍數 ✅ 不用補）
offset 10: [d]                 char
offset 11: [pad]               ← ② 尾端填充！總大小要是 4 的倍數

sizeof(struct S) == 12
```

> **為什麼需要尾端填充**：`struct S arr[2];` 時，第二個元素也必須正確對齊 ——
> 如果大小是 11，`arr[1]` 就會從 offset 11 開始，`b` 對不齊了。

### 重排可以省空間

```c
struct S2 { int b; short c; char a; char d; };   // 4 + 2 + 1 + 1 = 8，完全沒 padding
```
**大的排前面**通常最省。從 12 降到 8，省了 33%。

### 對應硬體佈局要用 packed

當 struct 要**直接對應硬體暫存器佈局或網路封包格式**時，不能有任何 padding：

```c
struct __attribute__((packed)) reg_map {   // GCC/Clang
    uint8_t  ctrl;
    uint32_t data;
};
// 或 #pragma pack(1)
```

**代價**：存取未對齊欄位會變慢，某些架構（部分 ARM）直接 fault。

---

## 3 · endianness

多位元組的值在記憶體裡的擺放順序：

- **little-endian**：低位元組放低位址（x86、大多數 ARM）
- **big-endian**：高位元組放低位址（網路位元組序、部分 MIPS）

### ⚠️ 先搞清楚 hex 怎麼拆成 byte

**兩個十六進位數字 = 1 byte：**

```
0x12345678  →  [12] [34] [56] [78]
                 ↑    ↑    ↑    ↑
               byte byte byte byte
```

### 擺法對照

```c
uint32_t x = 0x12345678;
char *p = (char *)&x;
```

```
位址:            &x    +1    +2    +3
little-endian:  [78] [56] [34] [12]     → p[0]=0x78, p[3]=0x12
big-endian:     [12] [34] [56] [78]     → p[0]=0x12, p[3]=0x78
```

### 偵測

```c
int is_little_endian(void) {
    uint32_t x = 1;
    return *(unsigned char *)&x;   // little → 1、big → 0
}
```

**為什麼轉 `unsigned char*` 不是 `int*`：**

| 轉型 | 讀幾個 byte | 結果 |
|---|---|---|
| `*(char *)&x` | **1** | little → `0x01`、big → `0x00` ✅ 分得出來 |
| `*(int *)&x` | **4** | 兩種都是 `1` ❌ 分不出來 |

**endianness 只有在「逐 byte 拆開看」時才看得見** —— 讀 4 bytes 會照平台規則組回原值，
順序就被還原掉了。

用 `unsigned char` 的兩個理由：
1. `sizeof(char)` **標準保證是 1**，是唯一能可靠逐 byte 檢視的型別
2. `char` / `unsigned char` 是 **strict aliasing 的明文豁免**，允許檢視任何物件的位元組表示
   （`*(float*)&x` 那種就是 UB）

> **通則：指標的型別決定「解參考時讀幾個 byte、怎麼解讀」**，也決定 `p + 1` 跳多遠。
> 這也是 `void*` 不能解參考、不能做指標運算的原因。

---

## 4 · 位元操作

```c
reg |=  (1u << n);      // set    第 n 位
reg &= ~(1u << n);      // clear  第 n 位
reg ^=  (1u << n);      // toggle 第 n 位
if (reg & (1u << n))    // test   第 n 位
```

### 寫入一個「欄位」（連續幾個 bit）

韌體最常見的操作 —— 把 bit 4~7 設成某個值，其他位元不動：

```c
void set_field(volatile uint32_t *reg, uint32_t value) {
    *reg = (*reg & ~(0xFu << 4))       // ① 先清掉 bit 4~7
         | ((value & 0xFu) << 4);      // ② 再把新值移進去
}
```

兩個重點：
1. **用 `~` 產生遮罩**，不要手寫 32 個位元 —— `~(0xF << 4)` 就是
   `1111...11110000_1111`，安全又好讀。
2. **`value` 要先遮罩** `(value & 0xF)` —— 否則呼叫者傳 `0xFF` 會蓋到 bit 8~11。

⚠️ **這是 read-modify-write，不是原子操作**：中斷或另一核在「讀」和「寫回」之間也改了這個
暫存器，妳會把它的改動蓋掉。需要關中斷保護，或用硬體提供的 set/clear 專用暫存器。

### 常見技巧

```c
x && !(x & (x - 1))     // 判斷是不是 2 的冪
                        // 2 的冪只有一個 bit 是 1，減 1 會把它變 0、低位全變 1
x & (x - 1)             // 清掉最低位的 1
x & -x                  // 取出最低位的 1
```

---

## 5 · inline vs macro

### 函式呼叫的成本

```
① 參數放進暫存器/stack  ② 存返回位址  ③ 跳過去
④ 執行本體 ← 只有這步是真正的工作
⑤ 恢復現場  ⑥ 跳回來
```

對只有一兩行的小函式，前後那五步可能比工作本身還貴 —— 這就是想 inline 的理由。

`inline` 讓編譯器**把函式本體貼到呼叫處**，省掉跳轉：

```c
static inline int min(int a, int b) { return a < b ? a : b; }
int c = min(x, y);      // 展開成 int c = (x < y ? x : y);
```

### ⭐ 巨集的兩個陷阱是**獨立的**

| 陷阱 | 原因 | 加括號有用嗎 |
|---|---|---|
| **① 優先權** | 展開後跟周圍運算子搶結合 | ✅ **有用** |
| **② 多次求值** | 參數在定義裡本來就出現多次 | ❌ **沒用** |

```c
#define DOUBLE(x) x + x

DOUBLE(3) * 2       // → 3 + 3 * 2 = 9，不是 12      ← 陷阱 ①
int i = 5;
DOUBLE(i++)         // → i++ + i++ → 11，且 i 變 7   ← 陷阱 ②
```

加了括號之後：

```c
#define DOUBLE(x) ((x) + (x))

DOUBLE(3) * 2       // → ((3)+(3))*2 = 12   ✅ ① 修好了
DOUBLE(i++)         // → ((i++)+(i++))      ❌ ② 還是兩次！
```

**括號解決的是「展開後的運算順序」，解決不了「參數的文字被貼了幾次」。**

> ⚠️ `i++ + i++` 其實是**未定義行為**（同一序列點內修改 `i` 兩次）。
> 面試講「這是 UB」比講具體數字更正確。

### 函式為什麼沒這問題

**函式先把參數求值完再傳進去** —— `i++` 只執行一次，`a` 在函式內用幾次都是同一個值。

| | `#define` 巨集 | `inline` 函式 |
|---|---|---|
| 誰處理 | 前置處理器（貼**文字**） | 編譯器（貼**程式碼**） |
| 型別檢查 | ❌ | ✅ |
| 參數求值 | ⚠️ 用幾次算幾次 | ✅ 只算一次 |
| 除錯 | ❌ 展開後看不到 | ✅ 可下斷點 |

### 為什麼 inline 函式的定義要放 `.h`

**一般函式**：宣告放 `.h`、定義放 `.c` 就夠 —— 呼叫端只需要知道「怎麼呼叫」，
產生一個 `call` 指令，位址留給 linker 填。

**inline 函式**：要把本體**貼進來**，編譯器必須**當場看到本體**。只有宣告是貼不了的，
inline 就失效了。所以只要不只一個 `.c` 會用，**整個定義都要放進 `.h`**。

**而且要加 `static`** —— 否則十個 `.c` include 就有十份同名外部符號，linker 報
multiple definition。加 `static` 讓每份都是內部連結，互不衝突。
這就是 `static inline` 幾乎總是綁在一起的原因。

> 只有一個 `.c` 會用的話，直接寫在那個 `.c` 裡就好，不用汙染 header。

### 代價

inline 會讓程式碼變大（在 100 個地方呼叫 → 複製 100 份）。
Flash 只有幾十 KB 的 MCU 上，**只 inline 又小又常呼叫的函式**。

---

## ⚠️ 我犯過的錯（2026-08-15 測驗）

> 這節記自己實際答錯的，複習時優先看這裡。

### 1. hex 拆成 byte 的方式 ❌

`0x12345678` 的四個 byte 是 **`12` `34` `56` `78`** ——
**兩個十六進位數字 = 1 byte**，不是把數字一個一個拆。

當時答成 `08 05` / `01 04`，是把 hex digit 當成 byte 了。
→ little-endian 上 `p[0]=0x78`、`p[3]=0x12`，印出 **`78 12`**。

### 2. struct 的**尾端填充**忘記算 ❌

只想到「`char` 後面補 3 bytes」，漏掉**結尾也要補**。
規則是「**struct 總大小必須是最大對齊需求的倍數**」——
`char/int/short/char` 排到 offset 11，要補到 **12**。

### 3. 巨集的兩個陷阱沒分清 ❌

以為加括號就全好了。實際上：
- 優先權問題 → 括號**有用**
- 多次求值問題 → 括號**沒用**，只能改用 `static inline` 函式

### 4. bit 欄位寫入忘記遮罩 `value` ⚠️

```c
*reg |= value << 4;               // ❌ value > 15 會蓋到別的位元，而且沒先清舊值
*reg = (*reg & ~(0xFu << 4))      // ✅
     | ((value & 0xFu) << 4);
```
兩件事都要做：**先清舊值**、**新值先遮罩**。

### 5. `char * const p` 一定要在宣告時給初值 ⚠️

`const` 鎖的是指標本身 → 宣告當下是唯一能賦值的機會。

---

## Recall prompt

> 1. `int *a[10]` 和 `int (*a)[10]` 差在哪？那對括號在做什麼？
> 2. `struct { char a; int b; short c; char d; }` 的 sizeof 是多少？padding 出現在**哪兩個**地方？
> 3. `uint32_t x = 0x12345678;` 在 little-endian 上，`((char*)&x)[0]` 是什麼？
> 4. 為什麼偵測 endianness 要轉 `unsigned char*` 而不是 `int*`？（兩個理由）
> 5. 把 bit 4~7 設成 `value`、其他不動，怎麼寫？有什麼並行風險？
> 6. `#define DOUBLE(x) ((x)+(x))` 加了括號之後，`DOUBLE(i++)` 修好了嗎？為什麼？
> 7. 為什麼 inline 函式的定義必須放在 `.h`，而一般函式可以放 `.c`？

相關：[[const-volatile-static-define]] · [[c-typedef-function-pointers]] · [[embedded-systems]]
