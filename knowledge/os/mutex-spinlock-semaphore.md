---
id: os-mutex-spinlock-semaphore
domain: systems
title: Mutex vs Spin Lock vs Semaphore — and the ISR Case
tags: [os, concurrency, synchronization, locks, embedded, interrupts]
mastery: 0
source:
visibility: public
---

## The three locks

All three protect a shared resource — they differ in **what a thread does when it can't get in**, and **what they count**.

- **Mutex:** Provides mutual exclusion (one thread in the critical section at a time). If a thread cannot acquire the lock, it goes to **sleep (blocks)**, yielding the CPU — good for longer critical sections.
- **Spin Lock:** Same mutual exclusion, but instead of sleeping it **busy-waits** (spins in a loop), keeping the CPU. It avoids context-switch overhead, making it ideal for **very short** critical sections, or where you can't sleep (kernel / driver / ISR).
- **Semaphore:** A **signaling / counting** mechanism. A counting semaphore lets a limited number of threads into a resource pool; it can also enforce ordering between threads.

- **Mutex：** 用於互斥，一次只有一個 Thread 進入 Critical Section。拿不到鎖 → 進入**休眠 (Sleep/Block)** 並交出 CPU，適合較長的臨界區。
- **Spin Lock：** 同樣互斥，但拿不到鎖時在迴圈中「**盲等 (Busy-waiting)**」、不交出 CPU。適用於底層驅動或鎖定時間極短的場景，省下 Context Switch 開銷（ISR 裡唯一能用的）。
- **Semaphore：** 用於資源計數與同步，允許特定數量的 Thread 同時存取 (Counting)，也可控制執行緒先後順序。

## The stress test: protecting a critical section in an ISR

An **ISR (Interrupt Service Routine)** runs at very high privilege and is **not allowed to sleep**. So to protect a critical section shared between an ISR and other threads you **cannot use a Mutex** (it may block).

