---
id: ai-llm-vs-classifier
domain: ai
title: LLM vs Classifier — When the Boring Option Wins
tags: [ai-foundations, classification, system-design, guardrails, generative-ai]
mastery: 1
source:
visibility: public
---

## Idea

Routing free-form text into a **fixed, closed set of categories** is one of the oldest, cheapest
problems in machine learning. It does not need a generative model.

The reflex now is to reach for an LLM, and the reflex is understandable — a prompt gets you a
working version this afternoon with **zero labeled data**. But if the set of categories is fixed and
you have history, you already own a labeled dataset and never noticed: **every case a human has
already resolved is a `(text, correct label)` pair.**

So the real question is never "LLM or classifier". It's **which one belongs in the hot path, and
when do you switch.**

## Why / intuition

A classifier wins the steady state on four things, and only one of them is cost:

1. **Fixed latency.** A linear model over a vector is microseconds. An LLM call is hundreds of
   milliseconds and occasionally seconds, and you don't control which.
2. **Testable.** You can write a regression test with a held-out set and a number. "The prompt seems
   good" is not a test.
3. **Explainable.** When it puts a ticket in the wrong bucket, you can point at the features that
   did it. That matters the moment the output pages a human.
4. **Freezable — this is the underrated one.** A trained classifier is an artifact you version
   alongside your code. A prompt-based classifier sits on top of a model that **your provider can
   update or deprecate**, and its behavior can change overnight with nobody on your team touching a
   line of code.

The cost objection people raise against classifiers — *"but then I have to label data, stand up
training, retrain when things change"* — is mostly folklore for text classification. Order of
magnitude, for a few thousand to a few tens of thousands of examples:

| Approach | Hardware | Training time |
|---|---|---|
| TF-IDF + linear model (logistic regression / SVM) | **a laptop CPU** | **seconds** |
| Embedding + logistic regression | GPU or API for the embedding step only | **minutes** (the fit itself is seconds) |
| Fine-tune a small encoder (MiniLM / DistilBERT class, ~100M params) | **one ordinary GPU** | **10–30 minutes** |

*(Orders of magnitude, not precise figures — they move with dataset size and text length.)*

Retraining is a **cron job, not a project**. Getting this wrong in a design discussion is expensive,
because you end up conceding a weakness that isn't real. This is not the same universe as
fine-tuning a multi-billion-parameter generative model ([[ai-pre-train-vs-fine-tune]]) — it's three
orders of magnitude smaller.

## The pattern: bootstrap → steady state

The strongest answer isn't "don't use the LLM." It's a timeline where both have a job.

```
Week 1     LLM, zero-shot          ships immediately, needs no labels
           │
           ├─ every routed item + every human correction = a labeled example
           ▼
Month 2+   Classifier in the hot path      fast, testable, frozen, explainable
           LLM keeps the low-confidence tail   the genuinely open-ended inputs
```

1. **Ship the LLM version first.** It's correct precisely *because* you have no labeled data yet.
2. **Let it earn its replacement.** In production it generates the dataset the classifier needs —
   its own outputs, corrected by whoever consumes them downstream.
3. **Swap the hot path once the data exists** — for the four reasons above, not for cost.
4. **Keep the LLM on the tail.** Put a **confidence threshold** on the classifier; anything below it
   doesn't get auto-routed. That tail is where inputs are actually open-ended, which is where a
   generative model is genuinely better than a fixed label set.

Two-way door: step 1 is cheap to reverse, and it buys the thing step 3 requires.

## Guardrails, when the LLM *is* in the path

Anything feeding a deterministic downstream system needs these, or you've moved the failure from
"wrong answer" to "corrupted pipeline":

| Guardrail | What it actually means |
|---|---|
| **Enforce structure** | Function calling / JSON schema, validated on receipt (e.g. Pydantic) — not "please reply in JSON" |
| **Validate, then fall back** | Parse fails → retry once → fall back. Never pass unvalidated output downstream |
| **Lower the temperature** | Classification and extraction want low variance, not creativity |
| **Separate data from instructions** | User-supplied content is *data*. Treat it as instructions and you've built a prompt-injection hole |
| **Gate side effects** | Anything that changes state — refunds, reboots, deletions — gets a rule check or a human, never the model alone |
| **Degrade, don't die** | LLM times out → fall back to the deterministic path. Reduced quality beats an outage |

## How you know it works

Stop asking *"is the output right?"* and start asking *"how often does it agree with a human?"*

Hold out a set of cases people have **already** labeled by hand, run the system over them, and
report the **agreement rate**. That gives you a defensible number instead of a vibe, and the
score distribution tells you where to put the confidence threshold.

## Recall prompt

> A team wants to auto-route support tickets into ten fixed buckets, and argues an LLM prompt does
> it today with no labeled data. They're right — so what do you ship first, what replaces it, what
> triggers the swap, and which of the four reasons for swapping is *not* about cost?

> Related: [[ai-tfidf-vs-embedding]] · [[ai-pre-train-vs-fine-tune]] · [[ai-traditional-to-generative-ai]]
