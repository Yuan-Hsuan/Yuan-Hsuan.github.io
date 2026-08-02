---
id: ai-tfidf-vs-embedding
domain: ai
title: TF-IDF vs Embedding — Matching Words vs Matching Meaning
tags: [nlp, text-representation, embeddings, retrieval, classification]
mastery: 1
source:
visibility: public
---

## Idea

Both turn a piece of text into a **vector of numbers** so a machine can compare two texts.
The whole difference is **what those numbers mean**.

**TF-IDF** builds a **sparse** vector: one dimension for every word in your vocabulary. The value in
each slot answers *"how much does this word characterize this document?"* — it goes up when the word
appears often **in this document**, and up again when the word is **rare across the whole corpus**.
Nothing is learned; it's counting.

**Embedding** builds a **dense** vector — a few hundred to a few thousand dimensions, all non-zero,
produced by a trained model. No single dimension means "the word *router*". The vector is a position
in a learned space where **texts that mean similar things land near each other**.

## Why / intuition

> **TF-IDF matches words. Embeddings match meaning.**

That one line predicts almost every practical difference.

TF-IDF has no idea that *"my wifi keeps dropping"* and *"the connection is unstable"* are the same
complaint — they share almost no words, so their vectors are nearly orthogonal. An embedding model
puts them right next to each other, because it was trained on enough text to learn that.

The flip side is the part people forget: **TF-IDF's literalness is sometimes exactly what you
want.** If the thing you're matching on is an error code, a stack frame, a log signature, or a part
number, "meaning" is a distraction — you want the string. And an embedding model will happily rate
`E_TIMEOUT_0x51` as similar to `E_TIMEOUT_0x52`, which may be two completely unrelated bugs.

Two more differences that decide real designs:

- **Cost.** TF-IDF is arithmetic over a word count — free, instant, runs on a laptop. An embedding
  means a model forward pass per document, so you pay in GPU time or API calls, and you pay again
  every time you change the model.
- **Explainability.** With TF-IDF you can point at the exact words that made two documents match.
  With embeddings you get a similarity score and no reason.

## Example (shapes)

Say your corpus is 50,000 support tickets and your vocabulary is 50,000 words.

| | TF-IDF | Embedding |
|---|---|---|
| Vector length | **50,000** (= vocabulary size) | **768** or **1024** (fixed by the model) |
| Filled slots | maybe 20 non-zero (the words in this ticket) | **all of them** non-zero |
| Where it comes from | counting | a trained model's forward pass |
| Grows when… | your vocabulary grows | never — dimension is fixed |

**The TF-IDF weight itself:**

```
weight(word, doc) = tf(word, doc) × log( N / df(word) )
                    ─────────────    ──────────────────
                    how often here    how rare overall
```

`N` = number of documents, `df` = how many documents contain the word.

Concretely, with `N = 50,000` tickets:

- **"the"** appears in ~50,000 of them → `log(50000/50000) = 0` → **weight 0**. Useless for telling
  documents apart, and the formula zeroes it out automatically. That's the whole trick.
- **"5GHz"** appears in 500 of them → `log(50000/500) ≈ 4.6` → a strong signal.

## When to use which

| Situation | Reach for | Because |
|---|---|---|
| Error codes, log signatures, stack frames, IDs | **TF-IDF / BM25** | You want the literal string, and you want to see *why* it matched |
| Free-form human text, lots of paraphrase | **Embeddings** | Different words, same complaint |
| Small dataset, need a baseline today | **TF-IDF + a linear model** | Trains in seconds on CPU and is shockingly hard to beat |
| Production search / retrieval | **Both — hybrid** | Run BM25 and dense retrieval, merge the two candidate lists, then rerank |

**Hybrid is the honest default for retrieval.** Lexical search nails exact identifiers and rare
terms; dense search nails paraphrase. They fail on different inputs, which is exactly why combining
them beats either one. If you build a RAG pipeline over logs or tickets and only do dense retrieval,
the queries you'll silently lose are the ones where someone pasted an exact error string — the
easiest queries you had.

## Recall prompt

> Both represent text as a vector. What does a single dimension mean in each one, and which of the
> two would you use to find past bugs matching `E_TIMEOUT_0x51` — and why is that the opposite of
> the obvious answer?

> Related: [[ai-llm-vs-classifier]] · [[ai-transformer]] · [[ai-pre-train-vs-fine-tune]]
