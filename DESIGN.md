# DESIGN.md — Site Design Guideline（網站設計準則）

> **Single source of truth for how the site looks, reads, and behaves.**
> The CSS itself lives in `site/build.py` (HEAD template) — this file is the *contract* behind it.
> Rule of the house: **Decided once. Committed.** 每個視覺決策在這裡定案一次，之後不再每次重想。
>
> Reference / inspiration: [contentarchitecture.dev](https://www.contentarchitecture.dev/) —
> we already share its ground palette (`#f1eee7 / #232323 / #5b5a56`); what we borrow from it
> going forward is the **typographic system and the copy discipline**, not just colors.

---

## 0. Change process（改版流程）

1. Propose the change **in this file first** (edit the token / rule, note it in §9 Decision log).
2. Get Yuan's OK on anything visual (colors, layout, fonts) — never silently restyle the live site.
3. Then implement in `site/build.py`, run `python3 site/build.py`, eyeball `index.html`, commit.

---

## 1. Purpose & audience（這個網站是給誰看的）

The page has **one job**: let a recruiter or engineer decide in **60 seconds** that
Yuan is (a) actually coding, (b) able to explain reasoning clearly, (c) still improving.

Two readers, two speeds:

| Reader | Time | What they must get |
|---|---|---|
| Recruiter / HR | ~60 s | Hero thesis + numbers + proof it's current ("updated 2026-07") |
| Engineer / interviewer | ~10 min | 2–3 curated write-ups showing real reasoning + the build system itself |

Everything on the page must serve one of these two. If a section serves neither, cut it.

## 2. Positioning & voice（定位與文案原則）

- **One committed thesis, not a rotating slideshow.** The hero states a single line the
  reader cannot miss. Current thesis: **"The reasoning, not just the code."**
  (Rotating/typewriter showcases hide 2/3 of the message from a 10-second visitor.)
- **Evidence over claims.** Never "passionate about algorithms" — always the number and
  the artifact: "466 solved, 31 written up in full."
- **Numbers must agree everywhere.** One constant in `build.py` feeds hero, coverage,
  and cards. (Bug class we already hit: hero said 27, write-ups lede said 26.)
- **Show recency.** Learning-in-public credibility = the log is *alive*. The page carries
  a "last updated" stamp and surfaces the most recent write-ups.
- **Honesty is the brand.** Mastery self-ratings, mistakes, and "what I got wrong first"
  stay visible. That is the differentiator, not a weakness.
- Copy style: short plain sentences, everyday words, specific beats clever.
  (Same rule as the résumé/BQ material.)

## 3. Color tokens（顏色）

Warm paper ground + near-black ink; the **knowledge-graph panel is the one dark, bold
element** on the page. Everything else stays quiet.

| Token | Value | Role |
|---|---|---|
| `--bg` | `#f1eee7` | page ground (warm off-white) |
| `--surface` | `#ffffff` | cards |
| `--surface2` | `#f5f1e8` | insets, code blocks |
| `--border` | `#e3ddd0` | hairlines (warm, never pure grey) |
| `--fg` | `#232323` | ink |
| `--muted` | `#5b5a56` | secondary text (warm grey) |
| `--accent` | `#40392e` | links, dark accents |
| `--gold` | `#d6a878` | highlight (typed word, bars, kicker dot) |
| panel | `#232323` | knowledge-graph canvas ground |
| difficulty | `#8a8a8a → #5b5a56 → #232323` | Easy → Medium → Hard, one greyscale ramp (never green/orange/red) |

**Decided 2026-07-07 (Yuan):** keep `#d6a878` gold. No hot-orange accent.

**Decided 2026-07-07 (Yuan):** the site is **single-theme: clean warm off-white `#f1eee7`,
always**. No dark mode (`meta color-scheme: light`); the only dark surfaces are the graph
panel and the code window, by design.

**GitHub contribution ramp** (gold sequential, on `--surface`):
`#e7e0d1 → #eeddc2 → #dfb98a → #c08a4d → #8f6132` (empty → most active).

Rules:
- **One accent moment per viewport.** If two things compete for attention, demote one.
- Difficulty is an *ordinal* scale → one ramp, light→dark. Never traffic-light colors.
- Semantic/status colors (if ever needed) are separate from the accent and never decorative.

## 4. Typography（字體系統）

| Role | Face | Usage |
|---|---|---|
| Display / headings | `Fraunces` (serif) | h1–h3, card titles, brand |
| Body | `Inter` + `"PingFang TC","Noto Sans TC"` | paragraphs, UI |
| Utility / data | `JetBrains Mono` | kickers, tags, numbers, code |

Rules (the part we adopt from contentarchitecture.dev):
- **Mono is the voice of metadata.** Every kicker/eyebrow/label/stat is mono,
  UPPERCASE, `letter-spacing: .06–.08em`, muted color. Body text never is.
- **Numbers are always mono + `font-variant-numeric: tabular-nums`** so stats align.
- Headline scale via `clamp()`; h1 tracking tight (`-0.02` to `-0.03em`); body `line-height ≥ 1.6`.
- Running text measure ≤ ~70ch (`--wrap: 880px` handles this).
- Headings get `text-wrap: balance`.
- CJK fallbacks stay in every stack (content is bilingual EN/中文).

**Decided 2026-07-07 (Yuan):** keep Fraunces/Inter/JetBrains Mono. The warmth *is* the
brand; what we adopt from contentarchitecture.dev is the mono-metadata discipline and the
motion system (§7), not its typefaces. This decision is closed — stop re-choosing fonts.

## 5. Layout & spacing（版面）

- **The page is a rhythm of full-bleed color bands** (the contentarchitecture.dev
  structure — decided 2026-07-07 after Yuan flagged "只有封面滿版很奇怪"):
  every section is a full-width band, cream `#f1eee7` or black `#232323`, alternating;
  content inside is a centered `max-width: 1200px` wrap. Band order:

  | Band | Ground |
  |---|---|
  | Hero (split: text + graph canvas) | cream / black |
  | 01 Start here | cream |
  | 02 Experience (pinned scrollytelling) | **black** |
  | 03 Activity (GitHub calendar) | cream |
  | 04 The system (code window) | **black** |
  | 05 AI notes · 06 Practice log | cream |
  | Footer | **black** (bookend) |

- **Dark-band token re-scope**: `.band.dark` redefines the tokens
  (`--ink:#f1eee7; --muted:#a8a49c; --border:#413e37; --surface:#2a2823`), so all
  components restyle themselves — never hand-color inside a dark band. Primary buttons
  invert (cream bg, ink text, gold hover). Gold reads brighter on black — use it for
  dates/hooks/rail there.
- **Deep device frame** (inside black bands, the CA nested-frame move): outer frame
  `#141311`, `radius 18px`, `1px ring rgba(255,255,255,.09)`, large soft shadow; inner
  window `#232323` with `ring white/8`. Black-on-black layering via rings, not borders.
- Band padding-block `clamp(4rem, 9vw, 8.5rem)` — generous, CA-scale. Adjacent same-color
  bands get a hairline separator; color changes need none.
- **Hero = 100svh split**: left text column (~47%), right black graph canvas.
  Stacks at `≤900px`; small-phone adjustments at `≤560px`.
- Sections carry **mono eyebrows with gold index numbers** (`01 — START HERE`: the
  numbers encode scroll order, which is real information on a single-page site).
- Spacing: use flex/grid `gap`, not stacked margins. Section padding-block ≥ `5rem` desktop.
- Cards: white, `border-radius 12–14px`, 1px warm border, hover = border-color shift only
  (no shadows, no lift — the page stays flat and paper-like).
- Page must never scroll horizontally; wide tables/code get their own `overflow-x:auto`.

## 6. Components（元件規格）

- **Kicker / eyebrow**: mono, uppercase, muted, with gold dot or index number.
- **Hero thesis**: one h1 + one supporting paragraph + stat strip + ≤3 actions
  (primary = internal "Start here", secondary = GitHub / LeetCode, ghost style).
- **Hero stat strip — AI and LeetCode are separate groups**, divided by a vertical
  hairline, each with its own mono uppercase group label (`AI / CS224N` first, then
  `LEETCODE`). Never mix the two domains' numbers in one flat row.
- **Stat tiles**: big mono number (tabular-nums) + small mono label. No borders heavier
  than cards. A tile is *not* a chart — no decoration.
- **GitHub contribution calendar**: 20-week window (not 52 — the public streak is young;
  widen the window as history accumulates), 13px cells, 3px gap, gold sequential ramp
  (§3), month labels on top, `Less→More` legend, honest caption ("started logging
  publicly in spring 2026"). Production data: GitHub GraphQL contributions API at build
  time, cached into `site/`. Cells reveal in a left-to-right wave on scroll into view.
- **Code window ("The system")**: the CA "this is the actual repo" move, upgraded — a
  mac-style editor frame on `--panel` dark: title bar (3 muted dots + mono filename),
  left pane = file tree of the two-repo system (`mind/ 🔒 private` visible), right pane =
  the *real* `collect()` visibility-gate snippet from `build.py`, line numbers, syntax
  colors from the palette family only (gold keywords, warm-green strings, warm-grey
  comments), the two gate lines highlighted, blinking cursor on the last line. Lines fade
  in one-by-one on first reveal.
- **LeetCode is presented modestly.** Coverage numbers + difficulty bar + write-up list
  live together in ONE compact "Practice log" section near the bottom; copy frames volume
  as reps ("466 solved is just volume — the write-ups are the point"). LeetCode never
  gets more visual weight than the AI notes or Experience. AI notes get their own
  separate section listing all 5.
- **Difficulty bar** (coverage): single stacked proportion bar, greyscale ramp,
  2px gaps between segments, direct labels with dot markers (`Easy 113 · Medium 285 · Hard 68`).
  Never a pie chart.
- **Write-up cards**: serif title, domain pill (LeetCode olive / AI tan), difficulty pill,
  mastery `N/5`, tags, "Reveal write-up" (recall-then-reveal stays — it's pedagogically
  on-brand). Deep-linkable via `#card-<id>`.
- **Curated "Start here" row**: exactly **3** hand-picked write-ups with one line each on
  *why this one* ("read this to see how I reason about invariants"). Curation = judgment signal.
- **Knowledge graph**: monochrome dots on `#232323`; notes = hollow rings, topics = solid
  discs; click fans out + opens side panel. This is the site's signature — protect it,
  don't add colors to it.
- **The System section**: one section that treats the site itself as an engineering
  project — two-repo diagram (`mind/` private → `visibility:public` gate → `build.py` →
  static `index.html`; Notion → Coding Report → `leetcode/`), in a mono code-style panel.
  This is the "This is the actual repo" move.
- **Résumé / Experience section** (web-native, **no PDF by design**):
  - Placement: section `02`, right after "Start here" — recruiters reach it in one scroll.
  - Opens with the positioning line as a serif italic pull-quote with gold left border:
    *"I don't want to train the models — I want to build the engine that makes them fast
    and reliable."*
  - Body: **timeline rows** (`grid: 170px 1fr`, hairline-separated) — mono date column left;
    right column = serif company name, mono uppercase role line, 2–3 bullets max.
  - Bullet grammar: action + constraint + **quantified result in bold ink**; muted body text.
    One serif-italic "hook" sentence allowed per entry (personality, per BQ-hook rule),
    e.g. *"I couldn't scale the hardware, so I shrank the problem."*
  - Content source: `mind/resume/resume.md` → future `visibility: public` extract; until the
    pipeline exists, hand-maintain the section in `build.py`. Public version carries **no
    email/phone/address**; exact dates can stay coarse (years + duration).
  - CTA row: `Full history on LinkedIn ↗` (primary) + the mono note
    *"No PDF here on purpose — this page is the résumé, and it's always current."*
  - ⚠️ Employer content check: keep NVIDIA/Broadcom bullets at the same altitude as the
    public LinkedIn profile — no internal tool names or unreleased product details.
- **Floating nav**: pill bar, IntersectionObserver highlights active section.
- **Footer**: the honesty line (static, no backend, GoatCounter cookieless,
  only `visibility:public` renders) + last-build timestamp.

## 7. Motion（動態系統）— v1, adopted from contentarchitecture.dev's grammar

Philosophy: motion exists to say **"this log is alive"** and to sequence attention —
never to decorate. One orchestrated hero moment; everything after is quiet.

### 7.1 Timing tokens

| Token | Value | Used for |
|---|---|---|
| `--ease` | `cubic-bezier(.4,0,.2,1)` | every transition/reveal |
| micro | `.15s` | hover states (border, background, arrow nudge) |
| reveal | `.6s` | scroll/load fade-and-rise |
| grow | `.8s` | difficulty-bar scaleX |
| count | `900ms`, ease-out cubic | odometer number count-up |
| stagger | `60–150ms` between siblings | cards, tiles, rows, hero blocks |

### 7.2 The inventory（全部動態，僅此清單）

1. **Hero load sequence** (the one orchestrated moment, total < 1.5s):
   kicker (0s) → h1 (.15s) → sub (.3s) → stat strip (.45s, numbers **odometer count up**)
   → action buttons (.6s). Each = fade + `translateY(14px→0)`.
2. **Typewriter kicker**: "LEARNING IN PUBLIC" types at ~55ms/char, then the gold block
   cursor keeps blinking (`steps(1,end)`, .9s). This replaces the old rotating 3-scene
   showcase — the typewriter survives, the carousel does not.
3. **Status ping**: gold dot next to "Updated YYYY-MM" pulses outward
   (`ping 1.8s cubic-bezier(0,0,.2,1) infinite`, scale 2.4 → fade). The recency signal.
4. **Scroll cue**: `↓` at hero bottom, `steps(7)` drift-down loop (CA's heroScrollCue).
   Hidden on mobile; optionally hidden after first scroll.
5. **Graph pop-in**: nodes appear staggered (~60ms apart, radius grows 350ms), links fade
   in after both endpoints exist; then permanent gentle idle drift (sin/cos, ±2px).
   Pause rAF when tab hidden. Click/drag physics unchanged.
6. **Scroll reveals**: every section header, card, tile, timeline row and list row gets
   fade + rise via one `IntersectionObserver` (`threshold: .2`), fire **once**, staggered
   via `--d` custom property. No re-animation on scroll-up.
7. **Odometer on scroll**: coverage tiles count up when the tile scrolls into view.
8. **Difficulty bar grow**: segments `scaleX(0→1)`, origin left, staggered E→M→H.
9. **Hover micro-interactions**: card border → gold + "Read →" arrow nudges 4px;
   list rows get surface background; buttons shift border/background. `.15s` each.
10. **Résumé pinned scrollytelling** (the Experience section): the section is a tall
    scroll track (~320vh) with a `position: sticky; top: 0` full-viewport stage. Left
    column (headline + pitch quote + CTA) stays fixed; right column's timeline entries
    start at `opacity .13 / translateY(26px)` and switch on cumulatively as scroll
    progress crosses thresholds (≈ .04 / .42 / .74); a 2px gold progress rail fills
    alongside. Implementation: `sticky` + one passive scroll listener computing
    `p = -rect.top / (rect.height - viewportH)` — no scroll-jacking, native wheel.
    **Fallbacks:** `≤900px` and `prefers-reduced-motion` → normal flow, all entries
    visible, no pin.
11. **Code window line reveal**: on first intersection, lines fade/slide in at 100ms
    intervals; block cursor keeps blinking on the last line.
12. **GitHub grid wave**: cells scale/fade in left-to-right (`w*30ms + d*8ms` delays)
    on first intersection.

### 7.3 Rules

- Anything not in §7.2 doesn't animate. Adding a new animation = new decision in §9.
- All reveals are **once-only** and ≤ .8s; nothing loops except cursor, ping, cue, drift.
- Implementation: vanilla JS + one IntersectionObserver + CSS custom-prop stagger
  (`--d`), no libraries — consistent with the zero-dependency posture.
- **`prefers-reduced-motion: reduce`** turns off *everything*: content renders fully
  visible (`.rv{opacity:1;transform:none}`), numbers render final values, typewriter
  prints instantly, cursor/ping/cue static, graph laid out statically. Test both modes.

## 8. Accessibility & performance（可及性與效能）

- Contrast: body ink on ground ≥ 7:1 (`#232323` on `#f1eee7` passes); muted text ≥ 4.5:1.
- Keyboard: visible `:focus-visible` on all interactive elements incl. cards' reveal buttons.
- Graph canvas gets an offscreen text alternative (the write-up list *is* the fallback).
- Keep the dependency posture: **no JS frameworks, no build deps** — Google Fonts, KaTeX,
  GoatCounter are the only external requests. Every added asset must justify itself.
- Ship `og-image.png` in the same palette; keep JSON-LD Person, sitemap, robots current.

## 9. Decision log（決策紀錄）

| Date | Decision | Status |
|---|---|---|
| 2025 | Palette: warm paper `#f1eee7` + ink `#232323` + gold `#d6a878`, black graph panel | ✅ decided |
| 2025 | Recall-then-reveal cards; monochrome knowledge graph | ✅ decided |
| 2026-07 | This file becomes the design contract; changes go through §0 process | ✅ decided |
| 2026-07 | Hero: replace rotating 3-scene showcase with one committed thesis + stat strip | 🟡 proposed (v3 mockup) |
| 2026-07 | Add "Start here" curated row + "The System" section + recency stamp | 🟡 proposed (v3 mockup) |
| 2026-07-07 | Typography: **keep Fraunces/Inter/JetBrains Mono** (Yuan) | ✅ decided |
| 2026-07-07 | Accent: **keep gold `#d6a878`**, no hot orange (Yuan) | ✅ decided |
| 2026-07-07 | Résumé: **web-native section, no PDF**; timeline layout per §6; LinkedIn = full history | ✅ decided (content pending Yuan's review) |
| 2026-07-07 | Motion system v1 (§7): hero sequence, typewriter, ping, odometer, scroll reveals, reduced-motion | 🟡 proposed (v3 mockup) |
| 2026-07-07 | "Start here" picks: AI note 05 Backprop (first) · LC 84 · LC 4 | 🟡 proposed — Yuan may swap |
| 2026-07-07 | Single theme: warm off-white always, no dark mode (Yuan) | ✅ decided |
| 2026-07-07 | Hero stats: AI group and LeetCode group split by hairline, AI first (Yuan) | ✅ decided |
| 2026-07-07 | LeetCode = one modest combined "Practice log" section; AI notes get their own section (Yuan) | ✅ decided |
| 2026-07-07 | Résumé = pinned scrollytelling (sticky stage, entries reveal on scroll progress) (Yuan) | ✅ decided |
| 2026-07-07 | "The system" = editor-style code window showing the real visibility gate (Yuan: "學參考網站的內嵌程式碼，設計更漂亮") | ✅ decided |
| 2026-07-07 | GitHub contribution calendar added, 20-week window, gold ramp (Yuan asked; window short因為公開更新是最近開始) | ✅ decided |
| 2026-07-07 | Page = full-bleed cream/black band rhythm (CA structure); Experience + The system + footer on black; deep device frames inside black bands (Yuan) | ✅ decided |
