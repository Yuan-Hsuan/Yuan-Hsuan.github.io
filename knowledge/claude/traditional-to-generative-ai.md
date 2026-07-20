---
id: ai-traditional-to-generative-ai
domain: ai
title: Traditional AI → Generative AI — Emergent Abilities（傳統 AI 到生成式 AI）
tags: [ai-foundations, transformers, emergent-abilities, generative-ai]
mastery: 1
source: https://anthropic.skilljar.com/claude-101/
visibility: public
---

## 1. Idea: Three Things Made LLMs Possible（三個條件湊齊）
Modern LLMs took off when three developments landed together:

* **Architecture breakthroughs** — especially the **Transformer (2017)** ("Attention Is All
  You Need"), which lets a model weigh every word against every other word, so it scales to
  huge amounts of text.
* **Vast digital training data** — internet-scale text for the model to learn from.
* **A leap in compute** — one chip can't hold or crunch a model this big, so you need
  hardware specialized for neural-net math *and* a lot of it.

### Zoom in: the hardware（算力那一塊）
* **CPU → GPU → TPU** — increasingly specialized for the matrix math neural nets run on.
  CPU = a few strong all-rounders; **GPU** = thousands of small cores doing the same math
  in parallel (built for graphics, turns out perfect for neural nets); **TPU** = Google's
  **ASIC** built *only* for tensor/matrix multiply — less flexible, far more efficient at
  that one job. Rule of thumb: further right = more specialized, more efficient, less general.
* **Computing cluster（運算叢集）** — one chip still isn't enough, so you wire thousands of
  GPUs/TPUs together with very fast networking and run them as *one* giant machine (a TPU
  one is called a "pod"). The model or the training data is split across chips (model /
  data parallelism). The real bottleneck is often the **network between chips** — the heart
  of AI infra.

## 2. Why It's Different: Emergent Abilities（差別在「湧現能力」）
Traditional AI was **pre-programmed** — hand-written rules, or a separate model trained per
task. Generative AI isn't: past a certain scale, skills nobody trained for just *appear*.
That's an **emergent ability**（湧現能力）. Concretely, one model can now:

* **Adapt to new small tasks** with no retraining — you just describe it or show a couple
  of examples (in-context learning).
* **Reason step by step** through a problem, instead of blurting a single answer.

## 3. Current Limits（現在的天花板）
Powerful, but bounded. Four limits to keep in mind:

* **Knowledge cutoff** — it only knows what was in its training data; nothing after the
  cutoff date unless you feed it (tools, search, your files).
* **Hallucinations** — it can state wrong things confidently; verify anything load-bearing.
* **Context window** — it can only "see" a bounded amount of text at once; past that edge
  drops out of view.
* **Complex reasoning** — long, multi-step problems can still trip it up.

Ties back to [[ai-claude-basic-idea]]: capability = model + tools + context — and every
piece has an edge.

## Recall prompt
> What three developments made modern LLMs possible? Give the one term for skills that
> appear at scale without being trained for, and name two limits that still apply.
