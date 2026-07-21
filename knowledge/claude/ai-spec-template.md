---
id: ai-spec-template
domain: ai
title: My Spec Template — the Skeleton I Fill Before Building
tags: [claude, ai-fluency, spec, spec-driven-development, workflow]
mastery: 1
source: my own — a personal take on Spec-Driven Development (Kiro · GitHub Spec Kit · Osmani · Harper Reed)
visibility: public
---

> The concrete output of Phase 1 of [[ai-dev-workflow]]. This is the skeleton I fill in a
> `spec.md` before writing code — turning a fuzzy idea into something **a stranger could build
> without asking me a question.** It's my [[ai-description]] 3 P's, generalized into fields, and
> the fields are the industry's own — this is **Spec-Driven Development**: the spec is the
> artifact, the code is its build output.

**When to use it:** anything non-trivial. Skip it for a one-line change. The point isn't
ceremony — **an hour on the spec is the cheapest hour in the project** (explore + spec is cheapest
in tokens, most valuable in outcome). Fill the fields that carry weight for *this* task.

## The skeleton（骨架）

**1 · Thesis**
The single load-bearing sentence — what this is. If I can't write it, I don't understand the
task yet.

**2 · Requirements**
- **Problem statement** — what's wrong or missing *today*, why now, and what happens if I don't fix it. The problem, not the solution. No real pain → question building at all. 需求先講清楚「痛在哪」。
- **Goals** — what a *good, finished* result IS: form, behavior, and the one sentence for "done" (the acceptance criteria). The north star the whole spec serves.
- **Scope** — for an existing system: the specific change vs. what exists *today*, what's in, and — most importantly — **what NOT to touch**. Greenfield → "build from zero".
- **Assumptions & data** — the inputs/state involved, how it behaves when things go wrong (empty, offline, malformed), and what the spec **assumes or depends on**.
- *Technique — EARS:* for a testable requirement, phrase it "when [trigger], the system shall [response]" (Kiro's syntax) — it drops straight into a task's verify.

**3 · Design**
The existing architecture, pattern, or system the solution should **resemble — or deliberately diverge from**. "Model it on how X already did it here" or "like Y, except Z." Anchoring to a known shape stops the AI from inventing a design that fights the codebase.

**4 · Tasks — each with its own verification**
An ordered checklist of **right-sized chunks**, and **every chunk carries the pass/fail signal that proves it's done** — written right next to it: a test going green, a screenshot, a lint/typecheck, the exact number. No chunk is "done" on "looks right"; a machine pass ≠ done — I still read the diff. **One chunk = one verify = one commit.**

**5 · Non-goals & constraints**
The guardrails (perf, deps, style, scope) **and** an explicit **Non-goals** list. Naming what you're *not* doing is as load-bearing as the goal — it's what stops scope creep and re-litigated decisions (every strong PRD / Shape Up pitch does this).

**6 · Good enough? — the stop decision**
*My addition — most specs stop at "done", not "good enough".* The same test fires at every gate: *spec good enough → build; each task verified → commit; whole thing good enough → ship.*
- **Definition of Done met?** — the acceptance criteria + every task's verify green + constraints held. Any miss → not done.
- **Is more worth it?** — above that floor, does the next improvement beat its cost? If not, **ship**; polishing past that is the compulsive trap, not quality (Simon's *satisficing*：過了門檻就收手).

**7 · Example**
One canonical filled instance: a concrete input → expected output, or the format I want. One example beats a paragraph of description.

**8 · Roles — the agent brief**
Who the AI should be on this project (tone, verbosity, *when to push back*) and the **delegation boundary**: what I keep (judgment — the spec, the review, "is this right?") vs. what it executes. Deterministic bits get scripted, not delegated ([[ai-delegation]]). The persistent form of this is an `AGENTS.md` / `CLAUDE.md` in the repo.

**Decision records (ADR)** — a running `date → decision` list. Every non-obvious call recorded once, so I never re-argue it and a reader sees *why*.

## Filled example — the contribution-calendar timezone fix
A real one from this repo, kept tiny on purpose:

* **Thesis:** the site's click-a-day detail panel shows commits on the wrong day.
* **Requirements**
  * **Problem statement:** evening pushes drifted onto the next day's (empty) cell — the calendar looked wrong and undersold the streak; every rebuild re-shipped the error.
  * **Goals:** each day's per-repo activity lines up with the same day's green square, counts labeled honestly. Done = Jul-7's 10 contributions and its push list sit on the same cell.
  * **Scope:** change only the event-bucketing (UTC → local day) and the count label; leave the calendar layout, the scrape, and the panel UI untouched.
  * **Assumptions & data:** public Events API (UTC timestamps, no commit list when unauthenticated); offline → cached JSON, never fabricate; assumes the viewer's local tz is the intended frame.
* **Design:** keep the existing **two-pipeline** shape — scrape feeds the grid, Events API feeds the detail. The fix *aligns their day-bucketing*; not a third pipeline.
* **Tasks (each with its verify):**
  1. locate the aggregation — grep confirms a single `load_activity()`.
  2. bucket by local day — Jul-7 evening pushes now land on Jul-7.
  3. relabel "commits" → "pushes" — panel reads "N pushes".
  4. rebuild + eyeball — Jul-6 = 6/6, Jul-7 = 10/9, today matches; `node --check` passes.
* **Non-goals & constraints:** stdlib only, no new request; don't invent counts; **non-goal:** redesigning the calendar or adding auth.
* **Good enough?** Definition of Done met (cells align, labels honest, JS checks). More worth it? No — the look-ahead and per-hour precision are low-ROI nice-to-haves. Ship.
* **Roles:** AI executes the bucketing edit; I own "is the timezone logic actually right?" and read the diff. Push back if it touches more than the two functions in scope.

## Prior art（這其實是 Spec-Driven Development）
Not invented — a personal cut of a 2025–26 movement. **AWS Kiro** splits a spec into *Requirements → Design → Tasks* (with EARS); **GitHub Spec Kit** does `/specify → /plan → /tasks`; classic **PRDs** lead with a Problem statement and explicit **Non-goals**; **ADRs** are the decision log. My fields map onto all of them — the one part they mostly omit is field 6, *good enough*.

Sources: [Kiro / Spec Kit / Tessl compared — Martin Fowler](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) · [GitHub Spec Kit guide](https://intuitionlabs.ai/articles/spec-driven-development-spec-kit) · [Addy Osmani — How to write a good spec for AI agents](https://addyosmani.com/blog/good-spec/) · [Harper Reed — My LLM codegen workflow](https://harper.blog/2025/02/16/my-llm-codegen-workflow-atm/)

## Recall prompt
> Name the eight fields (+ the ADR log). Which are the standard PRD/SDD sections (Problem
> statement, Goals, Scope, Design, Tasks, Non-goals)? The "good enough" test fires at which gates,
> and what are its two parts? What does EARS give you?
