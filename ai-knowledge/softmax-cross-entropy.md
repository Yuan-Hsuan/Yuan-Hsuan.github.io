---
id: ai-softmax-cross-entropy
domain: ai
title: Softmax + Cross-Entropy
tags: [deep-learning, classification, loss]
difficulty: medium
status: learning
mastery: 2
last_reviewed: 2026-07-04
next_review: 2026-07-09
visibility: public
---

## Idea
**Softmax** turns raw scores (logits) into a probability distribution; **cross-entropy** measures
how far that distribution is from the true label. Together they're the standard classification head.
Softmax 把分數變機率，cross-entropy 量「預測分佈離正確答案多遠」。

## Why / intuition
- Softmax: `p_i = exp(z_i) / Σ_j exp(z_j)` — exponentiate (all positive) then normalize (sums to 1).
- Cross-entropy for a one-hot target: `L = -log(p_correct)`. Only the correct class's probability
  matters; push it toward 1. 目標是把正確類別的機率推向 1。

## Example (shapes/math)
```
logits z : (batch, C)
p        = softmax(z)          # (batch, C), each row sums to 1
loss     = -log(p[correct])    # scalar per example, then mean over batch
```
The beautiful part — the gradient of softmax+CE w.r.t. logits is just:
```
dL/dz = p - y_onehot           # (batch, C)
```
Predicted minus target. That clean form is *why* they're always paired. 梯度就是「預測 − 真實」。

## Two traps 兩個坑
1. **Numerical stability:** subtract `max(z)` before exp (softmax is shift-invariant) to avoid overflow.
2. **Don't double-softmax:** frameworks' `CrossEntropyLoss` takes **raw logits**, not probabilities.

## Recall prompt
> What's the gradient of softmax + cross-entropy w.r.t. the logits, and why is that convenient?
> (`p - y`; predicted minus target → simple, stable backprop, which is why the two are always paired)
