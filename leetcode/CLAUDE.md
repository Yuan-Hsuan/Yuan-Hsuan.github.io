# leetcode/ — Note Protocol

How notes in this folder are written and how Claude assists. Read this before creating or
editing any note here. Inherits the site protocol in `../CLAUDE.md` and the design contract
in `../DESIGN.md`.

> These notes feed the public site: `../site/build.py` renders every `visibility: public`
> note into `index.html`. **Never hand-edit `index.html`.** A content push here ⇒ rebuild the
> site (`python3 ../site/build.py`) → `node --check` the inline JS → commit + push, so the
> notes and the contribution calendar go live together. **Push only when the author says so.**

## Frontmatter schema

```yaml
---
id: lc-two-sum              # stable slug, lc-<kebab-title>
domain: leetcode
title: 1. Two Sum
pattern: hash-table         # ONE canonical category — the shelf this problem lives on
concepts: [prefix-sum]      # optional list — the specific techniques it teaches
difficulty: easy            # easy | medium | hard
importance:                 # 1–5 review-priority knob (blank = author sets later)
last_reviewed: 2026-08-01   # ISO date of last review
source: https://leetcode.com/problems/two-sum/
visibility: public          # only `public` notes render on the site
---
```

- **`pattern` vs `concepts` is the core distinction.** `pattern` answers *"which category is
  this?"* and is exactly one value from the shelf list in `README.md` (hash-table, two-pointers,
  sliding-window, binary-search, bfs-dfs, dynamic-programming, heap, intervals, stack,
  linked-list, backtracking, greedy, tree/bst, matrix, array). A named algorithm
  (Manacher, Boyer-Moore, monotonic-stack, patience-sort, Dutch-flag, dummy-head…) is a
  **`concept`, never a `pattern`.**
- `build.py` builds the display/filter/graph tag list as `[pattern] + concepts`; notes still on
  the legacy `tags` key (cheatsheets, sibling repos) fall back unchanged.
- **No `mastery` / `optimal` / `tags` / `last_edit`** on problem notes — dropped in the
  2026-07-31 schema migration.

## Note body

Interview-style write-up, in this order:

- **`## 🎙️ Naive Solution`** — the brute-force baseline and why it's too slow. **Skip this
  section entirely when the problem has no real naive→optimal twist** (e.g. an obvious
  simulation); don't pad it.
- **`## 🚀 Pitch`** — how you'd explain the solution out loud:
  - `### The Bottleneck Observation` — the pain point that forces a better approach.
  - `### The Strategy` — the key idea / data structure.
  - `### The Precise Execution` — the exact steps / recurrence / edge handling.
  - `**Complexity**` — a Time and Space bullet.
- `---`
- **`## 🛠️ Solution`** (or `## 🛠️ Optimization`) — the final C++ code in a ```cpp fence.
- Optional: **`## 🛡️ Defensive Coding`**, **`## 💡 Heuristic Challenge`** (a harder follow-up).

## How Claude assists

1. **Author writes everything; Claude supplies only the blank template.** When given a problem
   number, Claude **creates the `.md` note file immediately** — frontmatter (with `pattern` set)
   + empty section skeleton. **No code, no complexity values, no solution material of any kind**
   (confirmed 2026-08-01). The author fills in all prose, the Complexity numbers, and the code
   themselves. Don't offer to "organize" or write the note for them.
2. **Verbal-practice grading loop.** When the author pitches a solution out loud, Claude: (1)
   grades it out of 10 against the note as answer key; (2) lists exactly what was missed
   (prioritizing the edge cases an interviewer probes); (3) folds genuinely-new good points into
   the note *only if* they add something it lacks — otherwise says so and adds nothing. Also
   catches delivery/language slips.
3. **Review priority = `importance`**, not a spaced-repetition CLI. Re-drill the highest-
   importance problems by pitching aloud, then bump `last_reviewed`.

## Gotchas

- **Images** live in a per-note `imgs/` subfolder and are referenced relatively
  (`imgs/foo.svg`); `build.py` prepends the note's folder so the same path renders in both the
  IDE preview and the site. Keep `]` out of image alt text (it breaks the markdown parser).
- **Never write a bare `$`** in a note — KaTeX auto-render treats `$…$` as inline math and
  mangles it. Write `5 / 25` and label the unit as "USD".
- One file per problem, named `<number>. <Title>.md`. `id` must be unique across the folder.
