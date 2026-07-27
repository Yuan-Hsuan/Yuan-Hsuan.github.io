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

## 　`std::map`/`set` vs. `unordered` Variants

| | `set` | `unordered_set` | `map` | `unordered_map` |
|---|---|---|---|---|
| Underlying | red-black tree | hash table | red-black tree | hash table |
| Find / insert / erase | **O(log n)** | **avg O(1)**, worst O(n) | **O(log n)** | **avg O(1)**, worst O(n) |
| Ordered? (`lower_bound`) | ✅ | ❌ | ✅ | ❌ |

* Always say "average $O(1)$" for hash tables to show you understand hash collisions.
    * `set` / `map`'s O(log n) is **guaranteed**.

* `unordered_map<vector<int>, int>` fails to compile because C++ has no default hash for vectors, pairs, or triplets. **Three ways out:**

    * **Use `std::map` instead** — a red-black tree only needs `operator<`, which `vector` already provides. Costs O(log n) per operation.
    * **Encode the key as a `string`** — serialize the vector into a string, then `unordered_map<string, ...>`. Keeps average O(1).
    * **Provide a custom hash** — pass your own hash functor as the third template argument (the most work).

## String Operations = $O(L)$ Time

* Copying, substrings, concatenation, and hashing all require traversing the string, taking $O(L)$ time ($L$ = length of string).
* If you hash a string of length $L$ inside a loop of size $N$, your time complexity instantly becomes $O(N \times L)$.
* **A hash container's "$O(1)$" is per *number of elements*, not per key size.** A `string` key still costs $O(L)$ every insert/find (it hashes all $L$ chars, and compares $O(L)$ on a collision). `int` key → $L$ is constant → $O(1)$; `string` key → $O(L)$.

**Example — 127. Word Ladder** ([[lc-word-ladder]]): $N$ words of length $L$ live in an `unordered_set<string>`.
* One lookup is **not** $O(1)$ — hashing the length-$L$ word is $O(L)$.
* Each word spawns $L$ wildcard patterns (`h*t`, `ho*`, …); building + hashing each is $O(L)$ → $O(L^2)$ per word.
* Over all words: $O(N \times L^2)$ — that extra $L$ is exactly the string-key cost the "$O(1)$ lookup" hides.

## `std::sort` = $O(\log N)$ Space
The Stack Overhead: `std::sort` requires $O(\log N)$ auxiliary space to manage the recursive call stack.

> `std::sort` is **IntroSort** (quicksort + heapsort + insertion sort). It caps recursion depth, so the O(log N) is *guaranteed* — pure quicksort could degrade to O(N) stack on bad pivots, but IntroSort blocks that.