---
id: os-virtual-memory
domain: systems
title: Virtual Memory
tags: [os, memory, paging, mmu]
mastery: 0
source:
visibility: public
---

Virtual Memory is an OS abstraction that gives every process its own continuous address space, solving three problems:

1. **Overcomes hardware limits:** swaps rarely-used pages to disk, so a program acts as if it has vast, contiguous memory.
2. **Isolation & protection:** each process gets an independent virtual address space, so one crashing can't corrupt others.
3. **Simplified management (paging):** programs use virtual addresses; the OS's **Page Table + MMU** translate them to physical RAM automatically.


虛擬記憶體是 OS 的抽象層，解決三個問題：(1) **突破實體限制**——不常用資料換到硬碟 (Swap)，讓程式以為有連續又大的記憶體；(2) **記憶體隔離與安全**——每個 Process 有獨立虛擬定址空間，崩潰不會弄死別人；(3) **方便管理 (Paging)**——程式用虛擬位址，OS 透過 Page Table 與 MMU 自動映射到實體 RAM。
