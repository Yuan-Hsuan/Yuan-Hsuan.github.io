---
id: os-memory-leak
domain: systems
title: Memory Leak — System-Level Handling (Core Dump / Kill)
tags: [os, memory, debugging]
mastery: 0
source:
visibility: public
---

A memory leak occurs when a program continuously **allocates** memory without **freeing** it. At the system level, when RAM is critically low, the OS's **OOM Killer (Out-Of-Memory Killer)** intervenes.

For practical debugging: force a **Core Dump** of the suspect process to analyze which module holds the most memory, then use `kill` to terminate it and let the OS reclaim the resources. The code-level fix: free on every return path (`goto cleanup` in C, RAII / smart pointers in C++).


Memory Leak 是程式不斷 Allocate 卻忘記 Free。系統層面：記憶體快耗盡時，OS 的 **OOM Killer** 會介入。實務除錯：對可疑 Process 強制生成 **Core Dump** 分析哪個模組佔最多，再用 `kill` 終止、讓 OS 回收。程式碼根治：C 用 `goto cleanup`、C++ 用 RAII / smart pointer。
