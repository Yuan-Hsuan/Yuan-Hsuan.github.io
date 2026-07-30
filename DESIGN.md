# DESIGN.md — Site Design Contract（網站設計契約）

> Single source of truth for how the site looks, reads, behaves, and **grows**.
> The implementation lives in `site/build.py` (one file: template + CSS + JS + data pipeline);
> this file is the contract behind it. House rule: **Decided once. Committed.**
> 每個視覺決策在這裡定案一次，之後不再重想。

**Change process:** propose here first (edit the rule, add a §11 log line) → Yuan approves
anything visual → implement in `build.py` → `python3 site/build.py` → eyeball `index.html`
→ commit/push only when Yuan says so.

---

## 1. Identity & audience

One-line thesis (tab title, OG title): **"The reasoning, not just the code."**

The page has one job — let a reader decide in 60 seconds that Yuan is (a) actually coding,
(b) able to explain reasoning clearly, (c) still improving.

| Reader | Time | Must get |
|---|---|---|
| Recruiter / HR | ~60 s | hero + typewriter + stats → Résumé (02) → LinkedIn CTA |
| Engineer / interviewer | ~10 min | Start here (01) → the editor (04) → a few write-ups |

Every section serves one of these two readers, or it gets cut.

## 2. Principles（違反任何一條前先來改這份文件）

1. **Show, don't tell.** The site demonstrates instead of describing: the editor shows the
   real generator source; the calendar shows real GitHub counts; the globe shows the real
   note graph. Sample/fake data is never acceptable — if the real data isn't available,
   the section hides itself.
2. **Few words = confidence.** One sentence per section lede. No self-explanations
   (the "No PDF on purpose" line died for this). Evidence and numbers over adjectives.
3. **Two materials.** Square = instrument (data blocks, cards, calendar, editor, bars —
   `border-radius: 0`, may carry crop marks). Round = control (buttons, pills, inputs,
   the pill navigator, kg side panel). Never mix: a block with corner ticks is never rounded.
4. **One text-motion language: the typewriter.** Type → hold → delete → next. No decode/
   glitch/scramble effects (tried, rejected: "好奇怪"). No marquees (tried, rejected).
5. **One accent moment per viewport.** Gold is for the focal point (typed word, rail,
   ticks, ping); everything around it stays quiet warm-grey.
6. **Honesty is the brand.** Mastery self-ratings (reader overlay only), the young streak
   caption, mistakes in write-ups — they stay. Never inflate numbers; they all come from
   one computed source and cannot drift.
7. **Zero dependencies.** Python stdlib generator; vanilla JS; the only external requests
   are Google Fonts, KaTeX, GoatCounter. Every new asset must justify itself.

## 3. Tokens

| Token | Value | Role |
|---|---|---|
| `--bg` | `#f1eee7` | page ground — warm off-white, **single theme, no dark mode** |
| `--surface` / `--surface2` | `#ffffff` / `#f5f1e8` | inputs, insets |
| `--border` | `#e3ddd0` | hairlines（永遠是暖色，不用純灰） |
| `--fg` | `#232323` | ink |
| `--muted` | `#5b5a56` | secondary text |
| `--accent` | `#40392e` | links, hovers |
| `--gold` | `#d6a878` | THE accent: typed word, ticks, rail, ping, progress |
| `--panel` | `#232323` | dark surfaces: graph, xp band, editor window, footer |
| `--easy/--medium/--hard` | `#8a8a8a/#5b5a56/#232323` | difficulty = one greyscale ramp |
| `--gh0…--gh4` | `#e7e0d1→#8f6132` | contribution ramp (gold sequential) |
| syntax | gold keywords · `#a8b78c` strings · `#79746a` comments · `#e8d5b5` defs | editor panes |
| `--ease` | `cubic-bezier(.4,0,.2,1)` | every transition |

Fonts — decided, stop re-choosing: **Fraunces** (display: h1/h2/h3, card titles, brand),
**Inter** + PingFang/Noto TC (body), **JetBrains Mono** (all metadata: kickers, labels,
numbers `tabular-nums`, code, readouts). Mono is the voice of data; body text never mono.

