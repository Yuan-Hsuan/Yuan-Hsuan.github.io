---
id: ai-managing-claude-md
domain: ai
title: Managing CLAUDE.md — Guidance, Not Enforcement, So Keep It Lean
tags: [claude-code, claude-md, hooks, configuration]
mastery: 1
source: https://anthropic.skilljar.com/claude-code-in-action
visibility: public
---

## The trap: the file that only grows（越補越長，越長越沒人聽）
Hit a problem → add a rule → repeat, and soon Claude starts ignoring parts of the file. That's
not a bug: **CLAUDE.md is guidance, not enforced configuration.** Every line competes with every
other line for attention, so the longer it gets, the less reliably any single rule is followed.
The goal isn't to write everything down — it's to keep the file tight. **Leaner = more followed.**

## 1. Hard rules don't belong here — use hooks（硬規則交給 hook）
Before writing a rule, ask: is this a convention, or a line that must never be crossed?
"Never push to main" in CLAUDE.md is a **polite request** — Claude follows it *most* of the time,
and "most of the time" isn't good enough for something dangerous. A **pre-tool-use hook** is code
that runs before Claude acts and can actually **block** the action — real enforcement. Hard rules
→ hooks; CLAUDE.md keeps the softer conventions.

## 2. The four locations（四個檔案一起載入，各管各的事）
All four load together at launch and stack — nothing gets dropped.

| Location | Who controls it | What it's for |
| --- | --- | --- |
| **Managed policy** | your org's platform team | org rules; you can't exclude it |
| **User** | you, machine-wide | personal preferences that follow you across every project |
| **Project** | the team, checked into the repo | conventions shared with everyone on the repo |
| **Local** | you, git-ignored | personal notes for *this* repo only — e.g. architecture decisions for your own branch that shouldn't affect the team |

## 3. Split up a big file with imports（imports 只整理、不減量）
A long project file can be split with `@.claude/conventions/code-style.md`-style imports. But at
launch every import is **expanded inline right where you referenced it** — everything still loads
up front. **Use imports to organize, not to shrink the load.** Context read stays the same.

## 4. Phrasing: specific + checkable, and name the replacement（規則要驗得了、要給替代品）
* **Be specific and checkable** — "follow best practices" can't be checked, so it can't be followed.
  "Put new API routes in `src/api/handlers`, one per file" — you can look at the result and
  immediately tell if it was done right. That's the bar. (Same principle as the **Product** P in
  [[ai-description]], and as the one constraint on `/goal` in [[ai-steering-long-sessions]]:
  if you can't verify it, you can't ask for it.)
* **Name the replacement** — "don't use default exports" leaves the door open (then what?).
  "Use **named** exports, not default exports" closes it: nothing left to misinterpret.

## 5. Emphasis is a budget（大寫強調是預算，別全場都喊）
"IMPORTANT" and "YOU MUST" raise a rule's priority — but only **relative to the quieter lines
around it**. If every rule shouts, nothing stands out. Spend the emphasis on the two or three
rules that really hurt when broken; let the rest sit at normal volume.

## 6. Keep it under revision（把它當 production code 維護）
The file is never finished. When Claude does the wrong thing, treat it as a **bug report against
CLAUDE.md** — say "add that to the CLAUDE.md" and let it write the rule. And the flip side:
**if you can't justify a line, delete it.** Leaner file, more of it followed.

## Recall prompt
> Why does a longer CLAUDE.md get *less* obeyed? Where do hard rules belong instead, and what do
> imports NOT do? Name the two phrasing fixes that make a rule stick.
