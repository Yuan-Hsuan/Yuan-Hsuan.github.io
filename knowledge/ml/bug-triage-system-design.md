---
id: ai-bug-triage-system
domain: ai
title: Designing a Bug Triage System — Deterministic First, Probabilistic Last
tags: [system-design, classification, retrieval, guardrails, generative-ai, ai-foundations]
mastery: 1
source:
visibility: public
---

## The problem

Reports arrive as messy text — a support ticket, a crash log, a test failure. Before anyone can fix
anything, someone has to answer **"whose problem is this?"** and ideally **"what probably caused
it?"** On a team of any size that routing step quietly eats a large share of senior engineering
time, because it's the one step that can't start until a human has read the thing.

So: build a system that reads the report and outputs **owning team + likely root cause**.

The instinct in 2026 is to put the whole report in a prompt and ask. That version works on day one
and is the wrong destination. This note is the full design, and more importantly **the order the
decisions have to be made in** — because the order is where most of the quality comes from.

> **The governing principle:** *don't dissolve a precise signal into a fuzzy one and then pay a
> model to approximate it back.*

---

## Layer 1 — What is already structured?

**Ask this before anything else, every time.** A report is never pure prose. Buried in it are
**facts**: an error code, a module name, a firmware or build version, a device model, a stack frame,
a timestamp.

Those are not things to be *similar to*. They are things to **filter on**.

The mistake is to embed the whole blob and do similarity search over it. An embedding model will
cheerfully decide `E_TIMEOUT_0x51` and `E_TIMEOUT_0x52` are nearly identical — they differ by one
character — when they may be two completely unrelated subsystems. You had a key and you turned it
into a smell.

So layer 1 is a **parser**, and it's ordinary code: regex, a log grammar, a JSON field. No ML.

### How much authority does a code get?

Structured doesn't mean trustworthy. Real-world error codes are often *symptoms* — a timeout can be
produced by anything downstream of the thing that actually broke. So grade them, and grade them with
evidence rather than intuition:

| How concentrated is this code historically? | How to use it |
|---|---|
| Only ever produced by one subsystem | **Routing table.** Look it up, done. 100% precision, microseconds, fully explainable |
| Strongly points at two or three | **Hard filter** on the candidate set — then run the fuzzy layers *inside* that subset |
| Appears everywhere (generic timeouts, `UNKNOWN_ERROR`) | **Just a feature.** Don't filter on it; pass it down and let the next layer weigh it |

**You can measure which tier a code belongs in.** Take the resolved history, group by error code, and
look at the distribution of final root-cause owners. A code whose resolutions land 98% in one team
earns tier 1. A code spread evenly across nine teams earns tier 3. This is a query, not a judgment
call — and it's re-runnable, so the tiers stay honest as the product changes.

**Why this layer pays so well:** filtering the candidate pool from 50,000 to 3,000 doesn't just make
retrieval faster, it makes it *better*. Every fuzzy method has a false-positive rate; shrinking the
pool shrinks the absolute number of ways to be wrong.

---

## Layer 2 — Does the fuzzy part need a *generative* model?

Now you're left with the free-form narrative. What you do with it depends on what you want out.

**If the output is one of N fixed buckets** — which team owns this — that's **closed-set
classification**, and it doesn't need a generative model. Detail in [[ai-llm-vs-classifier]]; the
short version:

- You already have labels. Every previously resolved report is a `(text, correct owner)` pair.
- A classifier wins the steady state on **fixed latency, regression-testability, explainability, and
  freezability** — a prompt sits on a model your provider can change under you overnight.
- Training one is not the project people imagine: TF-IDF + a linear model is **seconds on a CPU**;
  fine-tuning a small encoder is **10–30 minutes on one ordinary GPU**. Retraining is a cron job.

**The honest sequence is a timeline, not a verdict:**

```
Week 1     LLM, zero-shot            ships now, needs no labels
           │
           ├─ every routed report + every human correction = a labeled example
           ▼
Month 2+   classifier in the hot path        fast · testable · frozen · explainable
           LLM keeps the low-confidence tail
```

Ship the LLM version first *because* you have no labeled data — and ship it knowing its real job is
to **generate the dataset that replaces it**. This is a two-way door: cheap to reverse, and it buys
the thing the better version requires.

---

## Layer 3 — Retrieval: "what did we do last time?"

Routing says *who*. Root cause needs *precedent* — find the resolved reports that look like this one
and put them in front of whoever (or whatever) writes the answer.

