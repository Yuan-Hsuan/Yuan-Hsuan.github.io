---
id: os-race-condition
domain: systems
title: Race Condition
tags: [os, concurrency, synchronization]
mastery: 0
source:
visibility: public
---

A race condition occurs when multiple threads **concurrently access and modify the same shared resource** (e.g. a global variable). Because the CPU switches threads at unpredictable moments, the final outcome depends on execution order, producing unpredictable bugs.

The fix is a **synchronization mechanism** — `Mutex`, `Semaphore`, or **atomic operations** — to protect the code region (the **Critical Section**), ensuring only one thread modifies it at a time.


發生在兩個以上的 Thread **同時存取且修改同一個共享資源**時。因為 CPU 切換執行緒的時機不可預測，結果取決於先後順序，產生不可預期的錯誤。解法是用同步機制（Mutex / Semaphore / 原子操作）保護 **Critical Section**，確保一次只有一個 Thread 進去改。
