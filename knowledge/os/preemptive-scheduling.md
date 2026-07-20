---
id: os-preemptive-scheduling
domain: systems
title: Preemptive Scheduling
tags: [os, scheduling]
mastery: 0
source:
visibility: public
---

Preemptive scheduling lets the OS **forcibly pause** a running process or thread — even if it hasn't voluntarily given up the CPU — usually via a **hardware timer interrupt**, and hand the CPU to another (typically higher-priority) task. This guarantees responsiveness and effective multitasking.

Contrast with *cooperative* scheduling, where a task keeps the CPU until it yields — one task that never yields freezes everything. That's why an RTOS uses priority-based preemptive scheduling.


搶占式排程是 OS 在一個 Process/Thread **尚未主動放棄 CPU** 時，透過硬體中斷（Timer Interrupt）**強行暫停**它，把 CPU 分配給優先權更高的任務，保證即時反應與多工。相對於 cooperative（要 task 自己讓出），preemptive 才不會被一個不讓的 task 卡死——RTOS 幾乎都用它。