The correct approach is a **Spin Lock that also disables local interrupts** (e.g. Linux's `spin_lock_irqsave`). This ensures the CPU won't be preempted by another hardware interrupt while touching the shared data, keeping it consistent. (User space can't reach this data anyway — address-space isolation + MMU; it must go through a syscall.)

**ISR (中斷服務常式)** 特權極高且**不能睡眠**，所以保護 ISR 與其他 Thread 共用的臨界區**不能用 Mutex**（會休眠）。正解是用 **Spin Lock 搭配關閉局部中斷**（如 `spin_lock_irqsave`），確保存取共享資源時不被其他中斷搶占。user space 本來就靠位址空間隔離 + MMU 碰不到，要進 kernel 只能走 syscall。

## Single-core vs multi-core: why `spin_lock_irqsave` needs *both*

Disabling interrupts and taking a spin lock solve **different halves** of the same problem — which half you need depends on the core count.

**Single core — disabling interrupts alone is enough.** On a preemptive RTOS, context switches are themselves **driven by an interrupt** (the scheduler tick, or `PendSV` on ARM). Disable interrupts and that tick can't fire, so **no other thread can be scheduled in either**. "Interrupts off" effectively means "nothing can interrupt me."

**Multi-core — it is not enough.** `disable_irq()` writes a **core-local register** (e.g. `PRIMASK` on ARM). Core 0 masking its own interrupts does nothing to Core 1, whose threads can still touch the shared data concurrently. You need a spin lock as well: a **shared-memory** variable acquired with an **atomic** instruction (test-and-set / compare-and-swap), where the hardware guarantees only one core wins.

That is exactly why Linux bundles the two into one API — `spin_lock_irqsave()`. Seeing that name tells you the data is touched by **both an ISR and another core**.

**單核 —— 光關中斷就夠了。** preemptive RTOS 的 context switch 本身是**靠中斷驅動的**（排程器 tick、ARM 的 `PendSV`）。關掉中斷 → tick 進不來 → **其他 thread 也切不進來**。所以「關中斷」在單核上等於「這段沒人能打斷我」。⚠️ 前提是臨界區內不能主動阻塞或讓出 CPU。

**多核 —— 不夠。** `disable_irq()` 改的是**本核的暫存器**（ARM 的 `PRIMASK`），Core 0 把自己的中斷關掉，Core 1 的暫存器完全沒被碰，它的 thread 照樣能同時寫共享資料。所以要再加 spin lock —— 它是**共享記憶體**上的變數，用**原子指令**（test-and-set / CAS）去搶，硬體保證同一時間只有一顆核搶得到。

這就是 Linux 把兩者包成 `spin_lock_irqsave()` 的原因；看到這個函式名就知道：**這份資料同時被 ISR 和其他核碰**。

| Protection | Blocks ISR on **this** core | Blocks **other** cores | Usable **inside** an ISR |
|---|---|---|---|
| **Mutex** | ✅ | ✅ | ❌ blocks → deadlock |
| **Disable interrupts** | ✅ | ❌ | ✅ enough on single core |
| **Spin lock** | ❌ | ✅ | ⚠️ same-core ISR deadlocks |
| **Spin lock + disable interrupts** | ✅ | ✅ | ✅ **the multi-core answer** |

**Why a spin lock alone deadlocks on one core:** a thread holds the lock, an interrupt fires on that same core, the ISR spins waiting for the lock — but the thread that would release it can never run again, because the ISR is holding the CPU. Disabling interrupts is what prevents that window.

**為什麼只用 spin lock 會在同一顆核死鎖：** thread 持有鎖時中斷來了，ISR 想拿鎖 → 拿不到 → 原地空轉；但要放鎖的那個 thread 又被這個 ISR 佔著 CPU 跑不完 → 永遠空轉。關中斷就是在防這個窗口。

## A semaphore is a counter, not a lock

This is the most common source of confusion: a semaphore only ever does two things — `give` (count +1, wake one waiter) and `take` (count −1, sleep if it's zero). Whether it behaves like a "lock" depends **entirely on how you use it**.

| | **As a lock** (mutual exclusion) | **As a signal** (notification) |
|---|---|---|
| Initial count | **1** | **0** |
| Who takes | whoever enters the critical section | the **consumer** |
| Who gives | the **same** thread, on the way out | the **producer** (often an ISR) |
| Direction | round trip | **one way** |
| Analogy | a toilet key — you return it yourself | a restaurant pager — kitchen buzzes, guest collects |

**This is why an ISR may use a semaphore but never a mutex.** The ISR only ever calls `give`, and `give` never blocks. A mutex enforces **ownership** — only the thread that took it may give it back — so an ISR would first have to take a lock it is not allowed to take.

**⚠️ Don't use a semaphore as a lock in practice.** A binary semaphore has **no ownership and no priority inheritance**, so it will expose you to **priority inversion**; and nothing stops an unrelated thread from giving it and breaking the invariant. That's why FreeRTOS ships two separate constructors: `xSemaphoreCreateMutex()` for mutual exclusion, `xSemaphoreCreateBinary()` for signalling.

**Semaphore 本質是計數器,不是鎖。** 它只做兩件事：`give`（計數 +1，叫醒一個等待者）和 `take`（計數 −1，是 0 就睡）。它像不像「鎖」，完全取決於**你怎麼用它** —— 初始計數 1 ＋ 同一個人一來一回 = 當鎖；初始計數 0 ＋ 一方 give 一方 take = 當通知。

**這也解釋了為什麼 ISR 能用 semaphore 卻不能用 mutex：** ISR 只呼叫 `give`，而 `give` 從不阻塞。Mutex 強制**所有權**（誰 take 誰才能 give），ISR 得先 take 一把它根本 take 不了的鎖。

**⚠️ 實務上不要拿 semaphore 當鎖用：** binary semaphore **沒有所有權、沒有 priority inheritance**，會踩到 **priority inversion**；而且任何 thread 都能 give，容易破壞不變量。所以 FreeRTOS 分成兩個 API —— 互斥用 `xSemaphoreCreateMutex()`，通知用 `xSemaphoreCreateBinary()`。
