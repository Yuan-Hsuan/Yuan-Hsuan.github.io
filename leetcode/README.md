# LeetCode — practice by pattern

Interviews aren't about memorizing 500 problems — they're about recognizing which of ~12
**patterns** a problem maps to. Notes live flat here, one file per problem (named by its
LeetCode number + title); the pattern classification lives in each note's `tags` frontmatter,
since one problem often maps to several patterns.

## Note structure

Each note is SCHEMA frontmatter + a short, interview-style write-up:

- **🎙️ Naive Solution** — the brute-force baseline and why it's too slow. Skipped when a
  problem has no real naive→optimal twist.
- **🚀 Pitch** — how I'd explain the solution out loud: *The Bottleneck Observation* → *The
  Strategy* → *The Precise Execution*, then a **Complexity** block.
- **🛠️ Optimization** — the final C++ code.
- Optional: **🛡️ Defensive Coding** and a **💡 Heuristic Challenge** (a harder follow-up).

## The core patterns

| pattern | signal it fits |
|---------|----------------|
| **hash-map** | need O(1) lookup of "have I seen X / its complement" |
| **two-pointers** | sorted array, pair/triplet, in-place from both ends |
| **sliding-window** | longest/shortest contiguous subarray/substring under a constraint |
| **binary-search** | sorted (or monotonic answer space), find boundary/target in O(log n) |
| **bfs-dfs** | trees/graphs, shortest path (BFS), connected components (DFS) |
| **dynamic-programming** | "count ways / min-max" with overlapping subproblems |
| **heap** | top-K, streaming median, merge K sorted |
| **intervals** | overlapping ranges, merge/insert/schedule |
| **stack** | matching pairs, next-greater-element, monotonic stack |
| **linked-list** | in-place reversal, fast/slow pointers (cycle) |
| **backtracking** | generate all permutations/subsets/combinations |
| **greedy** | locally-optimal choice provably gives global optimum |

(Which patterns already have write-ups shows on the site's practice-log filters — the notes'
`tags` are the source of truth, no hand-kept column here.)

## Frontmatter fields

- `tags` — the pattern(s); the source of truth for classification.
- `difficulty` — easy / medium / hard.
- `importance` — 1–5, how much I want to re-drill this. My review-priority knob; I bump it
  before an interview.
- `last_reviewed` — the date I last reviewed the problem.
- `id` / `title` / `source` / `visibility` — standard SCHEMA fields (only `visibility: public`
  notes render on the site).

## How I use this

1. Solve a problem → write it up here with the frontmatter above → commit (grows the graph).
2. Review by **importance**: re-drill the highest-importance problems by pitching the solution
   out loud, then bump `last_reviewed`.

> The goal isn't coverage, it's **pattern fluency** — being able to say within 60s "this is a
> sliding-window problem" and reach for the template.
