---
id: lc-jump-game-vii
domain: leetcode
title: 1871. Jump Game VII
tags: [sliding-window, dynamic-programming]
difficulty: medium
status: review
mastery: 3
importance: 3
optimal: true
source: https://leetcode.com/problems/jump-game-vii/
visibility: public
---

## 🎙️ Naive Solution
The goal is to decide whether we can reach the last index. A blind **Greedy** approach — always
taking `maxJump` — can miss the valid path, because the `minJump` lower bound may forbid exactly the
landing we picked. So we cannot be greedy; we must evaluate the reachability of **every** cell.

To evaluate a cell, we need to know whether at least one already-reachable cell exists inside its
historical window. If we naively rescan that whole window for every cell, we repeatedly re-check the
same cells, degrading the time complexity to **O(N * K)**.

## 🚀 Pitch

### The Bottleneck Observation
Consecutive cells look back at windows that overlap almost entirely. Re-scanning each window from
scratch throws away that overlap and redoes the same work again and again.

### The Strategy: Dynamic Sliding Window
Instead of looking back every time, maintain a **counter** of how many valid (reachable) cells
currently sit inside the window. As the window slides one step to the right, update the counter as
elements enter and exit. A cell is reachable exactly when this counter is positive — bringing the
solution down to an optimal **O(N)**.

## 🛠️ Solution
- For cell `i`, the window of possible predecessors is `[i - maxJump, i - minJump]`.
- As `i` advances, a new candidate enters the window on the right (index `i - minJump`) and the
  stale candidate leaves on the left (index `i - maxJump - 1`); update the counter for each.
- Cell `i` is reachable iff the window currently holds at least one reachable cell (counter > 0).
- The answer is whether the last cell is reachable.
