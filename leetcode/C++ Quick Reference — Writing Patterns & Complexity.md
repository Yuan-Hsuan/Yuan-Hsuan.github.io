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

## Keeping a Running Max/Min of a Changing Bag: `multiset` vs. `set` + `vector`

The problem shape: values keep being added and removed, and after every change you need the
current max (or min). Four standard ways to hold that bag — pick by *what you have to erase*.

| | `multiset<T>` | `map<T,int>` (value → count) | `set<pair<T,int>>` (value, unique id) | `vector<int>` counts + `set<T>` of present values |
|---|---|---|---|---|
| Duplicates | native | as a count | tagged unique | as a count |
| Insert / erase-one | $O(\log n)$ | $O(\log d)$ | $O(\log n)$ | $O(\log d)$ |
| Current max | `*rbegin()` | `rbegin()->first` | `rbegin()->first` | `*s.rbegin()` |
| Erase a **specific** occurrence | `erase(find(v))` — any one copy | decrement count | ✅ direct, by its id | decrement count |
| Needs values to be small ints | ❌ | ❌ | ❌ | ✅ (indexes the vector) |
| Memory | node per copy | node per distinct value | node per copy | node per distinct + flat array |

*(`n` = total elements, `d` = distinct values.)*

* **`erase(value)` on a `multiset` deletes *every* equal copy** and returns how many it removed —
  the classic bug when the bag holds repeated lengths. To drop exactly one, write
  `ms.erase(ms.find(value))`; `erase(iterator)` is amortized $O(1)$.
* **`count(v)` is $O(\log n + k)$**, not $O(\log n)$ — it walks the $k$ equal copies. If you only
  need "is it there", use `find`; if you need the multiplicity often, that's the signal to switch
  to `map<T,int>` where the count is stored, not counted.
* **`map<T,int>` is a multiset that pays per distinct value instead of per copy.** Fewer nodes,
  and `size()` is the distinct count — so keep a separate `total` if you need the element count.
  Its cost: you can only erase "some copy of `v`", never one specific occurrence.
* **`set<pair<T,int>>` is the version that can erase a specific occurrence.** Pair the value with
  a unique tag (an index, an id) so equal values stay distinct, then erase by the exact pair in
  one $O(\log n)$ hit — no `find`-then-erase dance, and no risk of deleting someone else's copy.
* **`vector` counts + `set` of present values** is the fastest of the four when the values are
  bounded small ints (lengths ≤ n, ages ≤ 120): the flat array holds the multiplicities with no
  allocation, the `set` holds only the distinct values so ordered queries cost $O(\log d)$.
* **The lazy-deletion alternative:** a `priority_queue` plus a "is this entry stale?" check when
  popping. $O(\log n)$ push, no arbitrary erase at all — good when you only ever *read* the max
  and can detect stale entries cheaply, bad when the queue fills with garbage.

## `std::prev` / `std::next` on a `set` = Amortized $O(1)$

Walking to a neighbour is **not** a second tree search. It's a tree successor/predecessor step:
if there's a right subtree, go right once then left all the way down; otherwise climb parent
pointers until you're someone's left child.

| | one step (`++it`, `prev(it)`, `next(it)`) | `next(it, k)` / `advance(it, k)` | jump to the k-th element |
|---|---|---|---|
| Cost | amortized $O(1)$, worst $O(\log n)$ | $O(k)$ | not supported |
| Why | path is bounded by the tree height | `set::iterator` is bidirectional, so it really takes k steps | needs an order-statistic tree (`__gnu_pbds::tree` → `find_by_order`, $O(\log n)$) |

* **A full scan is $O(n)$, not $O(n \log n)$.** Traversing `begin()` → `end()` crosses each tree
  edge exactly twice, so the whole walk costs $O(n)$ — that's where the amortized $O(1)$ per step
  comes from. Only a *single isolated* step can cost the full height.
* **The neighbour idiom rides along for free.** `auto it = s.lower_bound(x);` then `prev(it)` /
  `it` gives you the two neighbours of `x` in $O(\log n)$ total — the search is the cost, the
  neighbour step isn't.
* **Guard both ends — they're UB, not exceptions.** `prev(it)` needs `it != s.begin()`;
  dereferencing needs `it != s.end()`. `s.end()` itself *is* decrementable (that's how `rbegin()`
  works), but only when the set is non-empty.
* **Erasing invalidates only the erased iterator.** Every other iterator into a `set`/`map` stays
  valid across insert and erase, so grabbing `nxt = next(it)` *before* `s.erase(it)` is the safe
  way to erase while scanning.

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