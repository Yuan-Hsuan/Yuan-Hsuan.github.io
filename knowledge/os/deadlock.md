---
id: os-deadlock
domain: systems
title: Deadlock — the Four Coffman Conditions
tags: [os, concurrency, deadlock]
mastery: 0
source:
visibility: public
---

A deadlock occurs when multiple threads wait **indefinitely** for resources held by each other. It requires **all four** Coffman conditions to hold **simultaneously**:

1. **Mutual Exclusion:** a resource can be held by only one thread at a time.
2. **Hold and Wait:** a thread holds one resource while waiting for another.
3. **No Preemption:** resources can't be forcibly taken away; the holder must release voluntarily.
4. **Circular Wait:** a closed waiting cycle (A waits on B, B on C, C on A).

Because all four must hold at once, breaking **any one** prevents deadlock — e.g. impose a global lock ordering to kill *circular wait*.


多個執行緒互相等待對方釋放資源、永遠卡住。死結必須「**同時**」滿足四個必要條件：互斥、持有並等待、不可搶占、循環等待。破壞任一條即可預防。
