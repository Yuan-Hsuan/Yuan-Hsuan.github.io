---
id: ai-claude-basic-idea
domain: ai
title: The Basic Idea of Claude — Assistant, Not a Chatbox（Claude 的基本概念）
tags: [claude, ai-assistant, agents, llm-products]
mastery: 1
source: https://anthropic.skilljar.com/claude-101/
visibility: public
---

## 1. Idea: Assistant ≠ Chatbox（助理不只是聊天框）
A chatbox only *talks back*; an assistant **does things**. Claude can read and write
files, run code, search the web, call external tools, and carry a multi-step task to
completion. The chat window is just **one interface** to it — the conversation is how it
communicates, not what it *is*.

## 2. Why / intuition: One Engine, Many Bodies（一顆引擎，多種載體）
The same underlying model powers many different products. Each product wraps the engine
with a different **body** — different tools, context, and permissions:

* **claude.ai** — the familiar chat app (web / desktop / mobile).
* **Claude Code** — the same engine living in the terminal and IDE, with file-system and
  shell access, so it works like a coding teammate instead of a Q&A box.
* **Embedded surfaces** — Chrome extension, Slack… Claude shows up inside the apps where
  the work already happens（跑到你工作的地方，而不是把你拉去聊天室）.
* **Claude API** — the raw engine that other companies build *their* products on.

The mental model: **capability = model + tools + context**. Swap the body and the same
model becomes a different product. That's why "Claude" isn't one app — it's an assistant
available through many apps.

## 3. Example
Ask the chat app "what's in my project folder?" and it can only guess. Ask Claude Code
the same question and it **runs `ls`, reads the files, and answers from evidence** —
same model, different tools, completely different usefulness.

## Recall prompt
Why is "Claude is an assistant, not a chatbox" more than a slogan? Name three surfaces
Claude ships in, and explain what changes between them if the model is the same.
