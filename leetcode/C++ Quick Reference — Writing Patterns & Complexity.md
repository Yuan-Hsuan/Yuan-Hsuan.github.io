---
id: lc-cpp-quick-reference
domain: leetcode
title: C++ Quick Reference — Writing Patterns & Complexity
tags: [cpp, cheatsheet, stl, complexity]
difficulty: medium
visibility: public
source: https://en.cppreference.com/w/cpp/container
importance: 1
last_reviewed: 2026-07-25
---

> Quick reference for the C++ patterns and complexities I tend to forget. One topic per `##`, added over time.

## set vs. unordered_set

| | `set` | `unordered_set` |
|---|---|---|
| Underlying | red-black tree | hash table |
| Find / insert / erase | **O(log n)** (guaranteed) | **average O(1)**, worst O(n) |
| `lower_bound` / `upper_bound` | ✅ | ❌ |

* **Say "average O(1)" honestly** — `unordered_set` is **average** O(1) but **worst-case O(n)** (hash collisions / rehash); `set`'s O(log n) is **guaranteed**. In an interview, remember to add "average" for the unordered version.

## unordered_map & unordered_set

`unordered_map` / `unordered_set` hash their key with `std::hash`. The STL ships **no `std::hash` specialization for `std::vector`** (nor `pair` / `tuple`), so `unordered_map<vector<int>, ...>` **fails to compile** — the compiler doesn't know how to turn a vector into a hash code.

**Three ways out**

* **Use `std::map` instead** — a red-black tree only needs `operator<`, which `vector` already provides. Costs O(log n) per operation.
* **Encode the key as a `string`** — serialize the vector into a string, then `unordered_map<string, ...>`. Keeps average O(1).
* **Provide a custom hash** — pass your own hash functor as the third template argument (the most work).