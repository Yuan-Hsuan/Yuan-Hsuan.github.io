---
id: ai-pre-train-vs-fine-tune
domain: ai
title: Pre-train vs Fine-tune — and What You Can Actually Train
tags: [ai-foundations, training, fine-tuning, lora, generative-ai]
mastery: 1
source: https://anthropic.skilljar.com/claude-101/
visibility: public
---

## 1. Idea: Training Is Two Stages

### **Pre-training** = **base model**
* Pre-training is the first step, which involves training the model from scratch on **large unlabed corpora** scraped from the internet, books and social media. 
* This phase provides the model with the ability to acquire the general understanding of language, syntax, and factual information and generate human-like content.
* This is the giant, expensive stage — the cluster compute.

### **Fine-tuning = take that base model and specialize**
Fine-tuning is the advanced phase that employs more domain-specific datasets to fine-tune the model’s parameters, customizing it to the specific nuances of a task or domain. The technique significantly enhances the model’s knowledge, aligning it with particular industry standards.
Two common steps:
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
