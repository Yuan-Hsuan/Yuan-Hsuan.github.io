# Yuan-Hsuan.github.io — Project Protocol

Public "learning in public" site. GitHub Pages serves the committed `index.html`,
which is generated — **never hand-edit it**.

> Personal habits & decision style are inherited from `../CLAUDE.md`.
> **The visual/design contract is `DESIGN.md` — read it before any change.**
> Its §2 principles, §9 scaling playbook, and the rejected-ideas list are binding.

## Her visual taste（美感守則 — 這個網站的判準）

- Warm paper ground + near-black ink + **ONE gold accent moment per viewport**; serif
  display + mono for all metadata/numbers (`tabular-nums`); wide layouts (~1680px) with
  varied compositions — never uniform single-column stacks; a long vertical list is a smell.
- **Two materials:** square = instrument/data (may carry crop-mark corner ticks placed
  OUTSIDE the boundary); round = controls only. Never both on one block.
- **Text motion = typewriter only.** Rejected: decode/glitch text, marquees, emoji
  decoration, gradient-hero SaaS clichés, dark mode (single cream theme, always).
- **Real data or nothing** — fake/sample content in a UI gets called out. If real data is
  unavailable, hide the section instead.
- **Few words.** She deletes self-explaining copy on sight ("好多餘").

## Blind spots to quietly cover on this site（默默補位）

- **Mobile / a11y / reduced-motion:** she never asks — own that layer silently in every
  change (fallbacks for the pinned scrolly, keyboard paths, focus rings, static variants).
- **Public-exposure safety:** she moves fast; before anything ships, verify no contact
  info, employer internals, or `mind/` content reaches public output, and that public
  claims match her résumé/BQ material (`../mind/`).
- **Design outrunning content:** when she reaches for another visual tweak while the
  contribution streak or note count is thin, gently point the effort back to writing.

## The one-file architecture

Everything is `site/build.py` (stdlib only): section builders → HTML/CSS/JS template
constants → data pipeline (see DESIGN.md §7). Content sources:

- `leetcode/**/*.md` + `knowledge/**/*.md` + sibling repo
  `../Standford-cs224n-nlp/notes/concepts/` (all carry SCHEMA frontmatter)
- `site/solved.json` (LeetCode API dump), `site/contrib.json` + `site/activity.json`
  (GitHub calendar + events, auto-fetched每次 build、離線用快取)
- `EXPERIENCE` / `CURATED` constants in `build.py` (résumé + start-here picks;
  résumé source of truth is `../mind/resume/resume.md`, private)

**SAFETY BELT:** only `visibility: public` frontmatter ever renders (`collect()`).
Never bypass it. No contact info / employer internals / `mind/` content in public output.

## Workflow (every change)

```bash
python3 site/build.py          # regenerate index.html (fetches GitHub data, cache fallback)
open index.html                # eyeball it — Yuan reviews locally
# verify inline JS before committing:
#   extract <script> blocks → node --check
```

- Iterate in small batches exactly as Yuan asks; open the page after each build.
- **Commit/push only when Yuan says "commit+push"** (push = live deploy on Pages).
- **Content push ⇒ site rebuild (standing rule, 2026-07-08):** when she says commit+push for
  public-site **content** — leetcode write-ups here, or the sibling CS224n notes
  (`../Standford-cs224n-nlp/notes/concepts/`) — that push **includes** rebuilding this site
  (`build.py`) → JS check → commit + push, so the notes **and** the contribution calendar go
  live together. Scoped to site content only — never trigger it for `mind/` or unrelated repos.
- Record every visual decision in `DESIGN.md` §11; propose rule changes there first.
- Don't re-propose rejected ideas (DESIGN.md §9 list) without new evidence.

## Numbers discipline

Every stat on the page (466 solved, 26 write-ups, calendar counts…) is computed from the
data sources at build time. Never hand-type a number into copy — that's how the
26-vs-27 drift bug happened.

## Gotchas learned the hard way

- Contribution-calendar slicing must be **anchored to today** (trim the front for Sunday
  alignment, never the tail) — we once shipped a calendar that cut off the last 3 days.
- The editor panes read real repo files (including `build.py` itself via the
  "SAFETY BELT" line search); renaming that comment breaks the pane extraction.
- Mockup HTML files for review live OUTSIDE this repo (e.g. `~/github/mockup-*.html`) —
  anything committed here goes live.
- `.pages` files are zip + snappy; the résumé was extracted once already —
  `../mind/resume/resume.md` is now the readable source.
