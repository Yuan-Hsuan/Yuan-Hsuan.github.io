---
id: ai-description
domain: ai
title: Description — The 3 P's of Telling AI What You Want
tags: [claude, ai-fluency, description, prompting]
mastery: 1
source: https://anthropic.skilljar.com/ai-fluency-framework-foundations/
visibility: public
---

## 1. Idea: Description is the skill of being clear（描述 = 把想要的講清楚）
The second D of [[ai-fluency]]. Once [[ai-delegation]] decides *what* to hand off, Description
is *how you say it*. The plain-language version is [[ai-good-prompt-structure]] ("brief it like
a coworker"); the 3 P's are the sharper lens — a checklist for what a complete brief contains.

## 2. Product（要什麼）— describe the result, not the topic
Say exactly what a *good* output is: its **form, format, length, and what "done" looks like.**
"Write about delegation" is a topic; "a 150-word note, 3 numbered points, each with a bold
title" is a product. If you can't picture the finished thing, AI has to guess — and it will.
(Can't picture it *at all*? You're not ready to describe → [[ai-vague-requirements]].)

## 3. Process（怎麼做）— guide the approach, not just the goal
Tell it *how* to get there when the method matters: **think step by step, use this framework,
show your reasoning, ask me before you assume X.** You're not micromanaging — you're handing
over the path you'd take, so it doesn't invent a worse one. Skip this when any reasonable path
is fine; add it when the *how* is load-bearing.

## 4. Performance（怎麼互動）— set how it behaves *with* you
This is about the collaboration, not the single output: **the role/persona it plays, tone,
how verbose, and when to push back.** "Act as a skeptical reviewer and challenge my claims"
produces a very different session than "be encouraging." Set it once and it colors everything.

## 5. Worked example（把三個 P 疊在一起）
Weak: *"Help me prep for interviews."*
Strong, all three P's:
> **(Product)** Give me 5 behavioral questions with a one-line "what they're really testing."
> **(Process)** For each, ask *me* to answer first, then critique — don't hand me a model answer.
> **(Performance)** Be a blunt bar-raiser; if my answer is vague, say so directly.

Same request, but now AI knows the result, the method, *and* how to act. That's Description.

## 6. Six basic techniques（六個描述的基本招式）
The 3 P's are the lens; these are the concrete moves. Each one lives under a P:

* **Give context（給背景）** → *Product.* Say what you want, *why*, and the relevant background —
  the AI can't read the situation you're carrying in your head.
* **Show examples（給範例）** → *Product.* Show the output style or format you expect; one good
  example beats a paragraph of description.
* **Specify constraints（設限制）** → *Product.* Pin down length, format, and what to **exclude** —
  negative space is as load-bearing as positive.
* **Break complex tasks into steps（拆步驟）** → *Process.* Walk it through one step at a time
  instead of one giant ask.
* **Ask the AI to think first（先想再答）** → *Process.* Give it room to reason before answering
  ("Before answering, think through the problem carefully…") — quality jumps.
* **Define the AI's role or tone（定角色語氣）** → *Performance.* Tell it who to be ("a skeptical
  reviewer") and how to sound; it colors the whole session.

## Recall prompt
> Name the 3 P's of Description. Which one is about the *single output*, and which is about the
> *whole collaboration*? Give a weak prompt and rewrite it with all three.
