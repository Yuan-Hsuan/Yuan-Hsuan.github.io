---
id: systems-c-typedef-function-pointers
domain: systems
title: typedef & Function Pointers — 型別綽號與把函式當參數傳
tags: [c, pointers, typedef, callback, embedded]
mastery: 0
source: NVIDIA MCU Firmware VO（JR2013365）timer 題衍生
visibility: private
---

## typedef：把一個既有的型別取一個新名字

`typedef existing_type new_type;`

### Define an Alias for Pointer Type
```c
#include <stdio.h>

// Creating alias for pointer
typedef int* ip;

int main() {
    int a = 10;
    ip ptr = &a;

    printf("%d", *ptr);
    return 0;
}
```

### Output
```c
10
```

### 


## Function Pointer : 函式指標
要把「一個函式」當參數傳出去，
傳的其實是**它的位址** —— 所以需要一個指標來裝。

`return_type (*pointer_name)(parameter_types);`

### 傳入函式指標

```c
int add(int num1, int num2){
    return num1 + num2;
}

int sub(int num1, int num2){
    return num1 - num2;
}

typedef int (*ftprOperation)(int, int);

int compute(ftrOperation operation, int num1, int num2){
    return operation(num1, num2);
}

compute(add, 2, 3);
compute(sub, 2, 3);
```

### 傳回函式指標
```c
#include <stdio.h>

typedef int (*fptrOperation)(int, int);

int add(int a, int b) { return a + b; }
int sub(int a, int b) { return a - b; }

// ① 選擇層：依 opcode 回傳「要用哪個函式」
fptrOperation select(char opcode) {
    switch (opcode) {
        case '+': return add; // 注意：回傳 add，不是 add()
        case '-': return sub;
        default:  return NULL;
    }
}

// ② 執行層：選出來之後真的去算
int evaluate(char opcode, int num1, int num2) {
    fptrOperation operation = select(opcode);
    return operation(num1, num2);
}

int main(void) {
    printf("%d\n", evaluate('+', 5, 6));   // 11
    printf("%d\n", evaluate('-', 5, 6));   // -1
}

```

return add; 為什麼不加括號
這是這個範例最關鍵的一行:


return add;      // ✅ 回傳 add 這個函式的「位址」
return add();    // ❌ 呼叫 add 並回傳它的「結果」

函式名字單獨出現時,自動變成它的位址。 加了 () 才是呼叫。這跟陣列名字單獨出現會變成首元素位址是同一種語法糖。

也可以寫 return &add;,效果完全一樣 —— C 對函式名的 & 是可省略的。

### 邏輯

函式編譯後是一段機器碼，躺在 `.text` 區，有自己的起始位址。要把「一個函式」當參數傳出去，
傳的其實是**它的位址** —— 所以需要一個指標來裝。

```
記憶體
┌──────────────┐
│ 0x8001000    │ ← foo 的機器碼從這裡開始
│   foo 的程式  │
└──────────────┘

fptr func = foo;   // func 存著 0x8001000
func(data);        // 「跳到 0x8001000 執行」
```

### ⚠️ 那對括號不能省

```c
int (*fptr)(void*);   // ✅ 指標，指向「吃 void*、回傳 int」的函式
int *fptr(void*);     // ❌ 完全不同！這是「回傳 int* 的函式」
```

因為 `()` 的優先權比 `*` 高。不加括號時 `fptr` 會先跟 `()` 結合成「函式」；
加了括號才強迫 `*fptr` 先結合成「指標」。

### ⚠️ 少了參數列就不是函式指標

```c
typedef int (*fptr);              // 括號多餘 → 等於 int*，指向一個 int
typedef int (*fptr)(void* data);  // 有參數列 → 才是函式指標
//                  ↑↑↑↑↑↑↑↑↑↑↑ 關鍵在這段
```

---

## Callback

先交代好「等一下要做的事」，交給別人保管，時間到了由對方幫妳執行。

### 為什麼不能直接呼叫

1. **時間對不上**：要的是「100ms 之後才執行」，直接寫 `foo(data)` 是現在就跑。
2. **對象不確定**：寫 `execute_function_after` 時根本不知道未來誰會用它。函式內只能寫
   `cb(data)`，讓**呼叫者決定 `cb` 是誰**。

