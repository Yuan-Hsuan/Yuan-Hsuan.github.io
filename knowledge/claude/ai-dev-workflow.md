---
id: ai-dev-workflow
domain: ai
title: Building With AI — A Repeatable Explore → Spec → Build → Verify Playbook
tags: [claude, ai-fluency, workflow, prompting, development]
mastery: 1
source: https://code.claude.com/docs/en/best-practices
visibility: public
---

> My own working guideline for building anything non-trivial with AI. Synthesized from
> Anthropic's Claude Code best practices, [Harper Reed](https://harper.blog/2025/02/16/my-llm-codegen-workflow-atm/),
> and [Addy Osmani](https://addyosmani.com/blog/ai-coding-workflow/). Uses the 4D skills:
> [[ai-delegation]] · [[ai-description]] · [[ai-fluency]].

**At a glance:** `Explore → Spec → Plan → Build a chunk → Verify → Commit → loop`.

![The workflow as a flowchart: explore, spec, and plan happen before any code; then a build → verify → commit loop runs one chunk at a time](knowledge/claude/ai-dev-workflow.svg)

The counter-intuitive rule: **spend ~1/3 of total effort BEFORE any code gets written.**
Anthropic's finding — the explore + plan phases are the *cheapest in tokens and the most
valuable in outcome.* Jumping straight to code produces a polished solution to the wrong problem.

## 1. Phase 1 — Explore & Spec（發想：目標是一份 spec，不是一個感覺）
Don't start with "build me X." Start by turning a fuzzy idea into a written spec. Harper Reed's
move: tell the AI *"Ask me one question at a time so we can develop a thorough, step-by-step
spec for this idea"* — it interviews *you* until the idea is sharp (this is [[ai-vague-requirements]]
in action). Then: *"compile our findings into a developer-ready specification."*

* **Existing codebase? Read before you spec（改舊系統，先讀再想）:** have AI explore first —
  file structure, dependencies, how similar features were already done *here* — while it
  **writes nothing.** Skip this and it invents a design that fights your codebase. (Greenfield
  project → skip straight to the interview.)
* **When to STOP ideating (the signal):** the brainstorm hits a *natural conclusion* — the AI's
  questions stop surfacing anything new, and you can picture the finished thing. The concrete
  test: **could a stranger build it from your `spec.md` without asking you a single question?**
  If yes, stop. If no, you're not done — but if you're inventing *nice-to-haves*, you've overshot.
* **Time-box it (my rabbit-hole guard):** ~20–30 min for a feature-sized task. The spec should
  cover requirements, data, error handling, and how you'll test it — nothing more. Perfecting the
  spec past "buildable" is procrastination wearing a productive costume.

## 2. Phase 2 — Plan into right-sized chunks（拆成剛好的步驟）
Hand the spec back and ask for a step-by-step build plan, then break it into chunks. The sizing
rule (Harper Reed): each step **small enough to implement + test safely, but big enough to move
the project forward.** Too big → the output feels like "10 devs who never talked to each other"
(Osmani); too small → coordination overhead outweighs the help. Output = an ordered checklist.

## 3. Phase 3 — Build ONE chunk at a time（一次只做一塊）
Never hand over the whole plan at once. Osmani: *"let's implement Step 1 from the plan"* — build,
verify, *then* Step 2. **Also decide per chunk (from [[ai-delegation]]):** is it deterministic
(rename, config, mechanical)? Don't delegate it — script it or use a real tool. Only spend the AI
on the bits that genuinely need reasoning.

## 4. Phase 4 — Verify every chunk（驗收：給 AI 一把能自己驗的尺）
Anthropic's single highest-leverage practice: **give the work a way to be verified.** Not "looks
right" — a concrete pass/fail signal:
* runnable **tests** (does the suite go green?),
* a **screenshot** to compare against the intended UI,
* a **lint / typecheck** that returns OK or FAIL,
* the actual **numbers/output** matching what the spec said "done" looks like.

**And machine pass ≠ done — read the diff yourself.** Tests only cover what tests cover; a green
suite can hide a quietly-broken interface. Reading AI's diff line by line is the Discernment D of
[[ai-fluency]] made concrete: the reviewer is still you.
If you can't state how a chunk gets verified, you under-specified the Product in Phase 1 — go back.

## 5. Phase 5 — Commit & loop（驗過就 commit，再回頭）
Chunk passed → **commit it** — every green chunk is a rollback anchor — then the next chunk.
Chunk failed → feed the error + code back, fix, re-verify ("rinse and repeat"); if the fixing
spirals, **reset to the last green commit** instead of patching a mess. And if you're on the
**5th revision and it's still wrong**, don't write a harder prompt —
that's a *delegation* problem ([[ai-delegation]]): you handed off a bit that needed you, or one a
cheaper deterministic step should've narrowed first. Drop back a phase, don't push harder.

**When it goes off, the AI is a mirror（AI 走偏時，把它當鏡子）:** a bad answer is rarely the
model being dumb — it's usually where my brief was ambiguous. Don't blame the tool; read the wrong
output as a diagnostic of my own **Description** ([[ai-description]]): which P was underspecified?
Fix the brief, not my frustration. The reviewer — and the describer — is still me.

## 6. The four failure modes this guards against（這套流程在防四件事）
1. **Straight-to-code** → solves the wrong problem. Fix: Phase 1 spec first.
2. **One giant prompt** → incoherent mess. Fix: Phase 2–3 chunks.
3. **"Looks good" with no proof** → silent bugs. Fix: Phase 4 machine signal + your own diff read.
4. **No rollback anchors** → one bad chunk poisons everything after it. Fix: Phase 5 commit
   every green chunk.

## Recall prompt
> What are the five phases, and roughly how much of your effort goes in *before* any code?
> What's the stop-signal for ideation, and the one highest-leverage thing to set up for verification?
