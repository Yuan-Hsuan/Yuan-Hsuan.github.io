---
id: ai-transformer
domain: ai
title: How a Transformer Works — Parallel Reading, Sequential Writing
tags: [transformer, attention, tokens, kv-cache, inference]
mastery: 1
source: https://anthropic.skilljar.com/claude-with-the-anthropic-api/287722
visibility: public
---

## 1. Idea: A Stack of Layers That Predicts the Next Token
A transformer takes a sequence of token vectors and returns a probability distribution over the
entire vocabulary for what comes next. Every layer in the stack does exactly two things:

* **Attention** — the tokens look at each other and exchange information.
* **FFN (feed-forward)** — each token is transformed on its own, with no reference to its
  neighbours.

That split *is* the architecture. **Attention is the only place where tokens talk to each
other**; everything else processes each position independently. Stack that block 30–100 times,
train it to predict the next token, and you have a language model.

## 2. The Pipeline: Text In, One Token Out

```
text → tokenizer → token IDs → embedding + position
     → N × [ attention → FFN ]
     → logits over the whole vocabulary → sample one token
```

A **token is not a word.** It is a chunk of characters that a statistical procedure (BPE) found
worth keeping together: start with every character as its own token, then repeatedly merge the
most frequent adjacent pair, a few tens of thousands of times. The tokenizer knows nothing about
grammar — it only counts.

| Input | Tokens | Why |
|---|---|---|
| `cat` | 1 | Short and common — kept whole |
| `unbelievable` | ~3 (`un` `believ` `able`) | Long and rarer, so it is spelled out of common pieces |
| `cat` with a leading space | 1, but a **different** token from `cat` | Whitespace is usually glued to the front of a word |
| `1234` | often 2–4 | Specific number strings are rare, so they fragment |
| Common Chinese character | 1 | Frequent enough to earn its own entry |
| Rare Chinese character | 2–3 | Falls back to being assembled from UTF-8 bytes |

The rule of thumb: about **4 characters per token** in English, and roughly **1–2 tokens per
character** in Chinese. That `un` + `believ` + `able` split looks like prefixes and suffixes, but
that is a coincidence — frequent letter sequences just happen to line up with morphemes.

## 3. Attention: How Tokens Decide Who to Listen To
Each token projects itself into three different vectors, and the whole mechanism is a weighted
average built out of them:

| Vector | Role | Intuition |
|---|---|---|
| **Query** ($Q$) | What this token is looking for | "I am a pronoun — who do I refer to?" |
| **Key** ($K$) | What this token advertises about itself | "I am a person's name, mentioned earlier" |
| **Value** ($V$) | What this token actually hands over if attended to | The content that gets mixed in |

$$\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V$$

Read it right to left: $QK^{\top}$ scores every query against every key — that is "how much
should I care about you". Dividing by $\sqrt{d_k}$ stops those dot products from growing so large
that softmax saturates into a one-hot spike. Softmax turns the scores into weights that sum to 1.
Then those weights take a **weighted average of the value vectors** — that is the information
actually flowing between tokens.

Two additions that matter:

* **Multi-head** — run several independent Q/K/V sets in parallel and concatenate. Each head is
  free to learn a different kind of relationship: one tracks syntax, another tracks which noun a
  pronoun refers to, another tracks position.
* **Causal mask** — when training a next-token predictor, position $t$ must not see positions
  after it, or the answer leaks. So the upper triangle of the score matrix is set to $-\infty$
  before the softmax. **Every token attends only backwards**, which is exactly what makes the KV
  cache in §5 possible.

## 4. Why It Beat the RNN
An RNN computes $h_t$ from $h_{t-1}$. Step $t$ literally cannot begin until step $t-1$ finishes,
so a 500-word sentence is 500 dependent steps — and a GPU, which is thousands of cores waiting
for work, sits mostly idle.

Attention has no such chain. Every position is scored against every other position **in one
matrix multiplication**, so the whole sequence is processed at once and the hardware runs full.
That is the entire reason models of this size are trainable at all: not that attention is smarter
than recurrence, but that it **parallelizes**.

The bill for that comes as $O(n^2)$: $n$ tokens means $n^2$ pairwise scores. Double the context
and you quadruple the attention work. That is the real reason context windows have a ceiling, and
why long contexts cost disproportionately more（[[ai-traditional-to-generative-ai]]）.

## 5. Prefill vs Decode: Reading Is Parallel, Writing Is Not
This is the part that surprises people, and it follows directly from §4.

**Prefill — reading your prompt.** Every token of the prompt goes in **simultaneously**. There is
no left-to-right reading; attention lets each token see all the others in a single pass. A
100,000-token prompt is one big parallel computation.

**Decode — writing the answer.** Here it really is one token at a time, and it has to be: token
$n+1$ cannot be chosen until token $n$ exists, because token $n$ is part of its input. **Each
generated token costs one full forward pass through the entire model.**

The saving grace is the **KV cache**: the key and value vectors for tokens already processed do
not change (thanks to the causal mask — nothing looks forward), so they are stored and reused
instead of recomputed on every step. That cache is also what **prompt caching** bills against —
it is why re-sending an identical prefix is dramatically cheaper than sending it fresh.

## 6. What This Explains About the API
Four things that look like arbitrary pricing rules are really just consequences of §5:

1. **A long prompt is accepted quickly, but the reply trickles out.** Prefill is parallel; decode
   is sequential. Time-to-first-token and tokens-per-second are two different problems.
2. **Input tokens cost far less than output tokens** — a 5× gap on Opus 5. Input is absorbed in
   one batched pass; every output token is its own trip through the whole network.
3. **Thinking tokens are expensive** because they are *output* tokens — generated one at a time,
   billed at the output rate（[[ai-claude-model-family]]）.
4. **Fixed compute per token is what makes reasoning work.** One forward pass is a fixed number of
   layers, so a problem needing more steps than that depth has nowhere to go — unless the model
   writes intermediate tokens and feeds them back in. Each thinking token buys another full
   forward pass. That is test-time compute, and it is a property of this architecture, not a
   feature bolted on top（[[ai-pre-train-vs-fine-tune]]）.

## Recall prompt
> What are the two operations in a transformer layer, and which one is the only way tokens share
> information? Then explain why reading a prompt can be done in parallel but generating a reply
> cannot — and use that to explain why input tokens are cheaper than output tokens.
