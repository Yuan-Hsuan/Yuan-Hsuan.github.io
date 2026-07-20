---
id: ai-pre-train-vs-fine-tune
domain: ai
title: Pre-train vs Fine-tune — and What You Can Actually Train（預訓練 vs 微調）
tags: [ai-foundations, training, fine-tuning, lora, generative-ai]
mastery: 1
source: https://anthropic.skilljar.com/claude-101/
visibility: public
---

## 1. Idea: Training Is Two Stages（訓練分兩段）
* **Pre-training（預訓練）** — the model reads internet-scale text and learns to predict the
  next token. Output = a **base model**: a powerful autocomplete that knows language and the
  world, but isn't yet a helpful assistant. This is the giant, expensive stage — the cluster /
  compute from [[ai-traditional-to-generative-ai]].
* **Fine-tuning / post-training（微調）** — take that base model and *specialize* it. Two common steps:
  * **SFT (supervised fine-tuning)** — train on curated `instruction → good answer` pairs so
    it follows instructions.
  * **RLHF / preference tuning** — humans rank responses; the model learns to prefer the
    helpful, harmless ones. This is what turns a raw base model into a chat assistant like Claude.

Mental model: **pre-training grows the brain; fine-tuning teaches it manners and a job.**

## 2. Can We Train This Ourselves? — LoRA（我們自己做得到嗎？）
Depends which part:

* **Pre-train from scratch** — no. Needs a cluster, huge data, and a lot of money. Big labs only.
* **Full fine-tune** — needs the model's open weights *and* serious GPUs (you hold every weight
  plus optimizer state in memory at once).
* **LoRA / QLoRA** — **yes, this is the accessible path.** Instead of updating all billions of
  weights, you **freeze the base model and train tiny "adapter" matrices** slotted into its
  layers (*low-rank* = far fewer numbers to learn). Cuts trainable parameters by orders of
  magnitude (up to ~10,000× in the LoRA paper), so you can fine-tune a big open model on **a
  single GPU**. **QLoRA** adds quantization (shrink the base to 4-bit) to fit even bigger models.

**The catch — you can only fine-tune a model whose weights you can get:** open-weights models
(Llama, Mistral, Qwen…). **Closed models you generally can't fine-tune yourself** (no weights;
at most a provider may offer a hosted fine-tune API). **Claude you don't fine-tune at all** —
you steer it with prompt + context + tools（[[ai-claude-basic-idea]]）.

## 3. Example
Want a model that writes in your company's tone, from 500 examples?

* **Closed model (Claude):** don't fine-tune — put the examples + rules in the prompt/context
  (few-shot), or retrieve them at runtime (RAG).
* **Open model (Llama):** LoRA-fine-tune on the 500 examples on one GPU in a few hours; you ship
  a small **adapter file** (a few MB) that sits on top of the frozen base model.

## Recall prompt
> Name the two training stages and what each produces. Why does LoRA make fine-tuning possible
> on a single GPU, and which kind of model can you *not* fine-tune yourself?
