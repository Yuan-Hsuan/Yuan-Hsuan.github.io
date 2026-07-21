---
id: ai-delegation
domain: ai
title: Delegation — Deciding What to Do WITH AI vs. Yourself
tags: [claude, ai-fluency, delegation, judgment]
mastery: 1
source: https://anthropic.skilljar.com/ai-fluency-framework-foundations/
visibility: public
---

## 1. Idea: Delegation is cutting the work, not handing it all over（分派 = 切工作）
The first D of [[ai-fluency]]. Before you prompt anything, you decide **which parts of a
task you keep and which you give to AI**. A bad split wastes both sides — you either
babysit something AI could've done alone, or you outsource the one part that needed *your*
judgment and get a confident, wrong answer.

## 2. Three questions to make the split（切之前先問三題）
* **Vision（願景）** — What's the whole task for, and what does a *good* result actually look like? If you can't picture "good," you can't judge the output later.
* **Breakdown（拆解）** — What are the separate bits of work needed to get there? A task is never one lump — it's drafting + fact-checking + formatting + deciding.
* **Judgment check（判斷點）** — Which of those bits need *human* expertise, creativity, or judgment? Those you keep. The rest are candidates to hand off.

## 3. Then pick a mode for each bit（每一塊再選合作模式）
Delegation isn't finished when you decide "AI does this part" — you still choose *how* you
work on it, from the three modes: **Automation**（要結果就好）, **Augmentation**（一起想、留在
迴圈裡）, or **Agency**（放手讓它自己跑、你監督）. Same task, different bits, different modes.

## 4. Why it matters（Example）
Writing these very notes: the **vision** was "durable notes I can actually revise from," so
"good" meant accurate + in my own style. **Breakdown** = draft → check the model specs →
fit my format → decide what stays public. The **judgment bits** — is this claim true? does
this go on a public site? — I kept for myself; the drafting I *augmented* with AI, thinking
together instead of just taking output. Get the split wrong and no amount of clever
prompting saves you.

## 5. How working engineers actually split it（工程師真實的分派做法）
Two concrete demonstrations worth copying:

* **[Addy Osmani](https://addyosmani.com/blog/ai-coding-workflow/) — "scope management is everything."** He never hands the model a big
  monolithic task. He writes a `spec.md` himself, then prompts one step at a time —
  *"let's implement Step 1 from the plan"* — testing each before the next. Big requests, he
  says, produce code that feels like *"10 devs worked on it without talking to each other."*
  What he *keeps*: the spec, the review, the quality gates. What he *hands off*: the
  execution inside those guardrails.
* **[EclipseSource](https://eclipsesource.com/blogs/2025/04/08/ai-native-dibe-coding-delegation/) — don't delegate the deterministic stuff.** Renaming symbols, organizing
  imports, bumping a version across 100 files → use traditional tools, not AI (guaranteed
  accuracy). Better move: *"ask the AI to write a **script** that automates the analysis"* —
  shift it from dull laborer to **toolsmith**. And *do* delegate **underdefined** tasks (a
  new UI component, a prototype) — LLMs are good at filling blanks with plausible defaults.

**The pattern under both:** keep the *judgment* (spec, review, "is this right?"), hand off the
*execution* — and if a bit is fully deterministic, don't delegate it at all, script it.

## Recall prompt
> What three questions do you ask to split a task between you and AI? After you decide a bit
> goes to AI, what's the *next* decision you still have to make?
