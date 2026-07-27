---
id: ai-claude-model-family
domain: ai
title: The Claude Model Family — Picking a Tier, and What "Reasoning" Means
tags: [claude, claude-api, model-selection, extended-thinking, test-time-compute]
mastery: 1
source: https://anthropic.skilljar.com/claude-with-the-anthropic-api/287722
visibility: public
---

## 1. Idea: One Family, Three Tiers（同一家族的三個檔位）
Claude ships as a family of models that trade **intelligence against cost and latency**. The
tier names are stable across generations, so the tier — not the version number — is what you
actually pick. Model IDs are plain strings with no date suffix; that string is what goes in
`model=`.

|  | **Claude Opus** | **Claude Sonnet** | **Claude Haiku** |
|---|---|---|---|
| **Model ID** | `claude-opus-5` | `claude-sonnet-5` | `claude-haiku-4-5` |
| **Description** | Highest level of intelligence | Intelligent model that balances quality, speed, cost | Most cost-efficient and latency-optimized model |
| **Cost per MTok (in / out)** | $5 / $25 — high | $3 / $15 — medium | $1 / $5 — low |
| **Comparative latency** | Moderate | Fast | Fastest |
| **Context window** | 1M | 1M | 200K |
| **Max output** | 128K | 128K | 64K |
| **Supports reasoning** | Yes — `{"type": "adaptive"}`, and it is **on by default** | Yes — `{"type": "adaptive"}` | Yes, but the older style — `{"type": "enabled", "budget_tokens": N}`, and it rejects `effort` |
| **Best used for** | Advanced software development, especially large-scale architecting · long-running tasks that require sustained focus · strategic planning with multi-step problem solving | Common coding tasks · document creation and editing · content marketing and copywriting · data analysis and visualization · image analysis · process automation | Quick code completions and suggestions · content moderation and filtering · data extraction and categorization · language translation · Q&A and knowledge retrieval · **real-time user interaction and high-volume text processing** |

Prices are 2026-07; Sonnet 5 is running an introductory $2 / $10 through 2026-08-31.

Model choice is a **product decision, not a quality ranking**. A chat widget that answers in
300 ms with Haiku beats a "smarter" answer that arrives in 20 seconds; a nightly refactor job
nobody is watching should just use Opus.

Note the spread: **Opus costs 5× Haiku on both sides**, and if Opus also thinks for 2,000
tokens before answering, the real gap on a single request is far wider than 5×. That is the
whole reason the tier decision matters.

```python
# The same call, three product decisions.
client.messages.create(model="claude-haiku-4-5",  max_tokens=256,   messages=[...])  # live chat
client.messages.create(model="claude-sonnet-5",   max_tokens=16000, messages=[...])  # everyday work
client.messages.create(
    model="claude-opus-5", max_tokens=64000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},                                                # hard problem
    messages=[...],
)
```

Rule of thumb: **start at Sonnet.** Move up to Opus only when you can point at a task Sonnet
is actually failing; move down to Haiku when latency or volume — not quality — is the binding
constraint（[[ai-claude-basic-idea]]）.

## 2. Why: What "Reasoning" Actually Means（reasoning／extended thinking 到底是什麼）
"Supports reasoning" does **not** mean a different algorithm. It is the same next-token
prediction — the model has just been trained to **write out a private scratchpad of thinking
tokens first, then answer.**

Why that helps is a compute argument. A transformer does a **fixed amount of computation per
token**: one forward pass through a fixed number of layers. If a problem needs more steps than
that fixed depth can hold, the model has nowhere to put them — unless it **serializes the work
into tokens**. Each thinking token it writes becomes input to the next forward pass, so
generating 2,000 thinking tokens buys roughly 2,000 forward passes' worth of computation on
one question. This is **test-time compute（推論期算力）**: spend more tokens at inference
instead of more parameters at training.

So reasoning is a **knob, not a switch** — four settings, and the last one is the trap:

| `thinking` setting | What it does | Where it works |
|---|---|---|
| `{"type": "adaptive"}` | The model decides whether to think and how deep; you tune the spend separately with `output_config: {"effort": "low"…"max"}` | The current standard. Also enables interleaved thinking — it can think *between* tool calls |
| `{"type": "enabled", "budget_tokens": N}` | You hand it a fixed thinking-token ceiling. N must be ≥ 1024 and below `max_tokens` | The older style. Still correct on Haiku 4.5 and Sonnet 4.5; on Opus 5 / Sonnet 5 the API **refuses the request** |
| `{"type": "disabled"}` | No thinking at all | Most models. On Opus 5, only while `effort` is `high` or lower — pair it with `xhigh` or `max` and the API refuses |
| *(field omitted)* | **Depends on the model** — never assume "unset means off" | Opus 5 → runs adaptive anyway (**it thinks by default**); Opus 4.8 / 4.7 → no thinking; Sonnet 5 → adaptive |

"The API refuses the request" is worth spelling out: you get an **`invalid_request_error`
(HTTP 400) instead of an answer** — the request is thrown out *before* the model runs, so the
SDK raises an exception rather than returning text, and nothing is billed. Retrying is
pointless; the fix is always to change the code. That is why switching model generations is a
breaking change and not just a behavior change.

Two more consequences follow directly:

* **You pay for thinking.** Thinking tokens are billed as **output** tokens — the expensive
  side. They also count against `max_tokens`, which caps *thinking + answer together*, not
  just the answer. Port tight-`max_tokens` code to a model that thinks by default and replies
  start getting truncated.
* **You don't get to read it.** The raw chain of thought is never returned. Current models
  default to `display: "omitted"` — the thinking block comes back with empty text — and
  `display: "summarized"` gets you a summary, never the original.

**One correction to the slide:** the course's table marks Haiku as *"Supports reasoning: No"*,
which was true of the Haiku generation it was drawn from. **Haiku 4.5 does support extended
thinking**, just in the older `budget_tokens` form. So the durable version of the rule is:
*the cheap tier gets reasoning last, and in the more manual form.*

## Recall prompt
> Name the three tiers and the deciding factor for each. Then explain why writing thinking
> tokens makes a model better at hard problems — what does a transformer *not* have enough of
> without them, and what do you pay for it?
