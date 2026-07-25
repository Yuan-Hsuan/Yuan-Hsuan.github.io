---
id: lc-cpp-quick-reference
domain: leetcode
title: C++ Quick Reference — Writing Patterns & Complexity
tags: [cpp, cheatsheet, stl, complexity]
difficulty: medium
mastery: 1
visibility: public
source: https://en.cppreference.com/w/cpp/container
---

> Quick reference for the C++ patterns and complexities I tend to forget. One topic per `##`, added over time.

## set vs unordered_set

| | `set` | `unordered_set` |
|---|---|---|
| Underlying | red-black tree | hash table |
| Find / insert / erase | **O(log n)** (guaranteed) | **average O(1)**, worst O(n) |
| Iteration order | sorted (ascending) | unspecified |
| `lower_bound` / `upper_bound` | ✅ | ❌ |


**Easy-to-forget gotchas**

**Say "average O(1)" honestly** — `unordered_set` is **average** O(1) but **worst-case O(n)** (hash collisions / rehash); `set`'s O(log n) is **guaranteed**. In an interview, remember to add "average" for the unordered version.

**Need sorted output → always `set`** — `unordered_set` has no defined iteration order; if you need sorted results, use `set` (or `unordered_set` + `sort`).

**Range queries only exist on `set`** — `unordered_set` has **no** `lower_bound` / `upper_bound`; for "the first element ≥ x", you need `set`.