Two ways to find "similar", and they fail on different inputs ([[ai-tfidf-vs-embedding]]):

| | Finds | Misses |
|---|---|---|
| **BM25 / TF-IDF** (lexical) | exact identifiers, rare terms, error strings, function names | paraphrase — *"wifi keeps dropping"* vs *"connection is unstable"* |
| **Dense / embedding** | the same complaint in different words | precise tokens — treats `0x51` and `0x52` as neighbours |

**Which is why production retrieval runs both.** The failure modes are complementary, so the union
of the two candidate lists has meaningfully better recall than either. The classic silent loss from
dense-only retrieval is the *easiest* query you had: someone pasted the exact error string.

### Merging the two lists

Their scores are **not comparable** — BM25 is an unbounded sum (0 to ~30, scales with query length),
cosine similarity is bounded (−1 to 1, usually bunched in 0.6–0.9). `0.5·bm25 + 0.5·cosine` is
nonsense; the BM25 term dominates by construction.

**Option A — Reciprocal Rank Fusion.** Throw away the scores, keep the ranks, because ranks *are*
comparable:

```
score(d) = Σ  1 / (k + rank_i(d))            k is conventionally 60
         systems
```

Worked example, `k = 60`:

```
BM25   : D3(1)  D7(2)  D1(3)
Dense  : D1(1)  D3(2)  D9(3)

D3 = 1/61 + 1/62 = 0.03252    ← found by both
D1 = 1/63 + 1/61 = 0.03227    ← found by both
D7 = 1/62        = 0.01613    ← lexical only
D9 = 1/63        = 0.01587    ← dense only
```

**What `k = 60` buys you:** it flattens the top of each list. Without it, rank 1 scores 1.0 and rank
2 scores 0.5 — a cliff, so whichever system shouts loudest wins. With `k = 60`, `1/61 ≈ 1/62`, so
**"both systems found it" outweighs "it was #1 in one of them."** That's exactly the consensus
property you want, and it needs no tuning and no training.

**Option B — let a reranker absorb the problem.** If the pipeline already has a **cross-encoder
reranker**, there is nothing to fuse. A cross-encoder scores the `(query, document)` pair *together*
in one forward pass, so it doesn't care where a candidate came from and its scores are natively on
one scale:

```
query ─┬→ BM25  top-100 ─┐
       └→ dense top-100 ─┴→ union & dedupe (~150–200) → rerank → top-10
```

The extra cost is one BM25 pass (milliseconds, essentially free) plus 50–100 more documents through
the reranker. **The fusion problem disappears if you already have a reranker** — prefer this, and
keep RRF for when you don't.

---

## Layer 4 — Where the LLM actually earns its place

After three layers of filtering, retrieval, and classification, the generative model gets a small,
structured, high-signal context. Now it's doing something only it can do:

1. **Synthesizing the root-cause explanation** — turning *"here is the failure signature, here are
   the three most similar resolved reports, here are the candidate functions"* into prose a human
   can act on. Genuinely open-ended output. No classifier does this.
2. **The low-confidence tail.** Put a confidence threshold on the classifier; anything below it
   isn't auto-routed. Those are the reports that are actually novel — the right place for a model
   that generalizes.
