---
id: os-process-vs-thread
domain: systems
title: Process vs Thread
tags: [os, process, thread, concurrency, memory]
mastery: 0
source:
visibility: public
---

A **Process** is the smallest unit of resource allocation by the OS, with its own **isolated memory space**. 
A **Thread** is the smallest unit of CPU scheduling. Threads within the same process **share the Heap, Data section (global variables), and OS resources**, but each thread keeps its own independent **Stack and Registers** for function calls and local variables.

One-liner: Process = resource-allocation unit, memory-isolated; Thread = scheduling unit, shares heap/data but has its own stack.

**Process (行程)** 是作業系統分配資源的最小單位，各 Process 之間記憶體獨立、互不干擾。**Thread (執行緒)** 是 CPU 排程的最小單位，一個 Process 內可含多個 Threads。Threads 之間**共用 Heap 與 Data Section (全域變數)**，但每個 Thread 必須有自己獨立的 **Stack 和 Registers**，儲存各自的函式呼叫與區域變數。
