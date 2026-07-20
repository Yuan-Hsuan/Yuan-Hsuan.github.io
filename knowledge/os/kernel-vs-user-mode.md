---
id: os-kernel-vs-user-mode
domain: systems
title: Kernel Mode vs User Mode
tags: [os, security, privilege, syscall]
mastery: 0
source:
visibility: public
---

The CPU privilege separation exists for **protection**.

- **User Mode:** the restricted mode for regular applications — low privilege, **cannot** directly access hardware or unmapped memory.
- **Kernel Mode:** where the OS core and drivers run, with full access to hardware.

When a user-mode program needs a privileged operation (read a file, allocate memory), it issues a **System Call**, which traps into Kernel Mode to do the work safely, then returns.


區分兩種模式是為了**系統安全**。User Mode 是應用程式環境、權限極低，不能直接碰硬體或別人的記憶體；Kernel Mode 是 OS 核心與驅動的環境、最高特權。User 程式要讀寫檔案或配置記憶體，必須發 **System Call** 觸發中斷切到 Kernel Mode 代為執行，完成再切回。