3. **Cold start.** Before labels exist, it *is* the system (layer 2's week 1).

### Guardrails, non-negotiable

Anything feeding a deterministic downstream system needs all of these, or you've upgraded "wrong
answer" into "corrupted pipeline":

| Guardrail | Concretely |
|---|---|
| **Enforce structure** | Function calling / JSON schema, validated on receipt — not "please reply in JSON" |
| **Validate then fall back** | Parse fails → retry once → fall back. Never pass unvalidated output downstream |
| **Low temperature** | Extraction and classification want low variance, not creativity |
| **Data ≠ instructions** | Report text is *data*. Treat it as instructions and you've built a prompt-injection hole — and reports are attacker-writable |
| **Gate side effects** | Anything that changes state (auto-close, reassign, reboot, refund) goes through a rule or a human. The model advises; it does not act |
| **Degrade, don't die** | Model unavailable → fall back to rules + retrieval. Reduced quality beats an outage |

---

## The whole thing

```
raw report
    │
    ▼
┌─────────────────────────────────────────────────┐
│ 1. PARSE            plain code, no ML           │
│    error code · module · version · stack frame  │
└─────────────────────────────────────────────────┘
    │
    ├── tier-1 code? ──────────────► routing table → DONE (no model touched)
    │
    ▼
┌─────────────────────────────────────────────────┐
│ 2. FILTER           deterministic constraint    │
│    50,000 candidates → 3,000                    │
└─────────────────────────────────────────────────┘
    │
    ├──────────────────────┬──────────────────────┐
    ▼                      ▼                      │
┌───────────────┐   ┌──────────────────────────┐  │
│ 3. CLASSIFY   │   │ 3'. RETRIEVE precedent   │  │
│    owning team│   │  BM25 ∪ dense → rerank   │  │
└───────────────┘   └──────────────────────────┘  │
    │ low confidence?      │                      │
    ▼                      ▼                      ▼
┌─────────────────────────────────────────────────┐
│ 4. GENERATE        small structured context     │
│    root-cause narrative · novel-case routing    │
│    schema-enforced · no side effects            │
└─────────────────────────────────────────────────┘
```

Read it as a funnel: **every stage only pays for the precision it needs**, and each stage hands the
next one a smaller, cleaner problem. The expensive, unreliable component sits at the *end*, seeing
the least data, with the tightest constraints.

---

## How you measure it — per layer, not end-to-end

One global accuracy number tells you nothing about where to spend the next week.

| Layer | Metric | Why that one |
|---|---|---|
| **Parse** | **Coverage** — % of reports where the fields were extracted | It either found the code or it didn't; this is a parser bug rate, not a model score |
| **Filter** | **Leak rate** — how often the correct answer was filtered *out* | The one catastrophic failure. A wrong filter is unrecoverable downstream |
| **Retrieve** | **recall@k** (k = 50–100) | This layer's only job is *don't lose it*. Ordering is the reranker's problem; anything dropped here can never be recovered |
| **Rerank** | **precision@10** / MRR | Now ordering is the job |
| **Classify** | **Agreement rate** with human labels on a held-out set of already-resolved reports | Gives a defensible number instead of a vibe, and the score distribution tells you where to set the confidence threshold |
| **Generate** | Human spot-check + **downstream rework rate** | There is no automatic metric for a good explanation. Rework rate is the honest proxy |

**The recall-vs-precision split is the important idea here.** Early stages optimize *recall* — never
drop the right answer. Late stages optimize *precision* — put it on top. Getting this backwards
(a strict, high-precision retriever) silently caps the whole system's ceiling.

---

## Trade-offs, all in one view

| Decision | Cheap option | Expensive option | Choose the expensive one when |
|---|---|---|---|
| Extract fields | regex / parser | LLM extraction | Format is genuinely unstable across sources; then still validate against a schema |
| Use the error code | routing table | feature in a model | The code is historically diffuse (tier 3) |
| Assign owner | classifier | LLM prompt | You have no labels yet, or the label set isn't actually closed |
| Find precedent | BM25 only | + dense + reranker | Reports are written by humans in varied words — i.e. almost always |
| Merge two lists | RRF (no tuning) | cross-encoder reranker | You need ordering quality, not just consensus — and note the reranker replaces the fusion step |
| Explain root cause | template from top-1 precedent | LLM synthesis | The output is read by a human who needs reasoning, not a link |

**The one-line version of the whole table:** *pay for probabilistic machinery only where the input
is genuinely open-ended.*

---

## What this design does *not* solve

Say these out loud before someone else does:

1. **Cross-boundary defects.** The symptom surfaces in subsystem A, the cause lives in subsystem B.
   Every layer above reasons from the symptom, so every layer routes it to A. This is the hardest
   remaining class and it's usually where the last 20% of errors live.
2. **Unfaithful error codes.** Tier assignment is historical. A refactor can silently change which
   subsystem emits a code, and the routing table is now confidently wrong. Re-run the tiering on a
   schedule and alert when a code's distribution shifts.
3. **Feedback-loop poisoning.** If the classifier's own outputs become training labels without human
   correction, it trains on its own mistakes and drifts. Only *corrected* routings are ground truth.
4. **Cold start for new subsystems.** A brand-new module has no resolved history — no labels, no
   precedent. It falls to the LLM tail by construction, which is the correct behavior but worth
   stating rather than discovering.

---

## Recall prompt

> You're handed a stream of messy bug reports and asked to auto-route them. Name the four layers in
> order, and for each one say what it costs and what metric it's judged on. Then: why is it a
> mistake to embed the whole report — and why does the retrieval layer optimize recall while the
> reranker optimizes precision?

> Related: [[ai-llm-vs-classifier]] · [[ai-tfidf-vs-embedding]] · [[ai-pre-train-vs-fine-tune]]
