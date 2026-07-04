---
id: ai-attention
domain: ai
title: Attention (scaled dot-product)
tags: [transformers, attention, deep-learning]
difficulty: medium
status: learning
mastery: 2
last_reviewed: 2026-07-04
next_review: 2026-07-09
source: https://arxiv.org/abs/1706.03762
visibility: public
---

## Idea
Attention lets each token **pull information from every other token**, weighted by relevance.
每個 token 依「相關度」從其他所有 token 取資訊，權重是學出來的。

## Why / intuition
A word's meaning depends on context. Attention computes, for each query token, a
**weighted average of value vectors**, where the weights come from how well the query
matches each key. 相關度 = query 跟 key 的相似度 → softmax → 拿去加權平均 value。

## Example (shapes/math)
For sequence length `n`, model dim `d_k`:

```
Q, K, V : (n, d_k)
scores  = Q @ K.T            # (n, n)   query·key similarity
scaled  = scores / sqrt(d_k) # keep variance ~1 so softmax isn't saturated
weights = softmax(scaled)    # (n, n)   each row sums to 1
out     = weights @ V        # (n, d_k) weighted average of values
```

The `/ sqrt(d_k)` matters: without it, large dot products push softmax into tiny gradients.
除以 sqrt(d_k) 是為了控制方差，否則 softmax 會飽和、梯度變小。

## Recall prompt
> Write the scaled dot-product attention formula and say why we divide by sqrt(d_k).
> (softmax(QKᵀ/√d_k)·V ; the scale keeps dot-product variance ~1 so softmax stays in a good gradient region)

<!-- Links to my CS224n notes live in the private prep repo / course repo. -->
