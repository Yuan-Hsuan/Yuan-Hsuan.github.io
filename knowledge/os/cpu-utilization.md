---
id: os-cpu-utilization
domain: systems
title: CPU Utilization — Diagnosing Too Low / Too High
tags: [os, performance]
mastery: 0
source:
visibility: public
---

CPU utilization is the fraction of time the CPU spends actually executing instructions. The diagnostic value is in the **extremes**:

- **Too low:** likely **I/O bound** (waiting on disk or network), leaving the CPU idle. Increase multiprogramming (run more processes) to fill idle cycles.
- **Too high (≈100%):** could be genuine **CPU-bound** work — but watch for an **infinite loop**, or **thrashing** (RAM too small, so the OS spends its cycles swapping pages instead of computing).


CPU Utilization 是 CPU 真正在執行指令的時間比例，看**兩端**：太低 → 可能 **I/O Bound**（在等硬碟/網路），CPU 閒置，可多開 Process 提高使用率；太高（接近 100%）→ 可能 **CPU Bound**，但也可能是**無窮迴圈**或 **Thrashing**（記憶體不夠，OS 狂在硬碟與記憶體間搬資料，全花在 overhead）。
