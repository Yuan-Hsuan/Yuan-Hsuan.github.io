---
id: lc-find-the-duplicate-number
domain: leetcode
title: 287. Find the Duplicate Number
tags: [array, two-pointers, binary-search, bit-manipulation]
difficulty: medium
status: review
mastery: 2
importance: 2
optimal: false
source: https://leetcode.com/problems/find-the-duplicate-number/
visibility: public
---

## 🎙️ Naive Solution
The array holds `n + 1` numbers in the range `[1, n]`, so by pigeonhole a duplicate must exist. The
straightforward way is a hash set that records seen values — O(N) time but O(N) extra space, which
the problem's constraints ask us to avoid.

## 🚀 Pitch

### The Bottleneck Observation
We want to locate the duplicate **without** modifying the array and **without** extra space.

### The Strategy: Cycle Detection / Binary Search
Two optimal directions:
- **Cycle Detection (Floyd):** treat each value as a "next index" pointer. Because a value repeats,
  the resulting linked structure contains a cycle, and the cycle's entrance is the duplicate.
- **Binary Search on the value range:** for a candidate mid value, count how many array elements are
  `<= mid`; a count larger than `mid` tells us the duplicate lies in the lower half.