## 4. Layout — the band rhythm

Full-bleed bands, cream/black alternation; content in `.wrap` (1080px) / `.wrap.wide`
(1680px). Hero is the only 100svh split (text 47% | graph canvas).

| Band | Ground | Composition |
|---|---|---|
| Hero | cream + black | split; kicker · serif h1 typewriter · sub · split stats (AI first) · 3 actions |
| 01 Start here | cream | **3 black article columns left + head right** (head first on mobile) |
| 02 Experience | **black** | pinned scrolly: intro column left · **zigzag timeline** on center rail |
| 03 Activity | cream | split: head left · calendar + click-detail panel right |
| 04 The system | cream | full-width editor (dark window on cream) |
| 05 AI notes | cream | split: head left · numbered rows right |
| 06 Practice log | cream | split header · filter controls · tile grid + reader overlay |
| Footer | **black** | honesty line + links (bookend to the hero's black) |

Composition rules: never two consecutive sections with the same shape; long vertical
lists are a smell — break into grids/splits; sections carry mono eyebrows with gold
index numbers (scroll order = real information).

## 5. Components (spec by section)

- **Floating pill navigator**: serif brand "Yuan-Hsuan Wen" · section links (active =
  ink pill) · GitHub/LinkedIn external links. No dividers. Brand + externals hidden ≤640px.
- **Scroll progress**: 2px gold meter fixed at the very top.
- **Hero typewriter**: h1 "I work on `<word>`" — whole line Fraunces; typed word gold with
  block cursor; words: clean algorithms / the right data structure / NLP from scratch /
  AI infrastructure / learning in public.
- **Knowledge map** (the signature — protect it): a flat **community map** — each of the four
  domains (LeetCode / AI / Systems / Software) packs into its own cluster (hub topics central,
  rim ragged) and the four clusters **overlap into one round mass**; domain names sit in the
  open corners outside it. Monochrome dots (topics solid, notes smaller/fainter), labels:
  hub topics (count ≥ 2) at rest, notes only once their topic is focused; hover/click focuses
  node + neighbours and dims the rest; click opens the side panel → `expandCard`. Mono HUD
  readout bottom-right: real node/edge counts. Only motion is a ~1px idle bob. Pauses off-screen.
- **Black article blocks** (`.cardk`): gold mono meta · serif title · why-line ·
  tags + Read →; permanent crop marks (dim → gold on hover).
- **Experience**: 320vh+ scroll track, sticky stage; left = kicker/h2/pitch quote
  (gold-bordered serif italic)/LinkedIn CTA/one-line education; right = zigzag items on a
  center gold rail with dots, activated by scroll progress thresholds (computed from item
  count). Timeline = work only, newest first, "Currently" entry on top. Education is never
  a timeline item. Fallback to static single column ≤900px wide or ≤600px tall or
  reduced-motion.
- **Contribution calendar**: window = `CONTRIB_WEEKS` (6 for now) **anchored to today —
  trim only the front for Sunday alignment, never the tail** (bug we shipped once);
  +2 future weeks as dashed cells; 20px square cells, gold ramp; hover tooltip with real
  count ("7 contributions · Jul 4"); **click a day → detail panel on the right** listing
  per-repo commits/events from the public Events API (private repos structurally absent).
- **The editor**: mac-frame dark window in a deep `.crop` frame; file tree (role=tablist)
  switches 6 REAL files read at build time — two write-ups, an AI note, SCHEMA.md,
  build.py (reading itself, first 150 lines), generated index.html head. Real line
  numbers, palette-family syntax colors, line-by-line reveal, blinking cursor, scanline
  sweep. Pane height `clamp(300px, 58svh, 720px)`.
- **Tile grid + reader**: shopping-grid tiles (pills · serif title · ≤3 tags · "~N words" ·
  Read →); crop marks on hover; click → reader overlay (780px dialog, scrim+blur, Esc/
  scrim/✕, focus restore, KaTeX on open, `#card-<id>` deep links). **Mastery appears only
  inside the reader** — it is spaced-repetition metadata, not a public ability label.
- **Crop marks / HUD**: `.cardk/.tile` ticks sit OUTSIDE the boundary (inset −6px);
  `.crop` = always-on dim gold (dark frames); `.hud` = inside viewfinder corners, only on
  the hero graph (overflow-safe). Blocks with marks are always square (§2.3).

## 6. Motion inventory（僅此清單；新增動效 = 新決策）

1. Hero load stagger (kicker→h1→sub→stats odometers→buttons, <1.5s, once)
2. h1 typewriter loop (72ms type / 38ms delete / 1.7s hold) + block cursor blink
3. Kicker type-in on first reveal (52ms/char, starts 300ms after the fade)
4. Status ping on "Updated YYYY-MM"
5. Hero scroll cue ↓ (steps(7), hidden ≤900px)
6. Scroll reveals `.rv` (fade + 14px rise, .6s, once, `--d` stagger)
7. Odometer count-ups (900ms ease-out, on reveal)
8. Difficulty bar scaleX grow (staggered E→M→H)
9. Tile-in animation on grid render/filter (40ms stagger, capped)
10. Globe: idle rotation + birth fade-in + hover/drag physics
11. Editor line reveal per pane switch + scanline sweep (7s loop)
12. Calendar wave-in (col×30ms + row×8ms) + tooltip (.12s)
13. Hover micro-interactions ≤200ms: borders, arrow nudges, row surfaces, cell outline

Rules: reveals are once-only; nothing loops except cursor, ping, cue, scanline, globe;
`prefers-reduced-motion` disables everything (content fully visible, final values,
static globe); rAF loops pause when off-screen/hidden.

## 7. Data pipelines（真資料原則的實作面）

| Data | Source | Freshness | Failure mode |
|---|---|---|---|
| Write-ups | `leetcode/**/*.md` frontmatter+body | every build | `visibility != public` never renders (SAFETY BELT in `collect()`) |
| AI notes | sibling repo `Standford-cs224n-nlp/notes/concepts/` via `CS224N_META` | every build | skipped if repo absent |
| Solved counts | `site/solved.json` (`build_solved.py` ← LeetCode API) | manual refresh | hero/log fall back to 0 |
| Contributions | github.com/users/…/contributions (scraped levels + tooltip counts) | every build | cache `site/contrib.json` → else section hides |
| Day details | api.github.com events (public only) | every build | cache `site/activity.json` → else "no public details" |
| Editor panes | the repo's own files, incl. `build.py` reading itself | every build | missing file → tab skipped |
| Résumé | `EXPERIENCE` const, condensed from `mind/resume/resume.md` (private) | manual | no contact info ever renders publicly |

**Numbers single-source rule:** every stat on the page is computed in `page()`/builders
from these sources. Never hand-type a count into copy.

## 8. Accessibility & performance checklist

- Focus-visible rings (box-shadow, respects shape) on buttons/tiles/rows/tree tabs/close.
- Reader overlay: `role=dialog`, Esc + scrim close, focus restored to opener.
- Tiles keyboard-operable (`role=button`, Enter/Space); tree is a `tablist`.
- Inputs ≥16px font (iOS zoom); hover effects wrapped in `@media (hover:hover)`.
- Canvas globe has the write-up lists as its text alternative; HUD readout is text.
- Keep `index.html` under ~400 KB (now ~320 KB). Budget breakers → see §9.
- Keep: OG card, JSON-LD Person, sitemap, robots, canonical, GoatCounter (cookieless).

## 9. Scaling playbook（內容變多/要改進時，照這裡做）

**Write-ups 26 → 50+**
- Tile grid + filters hold fine to ~100 tiles; add a "show more" fold after ~48 if the
  section gets taller than ~3 viewports.
- `index.html` grows with embedded `body_html`. Past the 400 KB budget: emit card bodies
  to `site/cards.json` and fetch once when the reader first opens (keeps zero-framework).
- Past ~50 notes, consider per-note pages (`/notes/<id>.html`) generated by the same
  build for SEO/permalinks; tiles keep the overlay, search engines get real URLs.
- Globe: node cap by canvas width already exists; if labels crowd, raise the note-label
  depth threshold (currently `pz > 0.3`) before touching sizes.

**Curated picks（Start here）**
- Always exactly 3, hand-picked in `CURATED`. Rotate when a better exemplar exists —
  the criterion is "shows how I think", not recency or difficulty.

**AI notes 5 → more / new course**
- Keep reading from the sibling repo while CS224n is active — the notes carry standard
  SCHEMA frontmatter (`CS224N_META` retired 2026-07-17); when the course ends, move the
  final notes into `knowledge/` (already scanned).
- ≥10 AI notes: give section 05 the same filter row as the practice log.

**New domain (system-design, `sd-` per SCHEMA.md)**
- New section only at ≥5 public notes. Domain pill color comes from the existing warm
  family (e.g. `#6e6a5e`); never a new hue. Add to graph via tags as usual.

**Activity**
- As the streak matures, widen `CONTRIB_WEEKS` 6 → 12 → 20 (cell size back down to 13px
  past 12 weeks). Slicing is tail-anchored — keep it that way.
- Update the "started logging publicly in spring 2026" caption when it stops being true.

**Résumé**
- New job → new top entry replaces "Currently" (which moves into it or shrinks).
  Keep ≤5 items and balance zigzag column heights (L column = items 0,2,4…).
- Keep `mind/resume/resume.md` as the source; site bullets stay condensed
  (action + constraint + **bold result**), LinkedIn-safe altitude.

**Editor**
- Cap at 6 tabs; swap files instead of adding. If `build.py` outgrows 150 shown lines of
  interest, point the excerpt at the region that best proves the system (the safety belt).

**Deliberately rejected (don't re-propose without new evidence):** dark mode; decode/
glitch text effects; marquees; nav topbar; PDF résumé; rounded instrument blocks;
traffic-light difficulty colors; JS frameworks; hover-lift transforms on cards/tiles
(edge flicker loop — twice; hover feedback = border/shadow/ticks only); difficulty
split bar (E/M/H) as a page element; "case study" style self-referential stat copy.

**Parking lot (fine ideas, not yet earned):**

- **Domain tint on the knowledge map:** the clusters are monochrome and genuinely overlap, so
  they read by density alone. If the four groups ever stop being separable at a glance, the
  next lever is a very muted per-domain tint (the "B" mockup) — not a rainbow, and only if
  density stops carrying it. (Clustering itself shipped 2026-07-22; see §11.)

Also parked: RSS feed from write-ups; a 中文 mirror page;
OG-image auto-regeneration in CI; auto-refreshing the contribution calendar (evaluated
2026-07-08 → **not yet**: the streak is young and the calendar already refreshes on any
real rebuild, so effort belongs on content. When it's earned, do NOT ship the naive
nightly cron-commit — it churns the git history; prefer deploy-artifact via Actions
"GitHub Actions" Pages source (no commit), or a client-side fetch from a CORS source
rendered in our own style — and keep the "no backend / cookieless / fully-static" property).

## 10. Repo hygiene

- `site/build.py` is the whole implementation — template chunks as constants, builders
  per section, one motion IIFE, one globe IIFE. Dead CSS/JS gets deleted, not commented.
- Caches (`contrib.json`, `activity.json`, `solved.json`) are committed so offline
  builds work. `index.html` is generated output and is committed (Pages serves it).
- Verify before commit: `python3 site/build.py` + extract inline scripts → `node --check`.

## 11. Decision log（歷史，僅追加）

| Date | Decision |
|---|---|
| 2025 | Warm paper `#f1eee7` + ink `#232323` + gold `#d6a878`; monochrome knowledge graph; recall-then-reveal |
| 2026-07-07 | DESIGN.md becomes the contract; hero thesis; Fraunces/gold confirmed; single cream theme, no dark mode |
| 2026-07-07 | Band rhythm (cream/black), web-native no-PDF résumé, GitHub calendar, code-window "system" section |
| 2026-07-07 | Two-column splits; archive = tile grid + reader overlay; mastery → reader only |
| 2026-07-07 | Real data everywhere: editor reads repo files (incl. itself), calendar scrapes real counts, activity from events API |
| 2026-07-07 | Obsidian-style rotating globe with depth-faded labels |
| 2026-07-07 | Typewriter-only motion (decode & marquee rejected); crop marks outside SQUARE blocks; digital layer (dot grid, progress meter, scanline, HUD readouts) |
| 2026-07-07 | Start here = 3 black columns left + head right; zigzag experience on center rail; education = one line, not a timeline item |
| 2026-07-07 | Activity: 6-week window anchored to today (+2 dashed future weeks), click-a-day detail panel on the right |
| 2026-07-07 | Tab/OG title = the thesis; brand name in the pill navigator; nav dividers removed; wrap widths 1080/1680 |
| 2026-07-07 | Code cleanup: dead CSS (card2/c-*/mono), GROUPS/graph-groups removed; this document rewritten with scaling playbook |
| 2026-07-07 | Nav tabs renamed to match sections: Start here · Résumé · AI notes · Practice log (Graph tab dropped — the brand is the home link). Project protocol added as CLAUDE.md |
| 2026-07-09 | Contribution detail: bucket events by LOCAL day (UTC drift bug), label counts as "pushes" not commits (unauthenticated payloads omit the commit list) |
| 2026-07-09 | Knowledge globe: TOPICS are the first layer — only tags show labels / are clickable at rest. Note dots stay faint, unlabeled, and non-clickable until their topic is selected; problem titles never surface first (data still bipartite, gate is interaction-only) |
| 2026-07-15 | 06 reframed article-first: kicker/tab "Write-ups", h2 "Everything, written up."; AI/engineering cards sort before LeetCode. LC stats live in the hero only (difficulty bar deleted); hero gains a Software engineering column. `software-engineering` rendered as a first-class domain (honest pill/filter, not mislabeled LeetCode) |
| 2026-07-15 | Hover lift removed from tiles + cardk (flicker loop at edges) → rejected list. Scroll reveals faster: .38s, delays ×0.6 via calc(). Typewriter speed untouched. Curated picks rotated: SVD note · LC 84 · site architecture (depth × algorithm × judgment) |
| 2026-07-16 | Systems notes published (9 OS + 5 networking, three merges); `systems` first-class domain; hero = three groups (AI cs224n/claude split · Systems/SWE · LeetCode); AI section "Theory by hand, tools by habit." with per-row track labels |
| 2026-07-20 | New chapter **06 · How I build** (Write-ups → 07, nav tab added): the build-with-AI method as a flowchart — Yuan's hand-made `ai-dev-workflow.svg` inlined (data-phase hooks), click a phase box → gold highlight + detail panel; the Build→Verify→Commit loop pulses the gold "next chunk" arrow. Title names the method: "How I build software with AI." Explored 3 demo directions (playable-loop / scrollytelling / console) + a native regenerated flowchart; she chose to keep her own SVG. Mockups live outside the repo |
| 2026-07-20 | Curated pick #1 = ai-dev-workflow (AI building method); trio now workflow × LC 84 × site architecture (3 domains). `[[wikilink]]` cross-refs now resolve to clickable card-openers site-wide (`resolve_wikilinks`); dangling ones degrade to plain text |
| 2026-07-16 | Globe fix: node order scattered by stable md5 hash — index-ordered fibonacci sphere had clumped notes/tags into latitude bands (notes packed at top). Resting labels only for topics with ≥2 notes; singletons name themselves on focus |
| 2026-07-15 | Résumé synced to resume.md 7/12 overhaul: Broadcom = co-op (Mar 2021–Jun 2022, PDN bullet) + full-time (Jun 2022–Dec 2023), locations on both. Contribution calendar includes private-contribution counts (GitHub setting; counts only, no details) |
| 2026-07-22 | 03 Activity contrast fixed: the empty cell `#e7e0d1` and level-1 `#eeddc2` were the same lightness (l1 even lighter), so a 1-commit day was invisible. New ramp recedes the empty (`#e6e0d2`) and starts the gold clearly "on" (`#e8c99a → #d9a866 → #c0863c → #8f5f26`), strictly darkening — GitHub's off→on jump in the cream palette |
| 2026-07-22 | **Sphere → community map.** The rotating fibonacci globe is retired: each of the four domains now packs into its own cluster (hubs central via a 0.68 radial exponent, ragged rim via seeded jitter) and the four clusters **overlap into one round mass** — her reference `design-refs/graph-viz-node-link-layouts-reference.jpg` panel (c). Domain names sit in the open corners; no frames around clusters (rejected: per-cluster outline ring). Rotation/drag removed (nothing to rotate) — hover to focus, click a topic; touch = tap. `ci` (2-way, dead) → `dom` (4-way, load-bearing); md5 node shuffle deleted with the sphere. Groups read by density alone; muted per-domain tint parked in §9 if that ever stops working |
| 2026-07-24 | LeetCode total now auto-fetches from LeetCode's public GraphQL (`matchedUser.submitStatsGlobal`, no cookie) → real count, self-updating, cached in solved.json with offline fallback (mirrors load_contrib). Verify certificate line under the education line (§02): "Certified · Anthropic · AI Fluency: Framework & Foundations ↗" → Skilljar verify page; mono + one gold link, no badge image (name matches the verify page verbatim) |
| 2026-07-24 | Merged `software-engineering` → `systems` (was a 1-note domain; supersedes the 2026-07-15 first-class-domain entry). Domain now 3-way (leetcode/ai/systems); `systems` relabelled "Systems / Eng"; knowledge map = 3 clusters; hero "Systems / SWE" group → "Systems / Eng" single stat. |
| 2026-07-24 | 07 Write-ups: the domain `<select>` becomes a **tab row** (All · LeetCode · AI · Systems / Eng, count per tab, ordered by size). Active tab carries the single gold underline; difficulty/topic/search still combine within the active tab; strip scrolls horizontally on mobile. |
| 2026-07-24 | Section 05 "AI notes" retired — it was a subset of 07. 07 becomes the single **learning-tracks** archive: each domain tab carries a track intro (headline + one line; AI = the rescued "Theory by hand, tools by habit."), and the grid uses **Show more** (Medium-style load-more, 24 at a time) instead of a wall. Sections renumber 06→05 (How I build), 07→06 (Write-ups); "AI notes" nav tab removed. Mastery signal deliberately NOT shown (data too sparse — 68/90 unset). Medium studied for the patterns (topic pills, load-more), adapted to the cream/serif contract — no sans/thumbnails/infinite-scroll. |
| 2026-07-24 | Bugfix: the "How I build" section had been silently dropping since `fe1e2c0` moved `ai-dev-workflow.svg` into `knowledge/claude/imgs/` but left `build.py`'s `WORKFLOW_SVG` on the old path → `build_html()` hit its `return ""` guard. Repointed the path; section is back. |
| 2026-07-24 | Reader (article view) typography, Medium-informed: body had no `.rbody` text rule → fell back to Inter sans 16px. Now **serif body in Medium’s reading serif** — new `--read` token `Charter,"Bitstream Charter",Georgia,serif` (Charter ships on macOS/iOS, so it matches Medium exactly there; Georgia fallback), ~18px / 1.72, real paragraph rhythm; **sans headings** — article title + `.rbody` h2/h3/h4 → `--sans` (the sans-headline / serif-reading combo she pointed to; a deliberate, reading-mode-scoped divergence from the site’s serif-everywhere headings); **wide margins** — panel 780→760px, responsive side padding `clamp(20px,5vw,52px)` so text does not hug the edge (~64-char measure). Title 1.35rem → clamp(1.6–1.95rem). Code blocks stay mono (her call). |