> **callback 的價值就是把「做什麼」和「什麼時候做」拆開。**

### `void* data` 這個慣例

callback 的參數幾乎都長成 `void* data`（context pointer）。因為系統**不需要知道**妳的資料是什麼型別，它只負責原封不動把指標交還給妳：

```c
typedef int (*fptr)(void* data);

int print_id(void* data) {
    int id = *(int*)data;      // 轉回自己知道的型別
    printf("id = %d\n", id);
    return 0;
}
```

**要傳多個參數？包成 struct，傳它的位址：**

```c
typedef struct { int pin; int times; } blink_args_t;

int blink_n(void* data) {
    blink_args_t* a = (blink_args_t*)data;
    for (int i = 0; i < a->times; i++) GPIO_Toggle(a->pin);
    return 0;
}

static blink_args_t args = { .pin = 5, .times = 3 };
execute_function_after(1000, blink_n, &args);
```

這是 C 做「泛型」的標準手法 —— 一個 `void*` 插槽，要塞多少東西都靠 struct 打包。

### ⚠️ 責任在妳，編譯器不檢查

這是 `void*` 最需要小心的地方：

```c
int   i = 42;
void* p = &i;

float f = *(float*)p;   // ⚠️ 編譯過，但結果是垃圾！
```

編譯器**完全不會警告** —— 妳說那是 `float`，它就照 `float` 的位元規則去解讀那 4 bytes。
但那塊記憶體裝的其實是整數 42 的位元排列，用浮點數規則讀出來會是一個莫名其妙的數字。

所以 `void*` 是「**用型別安全換通用性**」：能裝任何東西，代價是編譯器不再幫妳把關，
轉錯型別是妳自己的責任。

### ⚠️ 生命週期陷阱

傳出去的那塊資料**必須活得比 callback 執行的時刻久**：

```c
void thread_1(void) {
    blink_args_t args = {5, 3};              // ❌ 區域變數，在 stack 上
    execute_function_after(100, blink_n, &args);
}   // ← 函式返回，args 死了！100ms 後 callback 拿到垃圾位址
```

解法：用 `static`、全域，或 heap（韌體優先前兩者）。
這跟 dangling pointer 是同一類問題。

### 回傳型別要寫什麼

看**有沒有人在等結果**：

| 情境 | 例子 | 回傳值 |
|---|---|---|
| **Fire-and-forget** | timer callback、ISR | 沒人接 → `void` 最誠實（`int` 當狀態碼也常見） |
| **有人 join 等待** | `pthread_create` 的 start routine | `void*` 有意義，`pthread_join` 會收 |


## 7. 完整範例

```c
#include <stdint.h>

// ① 型別定義放檔案層級，在第一次用到之前（通常在 .h）
typedef int (*fptr)(void* data);

// ② 幾個符合這個簽章的 callback
int blink_led(void* data) { LED_Toggle(); return 0; }
int print_id(void* data)  { printf("%d\n", *(int*)data); return 0; }

// ③ 收 callback 的函式
void execute_function_after(uint32_t ms, fptr callback, void* data) {
    // 存起來，之後時間到了呼叫 callback(data)
}

// ④ 使用
static int my_id = 42;

void thread_1(void) {
    execute_function_after(100, blink_led, NULL);      // 不需要資料就傳 NULL
    execute_function_after(500, print_id,  &my_id);    // 傳 static 變數的位址
}
```

`blink_led` 和 `print_id` **簽章完全相同**，做的事卻不同 —— 這就是 `void*` 帶來的通用性。

---

## Recall prompt

> 1. 記 typedef 語法的那個訣竅是什麼？（提示：先寫變數宣告⋯）
> 2. `int *p(void*)` 和 `int (*p)(void*)` 差在哪？為什麼括號有差？
> 3. 為什麼 `*int p;` 不能編譯？
> 4. callback 為什麼不能直接呼叫就好？（兩個原因）
> 5. 要傳三個參數給 callback，但簽章只有一個 `void*`，怎麼辦？有什麼陷阱？

相關：[[embedded-systems]] · [[memory-leak]]
