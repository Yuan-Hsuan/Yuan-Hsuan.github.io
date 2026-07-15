# site/ — the static site generator

`build.py` **is the whole website**. It reads the repo's markdown notes + a little JSON,
and writes one `../index.html` that GitHub Pages serves. That's it — no backend, no
database, no build tool.

> Think of it as a **compiler, not a website**: inputs (markdown + JSON + a few Python
> constants) → output (one static `index.html`). The HTML lives inside Python because
> HTML is what this program *emits*.

## Core characteristic: zero dependencies 零依賴

The entire generator uses **only the Python standard library** — nothing to `pip install`.

- **f-string *is* the template engine.** A template engine just fills placeholders:
  `<h1>{{ name }}</h1>` + data → `<h1>Phoebe</h1>`. Python's f-string does exactly that
  (`f"<h1>{name}</h1>"`) — so there's no need for Jinja2 or any third-party templating.
- **Why zero-dep here:** this site is small and edited only occasionally. No dependencies
  means it never rots — `python3 build.py` just runs, months later, with no version bumps,
  no broken `npm install`, no supply-chain risk. Match the tooling to the problem size:
  small + stable + single-author → dependencies are overhead, not leverage.
- The browser side is the same philosophy: **vanilla JS**, no framework. The rotating
  knowledge globe is hand-drawn on a `<canvas>` (per-frame redraw of dots + edges) rather
  than pulling in a 3D or animation library.

## Structure of `build.py` (top to bottom)

| Layer | What it does | Key functions |
|---|---|---|
| **1 · Config constants** | The knobs: content dirs, GitHub user, curated picks, résumé (`EXPERIENCE`), calendar window | top of file |
| **2 · Content layer** | Parse markdown + frontmatter → `cards`; build the knowledge graph. Data only, no HTML | `parse_frontmatter`, `collect`, `build_graph` |
| **3 · Data pipeline** | Fetch real GitHub contributions / events / LeetCode counts at build time; cache to JSON so offline builds still work | `load_contrib`, `load_activity`, `load_solved` |
| **4 · Section builders** | Data → HTML fragments — this is where Python and HTML meet, real numbers interpolated into the layout | `hero_html`, `experience_html`, `activity_html`, `system_html`, … |
| **5 · Static templates** | All CSS and all JS, held as plain string constants | `HEAD`, `SCRIPT` |
| **6 · Assembly** | `page()` concatenates `HEAD` + sections + `SCRIPT`; `main()` orchestrates the run and writes `index.html` | `page`, `main` |

**Why section builders use f-strings but `HEAD`/`SCRIPT` don't:** CSS and JS are full of
`{ }` braces, which collide with f-string syntax. So the static assets stay as raw `"""`
constants and receive data through a few placeholders (e.g. `__BUILD_MONTH__`) or
`json.dumps` injection — avoiding brace-escaping hell.

## Real data or nothing

Every number on the page (solved count, calendar counts, write-up totals) is **computed
from the data sources at build time** — never hand-typed into copy (that's how a
26-vs-27 drift bug once happened). If a data source is unreachable and has no cache, the
section hides itself rather than showing fake content.

## Run

```bash
python3 site/build.py     # regenerate index.html (fetches GitHub data, falls back to cache)
open index.html           # eyeball it locally
```

Before committing, verify the inline JS: extract the `<script>` blocks and run
`node --check` on them.

> Design rationale, the seven visual principles, the rejected-ideas list, and the decision
> log live in [`../DESIGN.md`](../DESIGN.md). Working protocol is in [`../CLAUDE.md`](../CLAUDE.md).
