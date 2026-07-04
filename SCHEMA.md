# SCHEMA — the shared metadata contract 共用 metadata 合約

Every content file (LeetCode problem, BQ story, System Design writeup, AI concept)
begins with the **same YAML frontmatter**. This is the single rule that lets separate
folders stay separate for humans, but unified for the tools (CLI + site generator).

每個內容檔案的檔頭都用**同一套 YAML frontmatter**。這是「資料夾分開、工具統一」能同時成立的唯一規矩。

> This file is the source of truth. The CLI and the site generator both parse against it.
> Both repos (`Yuan-Hsuan.github.io` and `mind`) follow this schema.

---

## Frontmatter fields 欄位

```yaml
---
id: lc-two-sum              # REQUIRED. unique slug. prefix by domain: lc- / ai- / bq- / sd-
domain: leetcode            # REQUIRED. leetcode | ai | bq | system-design
title: Two Sum              # REQUIRED. human-readable
tags: [hash-map, array]     # topics/patterns. drives filtering + grouping
difficulty: easy            # easy | medium | hard  (leetcode & system-design; omit for bq/ai)
status: learning            # new | learning | review | mastered
mastery: 2                  # 0–5 self-rating. 0 = just saw it, 5 = could teach it
last_reviewed: 2026-07-04   # ISO date (YYYY-MM-DD). empty if never reviewed
next_review: 2026-07-08     # ISO date. COMPUTED by the CLI — don't hand-edit
source: https://leetcode.com/problems/two-sum/   # optional link
visibility: public          # public | private   ← SAFETY BELT (see below)
---
```

### The `visibility` safety belt 安全帶

- The **site generator only renders `visibility: public`** files.
- Anything in `prep-private/` is `visibility: private`.
- Even if a private file is ever misplaced into the public repo, the site will **not**
  render it. Defense in depth — never rely on the folder alone.
- 網站產生器**只渲染 `visibility: public`**。就算私密檔案手滑跑進公開 repo，也不會被渲染出來。

---

## Field meanings 欄位語意

| field | who edits | notes |
|-------|-----------|-------|
| `id` | you (once) | never changes; used as the stable key across tools |
| `mastery` | you | your honest self-rating after each review |
| `status` | you or CLI | lifecycle flag |
| `last_reviewed` / `next_review` | **CLI only** | spaced-repetition scheduling writes these back |
| `visibility` | you | `public` only for things safe to show the world |

## Recommended body structure 建議內文結構 (per domain)

Tooling reads the frontmatter; the body is free markdown, but keeping these sections
consistent lets the site render nicely and the CLI generate recall prompts.

- **LeetCode**: `## Problem` → `## Pattern insight` → `## Solution` (code) → `## Complexity` → `## Recall prompt`
- **AI**: `## Idea` → `## Why / intuition` → `## Example (shapes/math)` → `## Recall prompt`
- **BQ**: STAR — `## Situation` → `## Task` → `## Action` → `## Result` → `## Maps to questions`
- **System Design**: `## Requirements` → `## Estimates` → `## High-level design` → `## Deep dives` → `## Recall prompt`

The `## Recall prompt` line is what the CLI shows you first in a quiz — you try to answer
from memory before revealing the rest.
