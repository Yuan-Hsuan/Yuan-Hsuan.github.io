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
