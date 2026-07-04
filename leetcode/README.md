# LeetCode — practice by pattern 依範式練習

Interviews aren't about memorizing 500 problems — they're about recognizing which of ~12
**patterns** a problem maps to. Each folder here is one pattern. Each file is one problem with
its pattern insight, my solution, and a recall prompt. 面試不是背 500 題，而是認出這題屬於哪個範式。

## The core patterns 核心範式

| pattern | signal it fits 什麼時候用 | seeded |
|---------|--------------------------|--------|
| **hash-map** | need O(1) lookup of "have I seen X / its complement" | ✅ two-sum |
| **two-pointers** | sorted array, pair/triplet, in-place from both ends | ✅ valid-palindrome |
| **sliding-window** | longest/shortest contiguous subarray/substring under a constraint | ✅ longest-substring |
| **binary-search** | sorted (or monotonic answer space), find boundary/target in O(log n) | ✅ binary-search |
| **bfs-dfs** | trees/graphs, shortest path (BFS), connected components (DFS) | — |
| **dynamic-programming** | "count ways / min-max" with overlapping subproblems | — |
| **heap** | top-K, streaming median, merge K sorted | — |
| **intervals** | overlapping ranges, merge/insert/schedule | — |
| **stack** | matching pairs, next-greater-element, monotonic stack | — |
| **linked-list** | in-place reversal, fast/slow pointers (cycle) | — |
| **backtracking** | generate all permutations/subsets/combinations | — |
| **greedy** | locally-optimal choice provably gives global optimum | — |

## How I use this 我怎麼用

1. Solve a problem → write it up here with the schema frontmatter → commit (grows the graph).
2. The `## Recall prompt` is what the CLI (and the site) quiz me on later.
3. `mastery` 0–5 tracks whether I could re-derive it cold. Re-review when the CLI says it's due.

> Goal isn't coverage, it's **pattern fluency** — being able to say within 60s "this is a
> sliding-window problem" and reach for the template. 目標是範式的直覺，不是題數。
