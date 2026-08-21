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

## Backtracking notes — the six-slot pitch template

Every `pattern: backtracking` note uses the same two subsections, in this order. The reference
implementation is `93. Restore IP Addresses.md`; 22 / 46 / 47 / 78 follow it. Reuse the connective
sentences verbatim — the point is that only the slot *contents* change between problems.

```
### The Strategy: <name of the approach>
I'd model this as a backtracking problem. The problem wants **every** <thing>, so I have to
build each one. <one clause on why the exponential search is affordable, from the constraints>

### The Precise Execution
To implement the backtracking, at each step:

- **The state.** I would carry <params> down: ...
- **The decision.** I decide **<the one decision this level makes>**.
- **The options.** <the option set>.
- **The undo.** After each call returns, I pop ... so the next choice starts from the same
  state the previous one did.

To finalize:

- **The record.** When <condition>, I add the path to the answer.

To optimize it, I return early when:      <- or "There is nothing to prune here:"
- **The pruning.** <legality rule>. <dedup rule, or an explicit statement that none is needed>
```

- **Only "the decision" and "the options" really change between problems.** State / undo / record
  are the same sentence with different nouns.
- **Two kinds of pruning, always distinguish them.** *Legality* pruning answers "how do you avoid
  dead ends"; *dedup* pruning answers "how do you avoid repeated answers". When a problem has
  neither, say so out loud rather than skipping the slot (78 and 46 have neither; 93 and 22 have no
  dedup; 47's whole point is the dedup rule).
- **Skip `## 🎙️ Naive Solution` when backtracking is the first thing anyone would reach for**
  (93 has no naive→optimal twist). Keep it only where the brute force is genuinely different, as in
  22 (generate all `2^(2N)` strings, then validate).

## The author's spoken-pitch voice

Calibrated from her rewrites of drafted scripts (2026-08). Match this when drafting or polishing
any spoken pitch — hers is tighter than the default.

- **First person, present tense, contractions.** "I'd model this as…", "I decide…", "I have three."
  Never the stiff construction "For the state, I recurse with two values" — she rewrites it every
  time.
- **Cut justification she considers self-evident.** She removed the "DP would help if I only needed
  the count" line and the whole naive section from 93. Say why the approach is right *once*, in one
  clause, and move on.
- **Spoken connectives carry the structure.** "To implement the backtracking, at each step:" /
  "To finalize:" / "To optimize it, I return early when:" — the transitions, not the labels, are
  what make it sound like a person talking.
- **A concrete instance beats an abstract rule in prose.** She rewrote the length-pruning inequality
  as "only 2 segments left to build but 7 characters remaining".
- **Complexity is the exception — she wants it formal.** State the practical bound first ("bounded
  by a constant because the max length is 12 characters"), then the generalized parametric form
  (`O(M^N · N)`). Don't substitute plain-language formulas like "(number of leaves) × (copy cost)",
  and **don't edit a Complexity block she has written** unless she asks.

## Gotchas

- **Images** live in a per-note `imgs/` subfolder and are referenced relatively
  (`imgs/foo.svg`); `build.py` prepends the note's folder so the same path renders in both the
  IDE preview and the site. Keep `]` out of image alt text (it breaks the markdown parser).
- **Never write a bare `$`** in a note — KaTeX auto-render treats `$…$` as inline math and
  mangles it. Write `5 / 25` and label the unit as "USD".
- One file per problem, named `<number>. <Title>.md`. `id` must be unique across the folder.
