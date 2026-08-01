---
id: ai-steering-long-sessions
domain: ai
title: Steering Long Claude Code Sessions — Scope First, Then Steer
tags: [claude-code, long-sessions, plan-mode, compaction, rewind, worktrees, autonomy]
mastery: 1
source: https://anthropic.skilljar.com/claude-code-in-action
visibility: public
---

A long task is not just a scaled-up quick task. While quick tasks are simple loops (ask, work, check), complex tasks like cross-file refactoring can run for hours.

To succeed, you need two core habits: **Scope first, then steer.**

### 1. Scope First: Plan Mode

Before the AI writes any code, have it generate a blueprint.

* **Read-Only Research:** The AI reads the codebase, determines what needs to change, and proposes a plan for you to review.
* **Thorough Review:** Read the plan carefully—do not just skim. If anything is missing or incorrect, direct the AI to adjust it immediately.
* **The Payoff:** Iterating on a plan takes minutes, while cleaning up an unguided execution can take hours.


### 2. Steer While It Runs: The 5 Tools

When the AI is executing, use these tools to manage context and keep it on track:

| Tool / Shortcut | When to Use It | The Catch / Pro-Tip |
| --- | --- | --- |
| `/compact` | The context window is filling up, and you need the AI to keep going. | **Never run bare.** Always append instructions to guide the summary (e.g., `/compact Focus on the --version flag`). |
| **Rewind**<br><br>(Double `Esc`) | The AI takes a wrong turn. (Every user prompt creates a checkpoint). | It is always cheaper and faster to rewind than to prompt your way out of a mess. |
| `/goal` | You can define the "done" state better than the individual steps. | The condition must be strictly verifiable from the AI's output (e.g., all tests pass). Use `/goal clear` to cancel. |
| `/loop` | You are waiting on an external state change, like a CI run or deployment. | Hit `Esc` to stop the loop. |
| **Worktrees** | You are running multiple AI agents on the same codebase simultaneously. | Prevents agents from clobbering each other's code. Instead of sessions stepping on each other, each one gets its own independent file tree. Add a **`.worktreeinclude`** file at the root for essential git-ignored files (like `.env`). |

> **Worktree in one line:** each agent gets its own independent working folder (git history
> shared); a fresh tree grows tracked files only — git-ignored files come along only if listed
> in `.worktreeinclude` (a Claude Code feature, not native git).

These five steer a session *while it runs*; the standing guidance that carries *across* sessions
is [[ai-managing-claude-md]] — the other half of the same job.

---

### 3. The 5 Exits of the Rewind Menu

Rewind isn't just an undo button; it is a context-management tool. The menu allows you to choose exactly *what* rolls back:

* **Restore code and conversation:** A clean, full undo of a wrong turn.
* **Restore conversation:** Keep the code, but toss the sideways discussion.
* **Restore code:** Keep the discussion, but throw out the bad code.
* **Summarize from here:** Compresses everything *after* the checkpoint (great for clearing out a resolved side tangent).
* **Summarize up to here:** Compresses everything *before* the checkpoint (keeps the current implementation active while compressing long setups).

---

### 💡 Putting It Together

1. **Scope before you execute.**
2. **Direct your `/compact**` so the summary retains what matters most.
3. **Use Rewind generously** to course-correct early.
4. **Set measurable `/goals**` instead of micro-managing steps.
5. **Run parallel tasks in separate Worktrees** to avoid overlapping edits.
## Recall prompt
> Name the two habits that make long sessions work, and the five steering tools. Why is bare
> `/compact` risky, and what is the one constraint on what `/goal` can check?
