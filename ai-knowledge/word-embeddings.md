---
id: ai-word-embeddings
domain: ai
title: Word Embeddings (why dense vectors)
tags: [nlp, embeddings, word2vec, glove]
difficulty: easy
status: learning
mastery: 3
last_reviewed: 2026-07-04
next_review: 2026-07-09
source: https://web.stanford.edu/class/cs224n/
visibility: public
---

## Idea
Represent each word as a **dense low-dimensional vector** whose geometry encodes meaning —
so similar words sit near each other. 用低維稠密向量表示詞，語義相近 → 向量相近。

## Why / intuition
- **One-hot fails:** every word gets its own dimension, all orthogonal → dot product of any two
  distinct words is 0, so the model can't tell "cat" is closer to "dog" than to "car".
  獨熱編碼彼此正交，表達不出相似度。
- **Distributional hypothesis:** "You shall know a word by the company it keeps." A word's meaning
  = the distribution of contexts it appears in. 詞義 = 它出現的上下文分佈。
- **Embedding = structure-preserving compression:** map sparse 10⁴-dim one-hot → dense 50–300 dim,
  keeping semantic similarity. Meaning becomes **geometry** (cosine / dot product).

## Example (two philosophies)
- **Count-based (SVD):** build a word×context co-occurrence matrix `A`, factor `A = U S Vᵀ`,
  take the word vector = rows of `U·S`. (⚠️ `S` holds **singular values** σ = √λ of `AᵀA`, *not*
  eigenvalues. U = direction, S = importance.)
- **Prediction-based (word2vec skip-gram):** predict context words from a center word; uses a
  sigmoid with negative sampling, not a full softmax.
- **Hybrid (GloVe):** log-bilinear objective so `dot(w_i, w_j) ≈ log(co-occurrence)`; captures
  probability **ratios**.

## Recall prompt
> Why can't one-hot vectors express similarity, and what's the one-sentence idea that fixes it?
> (one-hot vectors are orthogonal → dot product 0; distributional hypothesis → learn dense vectors
> where nearby = similar)
