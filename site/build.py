#!/usr/bin/env python3
"""
build.py — static site generator for the "Learning in Public" portfolio.

Walks the public content folders, reads each file's YAML frontmatter (per ../SCHEMA.md),
and writes a single self-contained ../index.html laid out as full-bleed cream/black
bands (design contract: ../DESIGN.md):

  hero (thesis + knowledge graph) → 01 start here → 02 experience (pinned scrolly,
  black) → 03 activity (GitHub calendar) → 04 the system (code window, black) →
  05 AI notes → 06 practice log (write-up archive) → footer (black)

No dependencies (stdlib only). No backend. GitHub Pages serves the output.
The page is assembled by plain string concatenation (not str.format) so the
inline CSS/JS can use normal braces without escaping.

Usage:
    python site/build.py
"""
from __future__ import annotations
import html
import json
import re
import shutil
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# ---- config -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent          # repo root
CONTENT_DIRS = ["leetcode", "ai-knowledge"]            # public domains shown on the site
GITHUB_USER = "Yuan-Hsuan"
LINKEDIN_URL = "https://www.linkedin.com/in/yuan-hsuan-wen/"
OUT = ROOT / "index.html"

WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")             # [[note]] links, Obsidian-style

# ---- curated picks (section 01 — DESIGN.md §6) --------------------------------
# id must exist in the collected cards; missing ids are skipped gracefully.
CURATED = [
    dict(id="ai-backprop", meta="AI / CS224n · Note 05",
         why="Deriving the gradients on paper before letting PyTorch do it — with the "
             "shape-checking habit that catches most of my bugs."),
    dict(id="lc-largest-rectangle-in-histogram", meta="LeetCode 84 · Hard · Mastery 5/5",
         why="The monotonic-stack invariant, built up from the O(n²) version — how a "
             "trick becomes a reusable pattern."),
    dict(id="lc-median-of-two-sorted-arrays", meta="LeetCode 4 · Hard · Mastery 5/5",
         why="Binary search on the partition, not the value — including the off-by-one "
             "traps I fell into first."),
]

# ---- experience (section 02 — web-native résumé, DESIGN.md §6) ----------------
EXPERIENCE = [
    dict(when="2025 — 2026 · 7 mo", org="NVIDIA",
         role="Software Intern — AI debugging engine",
         bullets=[
            'Built an AI layer for Android <b>CTS failure triage</b>: a coarse-to-fine '
            'pipeline that routes each failure to the owning module and points at the '
            'suspect code block.',
            '<b>No training cluster, one consumer GPU</b> — an AST engine pre-filters the '
            'LLM’s context to a fraction of the tokens. <span class="xp-hook">'
            '“I couldn’t scale the hardware, so I shrank the problem.”</span>',
            '<b>~80% of routine triage automated</b>; adopted as a permanent asset.']),
    dict(when="2020 — 2023 · 3 yrs", org="Broadcom",
         role="System Software Engineer",
         bullets=[
            'Turned highly manual <b>network/hardware validation</b> into end-to-end '
            '<b>automated pipelines</b> — the systems habits the NVIDIA work was built on.']),
    dict(when="2024 — 2026", org="University of Southern California",
         role="M.S. Computer Science",
         bullets=[
            'Alongside coursework: <b>Stanford CS224n self-study</b> (this site’s AI '
            'notes) and a steady algorithms practice log.']),
]

# ---- external AI notes (single source of truth: the CS224n study repo) -------
# The notes live in the sibling repo; we read them at build time so the site is
# never a stale copy — edit the note there, re-run build.py, done. (Images are
# copied into ROOT/imgs so GitHub Pages can serve them.)
CS224N_NOTES = ROOT.parent / "Standford-cs224n-nlp" / "notes" / "concepts"
CS224N_SOURCE = "https://web.stanford.edu/class/cs224n/"
CS224N_META = {
    "01-word-embeddings.md":        dict(id="ai-word-embeddings", title="Word Embeddings (one-hot → dense)",
        tags=["nlp", "embeddings", "word-vectors"], difficulty="easy", mastery=3),
    "02-count-based-svd.md":        dict(id="ai-count-svd", title="Count-Based Word Vectors (SVD)",
        tags=["nlp", "svd", "co-occurrence", "embeddings", "linear-algebra"], difficulty="medium", mastery=3),
    "03-word2vec-and-glove.md":     dict(id="ai-word2vec-glove", title="word2vec & GloVe",
        tags=["nlp", "word2vec", "glove", "embeddings", "negative-sampling"], difficulty="medium", mastery=3),
    "04-neural-nets-ner.md":        dict(id="ai-neural-nets-ner", title="Neural Nets: NER & Non-linearities",
        tags=["nlp", "neural-networks", "ner", "non-linearities"], difficulty="medium", mastery=2),
    "05-backprop-matrix-calculus.md": dict(id="ai-backprop", title="Backprop & Matrix Calculus",
        tags=["neural-networks", "backpropagation", "gradients", "matrix-calculus", "deep-learning"],
        difficulty="medium", mastery=2),
}


# ---- frontmatter parsing ----------------------------------------------------
def parse_frontmatter(text: str):
    """Return (meta: dict, body: str). meta is {} if no frontmatter block."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    raw, body = parts[1], parts[2]
    meta = {}
    for line in raw.strip().splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):          # tags: [a, b]
            val = [t.strip() for t in val[1:-1].split(",") if t.strip()]
        meta[key] = val
    return meta, body.strip()


# ---- minimal markdown -> HTML (only what the cards use) ----------------------
def _inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)                    # `code`
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)          # **bold**
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",                            # ![alt](img)
               r'<img src="\2" alt="\1" style="max-width:100%;border-radius:8px;margin:10px 0">', s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)  # [t](url)
    return s


def render_body(md: str) -> str:
    """Markdown → HTML, protecting LaTeX math ($…$ / $$…$$) from the markdown pass so KaTeX
    (auto-render, loaded in <head>) can typeset it in the browser."""
    math = []
    def stash(m):
        math.append(m.group(0)); return f"@@MATH{len(math)-1}@@"
    md = re.sub(r"\$\$.*?\$\$", stash, md, flags=re.S)                 # display math
    md = re.sub(r"\$[^$\n]+?\$", stash, md)                            # inline math
    out = md_to_html(md)
    for i, m in enumerate(math):
        out = out.replace(f"@@MATH{i}@@", m)
    return out


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if line.lstrip().startswith("```"):                          # fenced code
            lang = line.lstrip()[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(html.escape(lines[i], quote=False)); i += 1
            i += 1
            cls = f' class="lang-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>" + "\n".join(buf) + "</code></pre>")
            continue
        if line.startswith("|") and i + 1 < n and set(lines[i + 1].replace("|", "").strip()) <= {"-", ":", " "}:
            header = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")]); i += 1
            th = "".join(f"<th>{_inline(c)}</th>" for c in header)
            trs = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>")
            continue
        if line.startswith(">"):                                     # blockquote
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip()); i += 1
            out.append("<blockquote>" + _inline(" ".join(buf)) + "</blockquote>")
            continue
        m = re.match(r"(#{1,6})\s+(.*)", line)                       # heading
        if m:
            lvl = min(len(m.group(1)) + 1, 6)
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if re.match(r"\s*[-*]\s+", line):                            # ul
            buf = []
            while i < n and re.match(r"\s*[-*]\s+", lines[i]):
                buf.append(re.sub(r"\s*[-*]\s+", "", lines[i], count=1)); i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ul>")
            continue
        if re.match(r"\s*\d+\.\s+", line):                           # ol
            buf = []
            while i < n and re.match(r"\s*\d+\.\s+", lines[i]):
                buf.append(re.sub(r"\s*\d+\.\s+", "", lines[i], count=1)); i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ol>")
            continue
        if not line.strip():
            i += 1
            continue
        buf = []                                                     # paragraph
        while i < n and lines[i].strip() and not re.match(r"(#{1,6}\s|\s*[-*]\s|\s*\d+\.\s|>|\||```)", lines[i]):
            buf.append(lines[i]); i += 1
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


# ---- collect content --------------------------------------------------------
def short_label(domain: str, title: str) -> str:
    if domain == "leetcode":
        m = re.match(r"^\s*(\d+)\.", title)
        if m:
            return m.group(1)
    return title if len(title) <= 16 else title[:15] + "…"


def collect():
    cards = []
    for d in CONTENT_DIRS:
        for path in sorted((ROOT / d).rglob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            if meta.get("visibility") != "public":                  # SAFETY BELT
                continue
            domain = meta.get("domain", "leetcode" if d == "leetcode" else "ai")
            tags = meta.get("tags", []) if isinstance(meta.get("tags"), list) else []
            related = meta.get("related", []) if isinstance(meta.get("related"), list) else []
            related += [w.strip() for w in WIKILINK.findall(body)]   # [[wikilinks]] in body
            cards.append({
                "id": meta.get("id", path.stem),
                "domain": domain,
                "title": meta.get("title", path.stem),
                "label": short_label(domain, meta.get("title", path.stem)),
                "tags": tags,
                "difficulty": meta.get("difficulty", ""),
                "mastery": int(meta.get("mastery", 0) or 0),
                "words": len(re.sub(r"```.*?```", " ", body, flags=re.S).split()),
                "related": related,
                "body_html": render_body(body),
            })
    cards.extend(external_ai_cards())
    return cards


def external_ai_cards():
    """Read the CS224n notes from the sibling repo at build time (single source of
    truth) and turn each into an AI card. Returns [] if the repo isn't next door."""
    if not CS224N_NOTES.exists():
        return []
    (ROOT / "imgs").mkdir(exist_ok=True)                          # copy note images for Pages
    for img in (CS224N_NOTES / "imgs").glob("*.png"):
        shutil.copy(img, ROOT / "imgs" / img.name)
    cards = []
    for fname, m in CS224N_META.items():
        path = CS224N_NOTES / fname
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        parts = text.split("\n---\n", 2)                         # drop title + header + Contents
        body = parts[2].strip() if len(parts) >= 3 else re.sub(r"^#.*\n", "", text, count=1).strip()
        body = WIKILINK.sub(r"\1", body)                          # strip [[ ]] the site can't resolve
        cards.append({
            "id": m["id"], "domain": "ai", "title": m["title"],
            "label": short_label("ai", m["title"]), "tags": m["tags"],
            "difficulty": m["difficulty"], "mastery": m["mastery"],
            "words": len(re.sub(r"```.*?```", " ", body, flags=re.S).split()),
            "related": [], "source": CS224N_SOURCE, "body_html": render_body(body),
        })
    return cards


# ---- knowledge graph (hierarchical: cluster -> topic -> note) ---------------
# Top-level clusters. A tag not listed here falls into "Other".
GROUPS = [
    ("Arrays & Strings", ["array", "string", "two-pointers", "sliding-window", "sorting",
                          "prefix-sum", "matrix", "simulation", "merge-sort", "counting-sort",
                          "bucket-sort", "quickselect", "string-matching", "line-sweep", "ordered-set"]),
    ("Search & DP", ["binary-search", "dynamic-programming", "greedy", "backtracking", "recursion",
                     "divide-and-conquer", "memoization", "enumeration", "combinatorics", "bitmask"]),
    ("Data Structures", ["hash-table", "stack", "monotonic-stack", "linked-list", "queue",
                         "heap-priority-queue", "design", "bit-manipulation", "doubly-linked-list",
                         "trie", "segment-tree", "binary-indexed-tree", "monotonic-queue",
                         "data-stream", "hash-function", "randomized"]),
    ("Graphs & Trees", ["depth-first-search", "breadth-first-search", "tree", "binary-tree",
                        "binary-search-tree", "graph", "union-find", "topological-sort",
                        "shortest-path", "minimum-spanning-tree", "eulerian-circuit", "graph-theory"]),
    ("Math", ["math", "counting", "number-theory", "geometry", "interactive", "probability"]),
    ("AI / NLP", ["nlp", "embeddings", "word2vec", "glove", "deep-learning", "classification",
                  "loss", "transformers", "attention"]),
]
OTHER_LABEL = "Other"


def build_graph(cards):
    """All-visible bipartite graph: every note and every topic is a node, notes link to
    their topics (+ any [[wikilinks]]). Coloured by domain only (2 colours)."""
    DOM_CI = {"leetcode": 0, "ai": 1}
    ids = {c["id"] for c in cards}
    tag_dom = defaultdict(Counter)
    tag_notes = defaultdict(list)
    for c in cards:
        for t in c["tags"]:
            tag_dom[t][c["domain"]] += 1
            tag_notes[t].append({"id": c["id"], "title": c["title"],
                                 "domain": c["domain"], "difficulty": c["difficulty"]})

    nodes, index = [], {}
    maxw = max((c["words"] for c in cards), default=1) or 1
    for c in cards:
        index["note:" + c["id"]] = len(nodes)
        nodes.append({"id": "note:" + c["id"], "type": "note", "label": c["label"],
                      "full": c["title"], "ci": DOM_CI.get(c["domain"], 0), "cardId": c["id"],
                      "difficulty": c["difficulty"],
                      "r": round(5 + 5 * (c["words"] / maxw) ** 0.5, 1)})
    maxd = max((len(v) for v in tag_notes.values()), default=1) or 1
    for t in sorted(tag_notes):
        dom = tag_dom[t].most_common(1)[0][0]
        index["tag:" + t] = len(nodes)
        nodes.append({"id": "tag:" + t, "type": "tag", "label": t, "full": t,
                      "ci": DOM_CI.get(dom, 0), "count": len(tag_notes[t]), "items": tag_notes[t],
                      "r": round(8 + 11 * (len(tag_notes[t]) / maxd) ** 0.7, 1)})

    edges = []
    for c in cards:
        a = index["note:" + c["id"]]
        for t in c["tags"]:
            edges.append([a, index["tag:" + t]])
    seen = set()
    for c in cards:
        for r in c["related"]:
            key = r.replace("lc-", "").replace("ai-", "")
            tgt = next((x for x in ids if x == r or x.endswith(key)), None)
            if tgt and tgt != c["id"]:
                e = tuple(sorted((index["note:" + c["id"]], index["note:" + tgt])))
                if e not in seen:
                    seen.add(e)
                    edges.append([e[0], e[1]])

    groups = [{"ci": 0, "label": "LeetCode"}, {"ci": 1, "label": "AI / NLP"}]
    return {"nodes": nodes, "edges": edges, "groups": groups}


def load_solved():
    p = ROOT / "site" / "solved.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ---- GitHub contribution calendar (section 03) --------------------------------
# Fetched at build time from GitHub's public contributions endpoint (no token),
# cached in site/contrib.json so offline builds still work. Section is omitted
# entirely if neither the network nor the cache yields data.
CONTRIB_WEEKS = 20

def load_contrib():
    cache = ROOT / "site" / "contrib.json"
    days = None
    try:
        req = urllib.request.Request(
            f"https://github.com/users/{GITHUB_USER}/contributions",
            headers={"User-Agent": "Mozilla/5.0 (build.py)"})
        page_html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
        found = {}
        for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", page_html):
            d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', td)
            l = re.search(r'data-level="(\d)"', td)
            if d and l:
                found[d.group(1)] = int(l.group(1))
        if found:
            days = [{"date": k, "level": v} for k, v in sorted(found.items())]
            cache.write_text(json.dumps({"days": days}), encoding="utf-8")
    except Exception as exc:                                     # offline → cache
        print(f"  (contributions fetch failed: {exc}; trying cache)")
    if days is None and cache.exists():
        days = json.loads(cache.read_text(encoding="utf-8")).get("days")
    if not days:
        return None
    days = days[-(CONTRIB_WEEKS * 7 + 6):]
    off = (date.fromisoformat(days[0]["date"]).weekday() + 1) % 7   # align col 1 to Sunday
    days = days[(7 - off) % 7:][:CONTRIB_WEEKS * 7]
    months, seen = [], None
    for i in range(0, len(days), 7):
        m = date.fromisoformat(days[i]["date"]).strftime("%b")
        months.append(m if m != seen else "")
        seen = m
    return {"levels": [d["level"] for d in days], "months": months}


# ---- HTML section builders ----------------------------------------------------
def esc(s):
    return html.escape(str(s), quote=True)


def hero_html(cards, solved):
    n_ai = sum(1 for c in cards if c["domain"] == "ai")
    n_lc = sum(1 for c in cards if c["domain"] == "leetcode")
    total = (solved or {}).get("counts", {}).get("total", 0)
    return f"""
  <header class="hero2" id="top">
    <div class="hero2-left">
      <p class="kicker rv" style="--d:0s"><span>Yuan-Hsuan Wen</span><span aria-hidden="true">·</span><span id="typed"></span><span class="cursor" aria-hidden="true"></span><span aria-hidden="true">·</span><span>Updated __BUILD_MONTH__<span class="ping" aria-hidden="true"></span></span></p>
      <h1 class="rv" style="--d:.15s">The <em>reasoning</em>, not just the code.</h1>
      <p class="hero-sub rv" style="--d:.3s">A systems engineer moving into AI infrastructure —
      logging the practice honestly: the trade-offs and the mistakes, not just accepted submissions.</p>
      <div class="stats rv" style="--d:.45s">
        <div class="sgroup">
          <div class="sl">AI / CS224n</div>
          <div class="srow">
            <div class="stat"><div class="n odo" data-n="{n_ai}">0</div><div class="l">deep notes</div></div>
            <div class="stat"><div class="n">minBERT</div><div class="l">in progress</div></div>
          </div>
        </div>
        <div class="vdiv" aria-hidden="true"></div>
        <div class="sgroup">
          <div class="sl">LeetCode</div>
          <div class="srow">
            <div class="stat"><div class="n odo" data-n="{total}">0</div><div class="l">solved</div></div>
            <div class="stat"><div class="n odo" data-n="{n_lc}">0</div><div class="l">write-ups</div></div>
          </div>
        </div>
      </div>
      <div class="actions rv" style="--d:.6s">
        <a class="btn primary" href="#start">Start here ↓</a>
        <a class="btn" href="#xp">Résumé ↓</a>
        <a class="btn" href="https://github.com/{GITHUB_USER}" target="_blank" rel="noopener">GitHub ↗</a>
      </div>
    </div>
    <div class="hero2-right">
      <canvas id="kg" aria-label="Knowledge graph of write-ups and topics"></canvas>
      <div class="kg-hint">click to fan out · drag</div>
      <aside class="kg-panel" id="kg-panel"></aside>
    </div>
    <div class="cue" aria-hidden="true">↓</div>
  </header>"""


def start_here_html(cards):
    by_id = {c["id"]: c for c in cards}
    items = []
    for i, pick in enumerate(CURATED):
        c = by_id.get(pick["id"])
        if not c:
            continue
        tags = " · ".join(c["tags"][:2])
        items.append(
            f'<a class="card2 rv" style="--d:{i*0.1:.1f}s" href="#card-{esc(c["id"])}" '
            f'onclick="expandCard(\'{esc(c["id"])}\');return false;">'
            f'<div class="meta">{esc(pick["meta"])}</div>'
            f'<h3>{esc(c["title"])}</h3>'
            f'<p class="why">{esc(pick["why"])}</p>'
            f'<div class="foot"><span>{esc(tags)}</span><span class="go">Read</span></div></a>')
    if not items:
        return ""
    return ('\n  <section class="band" id="start">\n    <div class="wrap">\n'
            '      <div class="sec-head rv">\n'
            '        <p class="kicker"><span class="idx">01</span><span>Start here</span></p>\n'
            '        <h2>Three write-ups that show how I think.</h2>\n'
            '        <p>Hand-picked, not sorted by recency. If you only have ten minutes, read these.</p>\n'
            '      </div>\n      <div class="cards2">' + "".join(items) + '</div>\n'
            '    </div>\n  </section>')


def experience_html():
    rows = []
    for i, e in enumerate(EXPERIENCE):
        lis = "".join(f"<li>{b}</li>" for b in e["bullets"])
        rows.append(
            f'<div class="xp-item" data-step="{i}">'
            f'<div class="xp-when">{esc(e["when"])}</div>'
            f'<h3>{esc(e["org"])}</h3>'
            f'<p class="xp-role">{esc(e["role"])}</p>'
            f'<ul>{lis}</ul></div>')
    return f"""
  <section class="band dark xp-pin" id="xp">
    <div class="xp-stage">
      <div class="wrap wide xp-grid">
        <div class="xp-left">
          <p class="kicker"><span class="idx">02</span><span>Experience</span></p>
          <h2>Systems engineer,<br>moving into AI infrastructure.</h2>
          <p class="pitch">“I don’t want to train the models — I want to build the
          engine that makes them fast and reliable.”</p>
          <div class="xp-cta">
            <a class="btn primary" href="{LINKEDIN_URL}" target="_blank" rel="noopener">Full history on LinkedIn ↗</a>
            <span class="xp-note">No PDF here on purpose — this page <em>is</em> the résumé,
            and it’s always current.</span>
          </div>
        </div>
        <div class="xp-right">
          <div class="rail" aria-hidden="true"><i id="railfill"></i></div>
          {"".join(rows)}
        </div>
      </div>
    </div>
  </section>"""


def activity_html(contrib):
    if not contrib:
        return ""
    return f"""
  <section class="band" id="activity">
    <div class="wrap wide split">
      <div class="sec-head rv">
        <p class="kicker"><span class="idx">03</span><span>Activity</span></p>
        <h2>Showing up, in public.</h2>
        <p>Every gold square is a commit to this log or its notes — pulled from GitHub at build time.</p>
        <p class="gh-note">Started logging publicly in spring 2026 — the streak is young on purpose.</p>
      </div>
      <div class="gh rv">
        <div class="gh-head">
          <a class="gh-title" href="https://github.com/{GITHUB_USER}" target="_blank" rel="noopener">github.com/{GITHUB_USER}</a>
          <span class="gh-title">Last {CONTRIB_WEEKS} weeks</span>
        </div>
        <div class="gh-months" id="ghmonths" aria-hidden="true"></div>
        <div class="gh-grid" id="ghgrid" role="img" aria-label="GitHub contribution calendar, last {CONTRIB_WEEKS} weeks"></div>
        <div class="gh-foot">
          <span class="gh-leg">Less
            <i style="background:var(--gh0)"></i><i style="background:var(--gh1)"></i><i style="background:var(--gh2)"></i><i style="background:var(--gh3)"></i><i style="background:var(--gh4)"></i>
          More</span>
        </div>
      </div>
    </div>
  </section>"""


# The code window shows the REAL safety-belt lines from collect() above — if that
# code changes, update this snippet (they are asserted to stay in sync in main()).
SYSTEM_SECTION = """
  <section class="band dark" id="sys">
    <div class="wrap">
      <div class="sec-head rv">
        <p class="kicker"><span class="idx">04</span><span>The system</span></p>
        <h2>This site is itself a project.</h2>
        <p>No framework, no build dependencies — one Python script turns a private second-brain
        repo into this page. This is the actual code that keeps private notes private.</p>
      </div>
      <div class="frame rv">
        <div class="win" id="win">
          <div class="win-bar">
            <div class="dots" aria-hidden="true"><i></i><i></i><i></i></div>
            <span class="fname">site/build.py — dependency-free static site generator</span>
          </div>
          <div class="win-body">
            <div class="tree" aria-hidden="true">
<b>~/github</b>
├ mind/               <span class="lock">🔒 private</span>
│ ├ resume/
│ ├ bq/ · system-design/
│ └ cli/  <span class="lock">spaced repetition</span>
└ <b>Yuan-Hsuan.github.io/</b>
  ├ leetcode/*.md
  ├ ai-knowledge/*.md
  ├ <span class="sel"> site/build.py ●</span>
  └ index.html  <span class="lock">← output</span>
            </div>
            <div class="code"><pre>
<span class="ln" style="--d:.05s"><span class="no"></span><span class="c"># the safety belt: private notes can never render</span></span>
<span class="ln" style="--d:.15s"><span class="no"></span><span class="k">def</span> <span class="f">collect</span>():</span>
<span class="ln" style="--d:.25s"><span class="no"></span>    cards = []</span>
<span class="ln" style="--d:.35s"><span class="no"></span>    <span class="k">for</span> path <span class="k">in</span> <span class="f">sorted</span>((ROOT / d).rglob(<span class="s">"*.md"</span>)):</span>
<span class="ln" style="--d:.45s"><span class="no"></span>        meta, body = parse_frontmatter(path.read_text())</span>
<span class="ln" style="--d:.55s"><span class="no"></span>        <span class="hl"><span class="k">if</span> meta.get(<span class="s">"visibility"</span>) != <span class="s">"public"</span>:</span></span>
<span class="ln" style="--d:.65s"><span class="no"></span>            <span class="hl"><span class="k">continue</span>  <span class="c"># ← everything else stays private</span></span></span>
<span class="ln" style="--d:.75s"><span class="no"></span>        cards.append(…)</span>
<span class="ln" style="--d:.85s"><span class="no"></span>    <span class="k">return</span> cards<span class="cursor" aria-hidden="true"></span></span>
</pre></div>
          </div>
        </div>
      </div>
      <p class="win-cap rv">Markdown in → one Python script (stdlib only) → static HTML out.
      No backend, cookieless analytics. The Notion “Coding Report” pipeline feeds leetcode/*.md.</p>
    </div>
  </section>"""


def ai_notes_html(cards):
    ai = [c for c in cards if c["domain"] == "ai"]
    if not ai:
        return ""
    rows = []
    for i, c in enumerate(ai):
        rows.append(
            f'<a class="row rv" style="--d:{i*0.06:.2f}s" href="#card-{esc(c["id"])}" '
            f'onclick="expandCard(\'{esc(c["id"])}\');return false;">'
            f'<span class="i">{i+1:02d}</span><span class="t">{esc(c["title"])}</span>'
            f'<span class="d">cs224n · mastery {c["mastery"]}/5</span></a>')
    return ('\n  <section class="band" id="ai">\n    <div class="wrap wide split">\n'
            '      <div class="sec-head rv">\n'
            '        <p class="kicker"><span class="idx">05</span><span>AI notes</span></p>\n'
            '        <h2>Stanford CS224n, worked through by hand.</h2>\n'
            '        <p>Concept notes written after doing the math and the PyTorch myself — not summaries of slides.</p>\n'
            '      </div>\n      <div class="rows">' + "".join(rows) + '</div>\n'
            '    </div>\n  </section>')


def log_html(cards, solved):
    n_lc = sum(1 for c in cards if c["domain"] == "leetcode")
    c = (solved or {}).get("counts", {})
    total, e, m, h = (c.get(k, 0) for k in ("total", "easy", "medium", "hard"))
    user = (solved or {}).get("username", GITHUB_USER)
    bar = ""
    if total:
        bar = f"""
      <div class="diffbar" role="img" aria-label="Difficulty split: {e} easy, {m} medium, {h} hard">
        <span class="e" style="flex:{e}"></span><span class="m" style="flex:{m}"></span><span class="h" style="flex:{h}"></span>
      </div>
      <div class="difflab rv">
        <span><span class="dot" style="background:var(--easy)"></span>Easy {e}</span>
        <span><span class="dot" style="background:var(--medium)"></span>Medium {m}</span>
        <span><span class="dot" style="background:var(--hard)"></span>Hard {h}</span>
      </div>"""
    return f"""
  <section class="band" id="log">
    <div class="wrap wide">
      <div class="split loghead">
        <div class="sec-head rv">
          <p class="kicker"><span class="idx">06</span><span>Practice log</span></p>
          <h2>The daily reps.</h2>
          <p>{total} solved is just volume — the {n_lc} write-ups are the point: pattern, trade-offs,
          and a recall prompt for spaced repetition. Click a card to read.</p>
        </div>
        <div class="rv">
          <div class="lc-inline"><span><b>{total}</b> solved</span><span><b>{n_lc}</b> write-ups</span>
            <a href="https://leetcode.com/u/{user}/" target="_blank" rel="noopener">leetcode.com/u/{user} ↗</a></div>{bar}
        </div>
      </div>
      <div class="controls rv">
        <select id="f-domain" aria-label="Filter by domain"><option value="">All domains</option>
          <option value="leetcode">LeetCode</option><option value="ai">AI Knowledge</option></select>
        <select id="f-diff" aria-label="Filter by difficulty"><option value="">All difficulty</option>
          <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></select>
        <select id="f-tag" aria-label="Filter by topic"><option value="">All topics</option></select>
        <input id="f-search" type="search" placeholder="search…" style="flex:0 1 180px" aria-label="Search write-ups">
        <span class="count" id="c-count"></span>
      </div>
      <div id="grid" class="tilegrid"></div>
    </div>
  </section>

  <div class="reader" id="reader" hidden>
    <div class="reader-scrim" id="reader-scrim"></div>
    <article class="reader-panel" role="dialog" aria-modal="true" aria-labelledby="reader-title">
      <header class="reader-head">
        <h3 id="reader-title"></h3>
        <div class="reader-pills" id="reader-pills"></div>
        <button class="r-close" id="reader-close" aria-label="Close">✕</button>
      </header>
      <div class="rbody" id="reader-body"></div>
    </article>
  </div>"""


FOOTER = f"""
  <footer class="band dark">
    <div class="wrap rv">
      <p class="fline">Built from markdown by <code>site/build.py</code> — static, no backend,
      privacy-friendly analytics (<a href="https://www.goatcounter.com" target="_blank" rel="noopener">GoatCounter</a>,
      no cookies). Only <code>visibility:public</code> content is shown.</p>
      <div class="fm">
        <span>Last build __BUILD_MONTH__</span>
        <a href="https://github.com/{GITHUB_USER}" target="_blank" rel="noopener">GitHub ↗</a>
        <a href="{LINKEDIN_URL}" target="_blank" rel="noopener">LinkedIn ↗</a>
        <a href="https://leetcode.com/u/{GITHUB_USER}/" target="_blank" rel="noopener">LeetCode ↗</a>
      </div>
    </div>
  </footer>

  <nav class="floatnav" id="floatnav" aria-label="Sections">
    <a href="#top" data-sec="top">Graph</a>
    <a href="#start" data-sec="start">Start</a>
    <a href="#xp" data-sec="xp">Résumé</a>
    <a href="#ai" data-sec="ai">Notes</a>
    <a href="#log" data-sec="log">Log</a>
  </nav>"""


def page(cards, graph, solved, contrib):
    data = ("<script>\n"
            f"const CARDS = {json.dumps(cards, ensure_ascii=False)};\n"
            f"const GRAPH = {json.dumps(graph, ensure_ascii=False)};\n"
            f"const TAGS = {json.dumps(sorted({t for c in cards for t in c['tags']}), ensure_ascii=False)};\n"
            f"const CONTRIB = {json.dumps(contrib, ensure_ascii=False)};\n"
            "</script>")
    build_month = date.today().strftime("%Y-%m")
    out = (HEAD + "\n<body>\n"
           + hero_html(cards, solved)
           + start_here_html(cards)
           + experience_html()
           + activity_html(contrib)
           + SYSTEM_SECTION
           + ai_notes_html(cards)
           + log_html(cards, solved)
           + FOOTER + "\n" + data + "\n" + SCRIPT + "\n</body>\n</html>")
    return out.replace("__BUILD_MONTH__", build_month)


# ---- static chunks ----------------------------------------------------------
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Yuan-Hsuan Wen — Software Engineer · CS/AI Notes &amp; LeetCode Write-ups</title>
<meta name="description" content="LeetCode write-ups, CS224n NLP notes, and system-design study — an early-career engineer learning CS &amp; AI in public.">
<link rel="canonical" href="https://yuan-hsuan.github.io/">
<meta name="author" content="Yuan-Hsuan Wen">
<meta name="theme-color" content="#f1eee7">
<!-- favicons -->
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<!-- Open Graph (link previews on LinkedIn / Slack / iMessage) -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="Yuan-Hsuan Wen">
<meta property="og:title" content="Yuan-Hsuan Wen — Software Engineer · CS/AI Notes &amp; LeetCode Write-ups">
<meta property="og:description" content="LeetCode write-ups, CS224n NLP notes, and system-design study — learning CS &amp; AI in public.">
<meta property="og:url" content="https://yuan-hsuan.github.io/">
<meta property="og:image" content="https://yuan-hsuan.github.io/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Yuan-Hsuan Wen — engineer &amp; writer learning in public: LeetCode, CS224n/NLP notes, system design.">
<!-- Twitter / X card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Yuan-Hsuan Wen — Software Engineer · CS/AI Notes &amp; LeetCode Write-ups">
<meta name="twitter:description" content="LeetCode write-ups, CS224n NLP notes, and system-design study — learning CS &amp; AI in public.">
<meta name="twitter:image" content="https://yuan-hsuan.github.io/og-image.png">
<!-- structured data: mark this site up as a Person for Google -->
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Person","name":"Yuan-Hsuan Wen","url":"https://yuan-hsuan.github.io/","jobTitle":"Software Engineer","description":"Early-career software engineer learning CS & AI in public — LeetCode, CS224n/NLP, system design.","sameAs":["https://github.com/Yuan-Hsuan","https://www.linkedin.com/in/yuan-hsuan-wen/","https://leetcode.com/u/Yuan-Hsuan/"]}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400;1,9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script data-goatcounter="https://yuanhsuan.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
<style>
/* Design contract: ../DESIGN.md — single cream theme, full-bleed cream/black bands. */
:root{
  --bg:#f1eee7; --surface:#ffffff; --surface2:#f5f1e8; --border:#e3ddd0;
  --fg:#232323; --muted:#5b5a56; --accent:#40392e; --gold:#d6a878;
  --lc:#3a352c; --ai:#8a8378; --panel:#232323;
  --easy:#8a8a8a; --medium:#5b5a56; --hard:#232323;
  --gh0:#e7e0d1; --gh1:#eeddc2; --gh2:#dfb98a; --gh3:#c08a4d; --gh4:#8f6132;
  --serif:"Fraunces",Georgia,serif;
  --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --ease:cubic-bezier(.4,0,.2,1);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;overflow-x:clip;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:16px;line-height:1.65;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
::selection{background:color-mix(in srgb,var(--gold) 45%,transparent)}
.wrap{max-width:960px;margin:0 auto;padding:0 clamp(20px,4vw,48px)}
.wrap.wide{max-width:1200px}
code,.mono{font-family:var(--mono)}
h1,h2,h3{text-wrap:balance}

/* ---- full-bleed band rhythm ---- */
.band{padding-block:clamp(4rem,9vw,8.5rem);scroll-margin-top:56px}
.band + .band:not(.dark){border-top:1px solid var(--border)}
.band.dark{background:var(--panel);
  --fg:#f1eee7; --muted:#a8a49c; --border:#413e37;
  --surface:#2a2823; --surface2:#1d1c19; --accent:#e8dcc6;
  color:var(--fg)}

/* ---- motion system (DESIGN.md §7) ---- */
.rv{opacity:0;transform:translateY(14px);
  transition:opacity .6s var(--ease),transform .6s var(--ease);transition-delay:var(--d,0s)}
.rv.in{opacity:1;transform:none}
.cursor{display:inline-block;width:.55em;height:1em;background:var(--gold);
  vertical-align:text-bottom;animation:blink .9s steps(1,end) infinite}
@keyframes blink{50%{opacity:0}}
.ping{position:relative;display:inline-block;width:8px;height:8px;
  border-radius:50%;background:var(--gold);margin-left:.5em}
.ping::after{content:"";position:absolute;inset:0;border-radius:50%;
  background:var(--gold);animation:ping 1.8s cubic-bezier(0,0,.2,1) infinite}
@keyframes ping{75%,100%{transform:scale(2.4);opacity:0}}
.cue{position:absolute;left:47%;bottom:18px;transform:translateX(-50%);
  font-family:var(--mono);font-size:.8rem;color:var(--muted);pointer-events:none;
  animation:cue 1.4s steps(7,end) infinite}
@keyframes cue{from{transform:translate(-50%,-8px);opacity:0}
  50%{opacity:1} to{transform:translate(-50%,6px);opacity:0}}
.diffbar span{transform:scaleX(0);transform-origin:left;
  transition:transform .8s var(--ease);transition-delay:var(--d,0s)}
.diffbar.in span{transform:scaleX(1)}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .rv{opacity:1;transform:none;transition:none}
  .cursor,.ping::after,.cue{animation:none}
  .diffbar span{transform:none;transition:none}
}

/* ---- mono metadata voice ---- */
.kicker{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted);
  display:flex;gap:.7em;align-items:center;flex-wrap:wrap;margin:0}
.kicker .idx{color:var(--gold);font-weight:600}

/* ---- hero (full-viewport split) ---- */
.hero2{min-height:100svh;display:flex;align-items:stretch;position:relative}
.hero2-left{flex:0 0 47%;min-width:0;display:flex;flex-direction:column;justify-content:center;
  gap:1.5rem;padding:clamp(24px,5vw,72px)}
.hero2 h1{font-family:var(--serif);font-weight:600;font-optical-sizing:auto;
  font-size:clamp(2.4rem,4.6vw,4rem);line-height:1.06;letter-spacing:-.01em;margin:0}
.hero2 h1 em{font-style:italic;font-weight:600;
  background:linear-gradient(transparent 70%,color-mix(in srgb,var(--gold) 42%,transparent) 70%)}
.hero-sub{color:var(--muted);max-width:34rem;margin:0;font-size:1.05rem}
.stats{display:flex;gap:2.2rem;border-top:1px solid var(--border);padding-top:1.2rem;flex-wrap:wrap}
.sgroup{display:flex;flex-direction:column;gap:.5rem}
.sgroup .sl{font-family:var(--mono);font-size:.62rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--muted)}
.srow{display:flex;gap:1.6rem}
.stat .n{font-family:var(--mono);font-variant-numeric:tabular-nums;
  font-size:1.5rem;font-weight:600;letter-spacing:-.02em;line-height:1.15}
.stat .l{font-family:var(--mono);font-size:.62rem;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted)}
.vdiv{width:1px;background:var(--border);align-self:stretch}
.actions{display:flex;gap:.7rem;flex-wrap:wrap}
.btn{font-family:var(--mono);font-size:.8rem;letter-spacing:.04em;
  text-decoration:none;padding:.75em 1.3em;border-radius:8px;color:var(--fg);
  border:1px solid var(--border);user-select:none;
  transition:border-color .15s,background .15s,color .15s}
.btn:hover{text-decoration:none;border-color:var(--fg)}
.btn:focus-visible,.card2:focus-visible,.row:focus-visible{outline:none;
  box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--gold)}
.btn.primary{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.btn.primary:hover{background:var(--accent);border-color:var(--accent)}
.band.dark .btn.primary{background:#f1eee7;color:#232323;border-color:#f1eee7}
.band.dark .btn.primary:hover{background:var(--gold);border-color:var(--gold)}
.hero2-right{flex:1 1 53%;align-self:stretch;position:relative;overflow:hidden;background:var(--panel)}
.hero2-right #kg{position:absolute;inset:0;width:100%;height:100%;cursor:grab}
.kg-hint{position:absolute;right:14px;bottom:12px;font-size:.74rem;color:#8a8a8a;pointer-events:none}
.kg-panel{position:absolute;right:0;top:0;bottom:0;width:min(320px,78%);background:#f5f1e8;
  border-left:1px solid #e3ddd0;transform:translateX(101%);transition:transform .28s var(--ease);
  overflow:auto;padding:18px 18px 24px;color:#232323}
.kg-panel.open{transform:none}
.kg-panel .ph{display:flex;align-items:baseline;gap:8px;margin:0 0 4px}
.kg-panel .ph b{font-family:var(--serif);font-weight:600;font-size:1.2rem}
.kg-panel .ph span{color:#5b5a56;font-size:.82rem}
.kg-panel .pclose{position:absolute;right:12px;top:10px;background:none;border:none;color:#5b5a56;
  font-size:1.1rem;cursor:pointer}
.kg-panel .pitem{display:flex;align-items:center;gap:8px;padding:9px 6px;border-bottom:1px solid #e3ddd0;
  color:#232323;cursor:pointer}
.kg-panel .pitem:hover{color:#40392e;text-decoration:none}
.kg-panel .pitem .pt{flex:1 1 auto;font-size:.9rem}
@media(max-width:900px){
  .hero2{flex-direction:column;min-height:0}
  .hero2-left{flex:none;width:100%;padding-top:88px}
  .hero2-right{flex:none;width:100%;height:56vh}
  .cue{display:none}
}

/* ---- two-column section compositions (DESIGN.md §5) ---- */
.split{display:grid;grid-template-columns:1fr 1.3fr;gap:clamp(2rem,4vw,4.5rem);align-items:start}
.split .sec-head{margin:0}
.loghead{margin:0 0 2.2rem;align-items:end}
.loghead .lc-inline{margin:0 0 1rem}
.loghead .difflab{margin:0}
@media(max-width:860px){ .split{grid-template-columns:1fr;gap:1.6rem} }

/* ---- section heads ---- */
.sec-head{margin:0 0 2.2rem}
.sec-head h2, .band h2{font-family:var(--serif);font-weight:600;font-optical-sizing:auto;
  font-size:clamp(1.6rem,2.7vw,2.2rem);letter-spacing:-.005em;line-height:1.2;margin:.5rem 0 0}
.sec-head p{margin:.5rem 0 0;color:var(--muted);max-width:44rem}

/* ---- start-here cards ---- */
.cards2{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.card2{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:1.4rem 1.4rem 1.2rem;display:flex;flex-direction:column;gap:.7rem;
  text-decoration:none;color:var(--fg);transition:border-color .15s}
.card2:hover{text-decoration:none;border-color:var(--gold)}
.card2 .meta{font-family:var(--mono);font-size:.65rem;letter-spacing:.07em;
  text-transform:uppercase;color:var(--muted)}
.card2 h3{font-family:var(--serif);font-weight:600;margin:0;font-size:1.18rem;line-height:1.3}
.card2 .why{color:var(--muted);font-size:.92rem;margin:0;flex:1}
.card2 .foot{font-family:var(--mono);font-size:.7rem;color:var(--muted);
  display:flex;justify-content:space-between;border-top:1px solid var(--border);padding-top:.7rem}
.card2 .foot .go{color:var(--fg)}
.card2 .foot .go::after{content:"→";display:inline-block;margin-left:.35em;
  transition:transform .15s var(--ease)}
@media(hover:hover){ .card2:hover .foot .go::after{transform:translateX(4px)} }

/* ---- experience: pinned scrollytelling on black ---- */
.xp-pin{height:320vh;position:relative;padding-block:0}
.xp-stage{position:sticky;top:0;min-height:100svh;display:flex;align-items:center}
.xp-grid{display:grid;grid-template-columns:minmax(280px,1fr) 1.25fr;
  gap:clamp(2rem,5vw,5rem);align-items:center;width:100%;padding-block:clamp(3rem,6vh,5rem)}
.pitch{font-family:var(--serif);font-style:italic;font-size:clamp(1.25rem,2vw,1.55rem);
  line-height:1.45;margin:1.6rem 0 2rem;border-left:3px solid var(--gold);padding-left:1.2rem}
.xp-cta .btn{display:inline-block;margin-bottom:.8rem}
.xp-note{font-family:var(--mono);font-size:.68rem;color:var(--muted);display:block;max-width:26rem}
.xp-right{position:relative;padding-left:2rem}
.rail{position:absolute;left:0;top:6px;bottom:6px;width:2px;background:rgba(255,255,255,.14)}
.rail i{position:absolute;left:0;top:0;width:100%;height:0%;background:var(--gold)}
.xp-item{padding:1.3rem 0;opacity:.15;transform:translateY(26px);
  transition:opacity .6s var(--ease),transform .6s var(--ease)}
.xp-item.on{opacity:1;transform:none}
.xp-item + .xp-item{border-top:1px solid rgba(255,255,255,.1)}
.xp-when{font-family:var(--mono);font-size:.68rem;letter-spacing:.07em;
  text-transform:uppercase;color:var(--gold)}
.xp-item h3{font-family:var(--serif);font-weight:600;margin:.3rem 0 0;font-size:1.35rem}
.xp-role{font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);margin:.2rem 0 .5rem}
.xp-item ul{margin:.2rem 0 0;padding-left:1.1rem;color:var(--muted);font-size:.95rem}
.xp-item li{margin:.3rem 0}
.xp-item li b{color:var(--fg);font-weight:600}
.xp-hook{font-family:var(--serif);font-style:italic;color:var(--gold)}
@media(max-width:900px){
  .xp-pin{height:auto;padding-block:clamp(4rem,9vw,8.5rem)}
  .xp-stage{position:static;display:block;min-height:0}
  .xp-grid{display:block;padding-block:0}
  .xp-right{margin-top:2rem}
  .xp-item{opacity:1;transform:none}
}
@media (prefers-reduced-motion:reduce){ .xp-item{opacity:1;transform:none;transition:none} }

/* ---- the system: deep device frame on black ---- */
.frame{background:#141311;border:1px solid rgba(255,255,255,.09);
  border-radius:18px;padding:clamp(8px,1.2vw,14px);box-shadow:0 24px 70px rgba(0,0,0,.45)}
.win{background:#232323;border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,.08)}
.win-bar{display:flex;align-items:center;gap:1rem;padding:.8rem 1.1rem;
  border-bottom:1px solid rgba(255,255,255,.08)}
.win-bar .dots{display:flex;gap:7px}
.win-bar .dots i{width:11px;height:11px;border-radius:50%;background:#4a463f}
.win-bar .fname{font-family:var(--mono);font-size:.72rem;color:#a8a49c;letter-spacing:.04em}
.win-body{display:grid;grid-template-columns:230px 1fr}
.tree{border-right:1px solid rgba(255,255,255,.08);padding:1.1rem 0 1.1rem 1rem;
  font-family:var(--mono);font-size:.74rem;line-height:2;color:#8f8b84;white-space:pre;overflow-x:auto}
.tree b{color:#f1eee7;font-weight:400}
.tree .lock{color:var(--gold)}
.tree .sel{background:#2f2c27;display:inline-block;width:100%;color:#f1eee7}
.code{padding:1.1rem 1.3rem;overflow-x:auto}
.code pre{margin:0;font-family:var(--mono);font-size:.8rem;line-height:1.85;color:#c9c5bd}
.ln{display:block;opacity:0;transform:translateX(8px);
  transition:opacity .45s var(--ease),transform .45s var(--ease);transition-delay:var(--d,0s)}
.win.in .ln{opacity:1;transform:none}
.ln .no{display:inline-block;width:1.4em;color:#565248;user-select:none}
.k{color:var(--gold)} .s{color:#a8b78c} .c{color:#79746a;font-style:italic}
.f{color:#e8d5b5} .hl{background:#33302a;border-radius:3px;padding:0 .2em}
@media(max-width:760px){ .win-body{grid-template-columns:1fr} .tree{display:none} }
@media (prefers-reduced-motion:reduce){ .ln{opacity:1;transform:none;transition:none} }
.win-cap{font-family:var(--mono);font-size:.7rem;color:var(--muted);margin:1rem 0 0}

/* ---- github activity ---- */
.gh{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:1.6rem;overflow-x:auto}
.gh-head{display:flex;justify-content:space-between;align-items:baseline;
  gap:1rem;margin-bottom:1.1rem;flex-wrap:wrap}
.gh-title{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted)}
a.gh-title:hover{color:var(--fg);text-decoration:none}
.gh-months{display:flex;font-family:var(--mono);font-size:.62rem;color:var(--muted);margin:0 0 .45rem}
.gh-months span{width:16px;flex:none}
.gh-grid{display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,13px);gap:3px;width:max-content}
.gh-grid i{width:13px;height:13px;border-radius:3px;background:var(--gh0);
  transform:scale(.4);opacity:0;
  transition:transform .4s var(--ease),opacity .4s var(--ease);transition-delay:var(--d,0s)}
.gh-grid.in i{transform:scale(1);opacity:1}
.gh-grid i.l1{background:var(--gh1)} .gh-grid i.l2{background:var(--gh2)}
.gh-grid i.l3{background:var(--gh3)} .gh-grid i.l4{background:var(--gh4)}
.gh-foot{display:flex;justify-content:space-between;align-items:center;
  margin-top:1rem;gap:1rem;flex-wrap:wrap}
.gh-note{font-family:var(--mono);font-size:.68rem;color:var(--muted)}
.gh-leg{display:flex;align-items:center;gap:4px;font-family:var(--mono);
  font-size:.62rem;color:var(--muted)}
.gh-leg i{width:11px;height:11px;border-radius:3px;display:inline-block}
@media (prefers-reduced-motion:reduce){ .gh-grid i{transform:none;opacity:1;transition:none} }

/* ---- note & log lists ---- */
.rows{border-top:1px solid var(--border)}
.row{display:flex;gap:1.4rem;align-items:baseline;padding:.85rem 4px;color:var(--fg);
  border-bottom:1px solid var(--border);text-decoration:none;transition:background .15s}
.row:hover{background:var(--surface);text-decoration:none}
.row .i{font-family:var(--mono);font-size:.7rem;color:var(--muted);min-width:2.2em;
  font-variant-numeric:tabular-nums}
.row .t{flex:1;font-family:var(--serif);font-size:1.02rem}
.row .d{font-family:var(--mono);font-size:.7rem;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em}
@media(max-width:560px){ .row .d{display:none} }
.lc-inline{display:flex;gap:1.8rem;align-items:baseline;flex-wrap:wrap;
  font-family:var(--mono);font-size:.78rem;color:var(--muted);
  font-variant-numeric:tabular-nums;margin:0 0 1rem}
.lc-inline b{color:var(--fg);font-weight:600;font-size:1rem}
.diffbar{display:flex;gap:2px;height:10px;border-radius:4px;overflow:hidden;
  max-width:560px;margin:0 0 .6rem}
.diffbar span{display:block}
.diffbar .m{--d:.15s} .diffbar .h{--d:.3s}
.diffbar .e{background:var(--easy)} .diffbar .m{background:var(--medium)} .diffbar .h{background:var(--hard)}
.difflab{display:flex;gap:1.6rem;margin:0 0 2rem;font-family:var(--mono);
  font-size:.7rem;color:var(--muted);flex-wrap:wrap;font-variant-numeric:tabular-nums}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:.4em}
.c-easy{color:var(--easy)} .c-medium{color:var(--medium)} .c-hard{color:var(--hard)}

/* ---- write-up archive: shopping-grid tiles + reader overlay ---- */
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 18px}
.controls select,.controls input{padding:9px 12px;border-radius:9px;border:1px solid var(--border);
  background:var(--surface);color:var(--fg);font-size:1rem;font-family:inherit}
.controls .count{color:var(--muted);font-size:.82rem;margin-left:auto;font-variant-numeric:tabular-nums}
.tilegrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:1.1rem 1.2rem 1rem;display:flex;flex-direction:column;gap:.6rem;cursor:pointer;
  user-select:none;transition:border-color .15s;animation:tileIn .45s var(--ease) both;
  animation-delay:var(--d,0s)}
@keyframes tileIn{from{opacity:0;transform:translateY(10px)}}
.tile:hover{border-color:var(--gold)}
.tile:focus-visible{outline:none;box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--gold)}
.tile .t-top{display:flex;gap:6px;flex-wrap:wrap}
.tile h3{font-family:var(--serif);font-weight:600;margin:0;font-size:1.05rem;line-height:1.35;flex:1}
.tile .tags{margin:0}
.tile .t-foot{font-family:var(--mono);font-size:.68rem;color:var(--muted);
  display:flex;justify-content:space-between;border-top:1px solid var(--border);padding-top:.65rem;margin-top:auto}
.tile .t-foot .go{color:var(--fg)}
.tile .t-foot .go::after{content:"→";display:inline-block;margin-left:.35em;transition:transform .15s var(--ease)}
@media(hover:hover){ .tile:hover .t-foot .go::after{transform:translateX(4px)} }
@media (prefers-reduced-motion:reduce){ .tile{animation:none} }
.pill{font-size:.7rem;padding:3px 9px;border-radius:20px;border:1px solid var(--border);color:var(--muted);
  text-transform:capitalize}
.pill.diff-easy{color:var(--easy);border-color:color-mix(in srgb,var(--easy) 55%,transparent)}
.pill.diff-medium{color:var(--medium);border-color:color-mix(in srgb,var(--medium) 55%,transparent)}
.pill.diff-hard{color:var(--hard);border-color:color-mix(in srgb,var(--hard) 55%,transparent)}
.pill.domain{background:var(--lc);color:var(--bg);border:none;font-weight:500}
.pill.domain.ai{background:var(--ai)}
.tags{margin:11px 0 0;display:flex;flex-wrap:wrap;gap:6px 12px}
.tags span{font-size:.74rem;color:var(--muted);font-family:var(--mono)}

/* reader overlay (the "product page" for a write-up) */
.reader{position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;
  padding:clamp(12px,3vw,32px)}
.reader[hidden]{display:none}
.reader-scrim{position:absolute;inset:0;background:rgba(20,19,17,.55);backdrop-filter:blur(3px)}
.reader-panel{position:relative;background:var(--bg);border:1px solid var(--border);border-radius:16px;
  width:min(780px,100%);max-height:min(88svh,900px);display:flex;flex-direction:column;
  box-shadow:0 30px 80px rgba(0,0,0,.35);animation:readerIn .22s var(--ease)}
@keyframes readerIn{from{opacity:0;transform:scale(.97) translateY(8px)}}
@media (prefers-reduced-motion:reduce){ .reader-panel{animation:none} }
.reader-head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;
  padding:18px 22px 14px;border-bottom:1px solid var(--border)}
.reader-head h3{font-family:var(--serif);font-weight:600;margin:0;font-size:1.35rem;letter-spacing:-.01em;
  flex:1 1 100%;padding-right:2rem}
.reader-pills{display:flex;gap:6px;flex-wrap:wrap}
.r-close{position:absolute;right:14px;top:14px;background:var(--surface);border:1px solid var(--border);
  color:var(--muted);border-radius:8px;width:32px;height:32px;cursor:pointer;font-size:.95rem;line-height:1}
.r-close:hover{color:var(--fg);border-color:var(--fg)}
.r-close:focus-visible{outline:none;box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--gold)}
.rbody{overflow:auto;padding:8px 22px 24px;overscroll-behavior:contain}
body.lock{overflow:hidden}
.rbody h3,.rbody h4,.rbody h5{font-family:var(--serif);font-weight:500;letter-spacing:-.01em}
.rbody pre{background:var(--surface2);border:1px solid var(--border);padding:14px 16px;border-radius:10px;overflow-x:auto}
.rbody code{font-family:var(--mono);font-size:.86em}
.rbody pre code{font-size:.82rem}
.rbody .katex-display{overflow-x:auto;overflow-y:hidden;padding:2px 0}   /* long equations scroll in-panel, not the page */
.rbody img{max-width:100%;height:auto}
.rbody table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.9rem;display:block;overflow-x:auto}
.rbody th,.rbody td{border:1px solid var(--border);padding:6px 10px;text-align:left}
.rbody blockquote{margin:12px 0;padding:8px 14px;border-left:3px solid var(--accent);color:var(--muted)}

/* ---- footer (black bookend) ---- */
footer.band.dark{padding-block:clamp(3rem,6vw,5rem)}
footer .fline{color:var(--muted);font-size:.85rem;max-width:44rem;margin:0}
footer .fm{font-family:var(--mono);font-size:.68rem;letter-spacing:.06em;
  text-transform:uppercase;margin-top:1rem;color:var(--muted);display:flex;gap:1.4rem;flex-wrap:wrap}
footer .fm a{color:var(--muted)}
footer .fm a:hover{color:var(--fg);text-decoration:none}

/* ---- floating tab navigator ---- */
.floatnav{position:fixed;left:50%;top:11px;transform:translateX(-50%);z-index:60;display:flex;gap:4px;
  padding:5px;background:color-mix(in srgb,#ffffff 90%,transparent);border:1px solid #e3ddd0;
  border-radius:999px;backdrop-filter:blur(12px);box-shadow:0 8px 26px rgba(0,0,0,.16)}
.floatnav a{padding:7px 16px;border-radius:999px;font-size:.86rem;color:#5b5a56;text-decoration:none;
  transition:background .2s,color .2s;white-space:nowrap}
.floatnav a:hover{color:#232323;text-decoration:none}
.floatnav a.active{background:#232323;color:#f1eee7}
@media(max-width:640px){ .floatnav a{padding:7px 11px;font-size:.78rem} }
</style>
</head>"""


# ---- client logic (plain JS, no interpolation) ------------------------------
SCRIPT = r"""<script>
const $ = id => document.getElementById(id);
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---- floating tab nav: highlight the section in view ---- */
(function(){
  const nav=$('floatnav'); if(!nav) return;
  const links=[].slice.call(nav.querySelectorAll('a'));
  const secs=links.map(a=>$(a.dataset.sec)).filter(Boolean);
  const io=new IntersectionObserver(es=>{ es.forEach(e=>{ if(e.isIntersecting){
    links.forEach(a=>a.classList.toggle('active',a.dataset.sec===e.target.id)); } }); },
    {rootMargin:'-45% 0px -45% 0px'});
  secs.forEach(s=>io.observe(s));
})();

/* ---- motion system: typewriter, reveals, odometers, scrolly, gh grid ---- */
(function(){
  /* typewriter kicker */
  const typed=$('typed');
  if(typed){
    const phrase='LEARNING IN PUBLIC';
    if(REDUCED){ typed.textContent=phrase; }
    else{ let i=0; (function tick(){ typed.textContent=phrase.slice(0,i++);
      if(i<=phrase.length) setTimeout(tick,55); })(); }
  }

  /* odometer count-up */
  const done=new WeakSet();
  function count(el){
    if(done.has(el)) return; done.add(el);
    const target=+el.dataset.n;
    if(REDUCED){ el.textContent=target; return; }
    const t0=performance.now(), dur=900;
    (function step(t){ const p=Math.min(1,(t-t0)/dur), e=1-Math.pow(1-p,3);
      el.textContent=Math.round(target*e);
      if(p<1) requestAnimationFrame(step); })(t0);
  }

  /* reveal on load (hero) + on scroll (everything else) */
  const heroRv=document.querySelectorAll('.hero2 .rv');
  requestAnimationFrame(()=>requestAnimationFrame(()=>heroRv.forEach(el=>el.classList.add('in'))));
  document.querySelectorAll('.hero2 .odo').forEach(el=>{
    if(REDUCED) el.textContent=el.dataset.n; else setTimeout(()=>count(el),500); });
  const io=new IntersectionObserver(es=>{ for(const e of es){ if(e.isIntersecting){
    e.target.classList.add('in');
    e.target.querySelectorAll('.odo').forEach(count);
    io.unobserve(e.target); } } },{threshold:.2});
  document.querySelectorAll('.band .rv, footer .rv, .diffbar, .gh-grid').forEach(el=>io.observe(el));
  const win=$('win'); if(win) io.observe(win);

  /* résumé pinned scrollytelling (sticky stage + scroll progress) */
  const pin=$('xp');
  if(pin){
    const items=pin.querySelectorAll('.xp-item');
    const rail=$('railfill');
    const T=[0.04,0.42,0.74];
    function xp(){
      if(matchMedia('(max-width:900px)').matches || REDUCED){
        items.forEach(it=>it.classList.add('on')); if(rail) rail.style.height='100%'; return; }
      const r=pin.getBoundingClientRect();
      const total=r.height-innerHeight;
      const p=Math.min(1,Math.max(0,-r.top/total));
      items.forEach((it,i)=>it.classList.toggle('on',p>=T[Math.min(i,T.length-1)]));
      if(rail) rail.style.height=(p*100)+'%';
    }
    addEventListener('scroll',xp,{passive:true});
    addEventListener('resize',xp);
    xp();
  }

  /* github contribution grid (CONTRIB is embedded at build time) */
  const grid=$('ghgrid');
  if(grid && typeof CONTRIB!=='undefined' && CONTRIB && CONTRIB.levels){
    let cells='';
    CONTRIB.levels.forEach((l,i)=>{
      const w=Math.floor(i/7), d=i%7;
      cells+='<i class="l'+l+'" style="--d:'+(w*30+d*8)+'ms"></i>';
    });
    grid.innerHTML=cells;
    const months=$('ghmonths');
    if(months) months.innerHTML=CONTRIB.months.map(m=>'<span>'+m+'</span>').join('');
  }
})();

/* ---- write-up archive: shopping-grid tiles + reader overlay ---- */
(function(){
  const grid=$('grid'); if(!grid) return;
  const tagSel=$('f-tag');
  TAGS.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;tagSel.appendChild(o);});
  const diffPill=d=>d?'<span class="pill diff-'+d+'">'+d+'</span>':'';
  const domPill=d=>'<span class="pill domain'+(d==='ai'?' ai':'')+'">'+(d==='ai'?'AI':'LeetCode')+'</span>';
  function tileHTML(c,i){
    return '<article class="tile" id="card-'+c.id+'" data-id="'+c.id+'" tabindex="0" role="button" '
      +'aria-haspopup="dialog" style="--d:'+((i%12)*40)+'ms">'
      +'<div class="t-top">'+domPill(c.domain)+diffPill(c.difficulty)+'</div>'
      +'<h3>'+c.title+'</h3>'
      +'<div class="tags">'+c.tags.slice(0,3).map(t=>'<span>#'+t+'</span>').join('')+'</div>'
      +'<div class="t-foot"><span>mastery '+c.mastery+'/5</span><span class="go">Read</span></div></article>';
  }
  function draw(list){
    grid.innerHTML=list.map(tileHTML).join('')||'<p style="color:var(--muted)">No cards match.</p>';
    $('c-count').textContent=list.length+' / '+CARDS.length;
    grid.querySelectorAll('.tile').forEach(el=>{
      el.onclick=()=>openReader(el.dataset.id);
      el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openReader(el.dataset.id); } };
    });
  }
  function apply(){
    const d=$('f-domain').value,diff=$('f-diff').value,tag=$('f-tag').value,q=$('f-search').value.toLowerCase();
    draw(CARDS.filter(c=>(!d||c.domain===d)&&(!diff||c.difficulty===diff)&&(!tag||c.tags.includes(tag))
      &&(!q||(c.title+' '+c.tags.join(' ')).toLowerCase().includes(q))));
  }
  ['f-domain','f-diff','f-tag','f-search'].forEach(id=>$(id).addEventListener('input',apply));
  draw(CARDS);

  /* reader overlay */
  const reader=$('reader'), rTitle=$('reader-title'), rPills=$('reader-pills'),
        rBody=$('reader-body'), rClose=$('reader-close'), rScrim=$('reader-scrim');
  let lastFocus=null;
  function openReader(id){
    const c=CARDS.find(x=>x.id===id); if(!c||!reader) return;
    lastFocus=document.activeElement;
    rTitle.textContent=c.title;
    rPills.innerHTML=domPill(c.domain)+diffPill(c.difficulty)+'<span class="pill">mastery '+c.mastery+'/5</span>';
    rBody.innerHTML=c.body_html; rBody.scrollTop=0;
    reader.hidden=false; document.body.classList.add('lock');
    if(window.renderMathInElement) renderMathInElement(rBody,{delimiters:[
      {left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});
    history.replaceState(null,'','#card-'+id);
    rClose.focus();
  }
  function closeReader(){
    if(reader.hidden) return;
    reader.hidden=true; document.body.classList.remove('lock');
    history.replaceState(null,'',location.pathname+location.search);
    if(lastFocus&&lastFocus.focus) lastFocus.focus();
  }
  rClose.onclick=closeReader;
  rScrim.onclick=closeReader;
  addEventListener('keydown',e=>{ if(e.key==='Escape') closeReader(); });
  window.expandCard=openReader;   // graph panel + curated picks land here
  window.addEventListener('load',()=>{ if(location.hash.indexOf('#card-')===0) openReader(location.hash.slice(6)); });
})();

/* ---- knowledge graph (all-visible; click a node to fan out its neighbours) ---- */
(function(){
  const cv=$('kg'); if(!cv||typeof GRAPH==='undefined'||!GRAPH.nodes) return;
  const ctx=cv.getContext('2d'), panel=$('kg-panel');
  const MONO='#ededed';                // single monochrome node colour on black
  const colr=ci=>MONO;
  const N=GRAPH.nodes, E=GRAPH.edges;
  N.forEach((n,i)=>n._i=i);
  const adj=N.map(()=>[]); E.forEach(e=>{adj[e[0]].push(e[1]); adj[e[1]].push(e[0]);});
  const edgeObjs=E.map(e=>[N[e[0]],N[e[1]]]);
  let W=0,H=0,DPR=Math.min(window.devicePixelRatio||1,2),alpha=1,hover=null,sel=null,drag=null,down=null;
  const deg=N.map((n,i)=>adj[i].length);
  const rank=N.map((n,i)=>i).sort((a,b)=>deg[b]-deg[a]);      // most-connected first
  let SHOW=N.slice(), SEDGES=edgeObjs.slice();
  function reflow(){                                          // show fewer dots on a smaller graph
    const cap = W<480?20 : W<720?34 : W<1000?52 : N.length;
    const keep=new Set(rank.slice(0,Math.min(cap,N.length)));
    SHOW=N.filter(n=>keep.has(n._i));
    SEDGES=edgeObjs.filter(e=>keep.has(e[0]._i)&&keep.has(e[1]._i)); alpha=1; }
  function resize(){ const r=cv.getBoundingClientRect(); W=r.width; H=r.height;
    cv.width=W*DPR; cv.height=H*DPR; ctx.setTransform(DPR,0,0,DPR,0,0); reflow(); }
  new ResizeObserver(resize).observe(cv); resize();
  N.forEach((n,i)=>{ const a=i*2.399, R=Math.min(W,H)*(0.12+0.28*Math.sqrt((i%23)/23));
    n.x=W/2+Math.cos(a)*R + (n.ci? -120:120); n.y=H/2+Math.sin(a)*R; n.vx=0; n.vy=0;
    n._b=REDUCED?0:400+i*40; });                              // staggered pop-in (DESIGN.md §7.2 #5)
  const born=performance.now();
  const isNbr=n=>sel&&(n===sel||adj[sel._i].indexOf(n._i)>=0);

  function step(){
    const cx=W/2,cy=H/2;
    for(const n of SHOW){ n.vx+=(cx-n.x)*0.004; n.vy+=(cy-n.y)*0.004; }
    for(let i=0;i<SHOW.length;i++)for(let j=i+1;j<SHOW.length;j++){
      const a=SHOW[i],b=SHOW[j]; let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||.01,d=Math.sqrt(d2);
      let f=Math.min((a.r*b.r*11)/d2,40); a.vx+=dx/d*f; a.vy+=dy/d*f; b.vx-=dx/d*f; b.vy-=dy/d*f; }
    for(const e of SEDGES){ const a=e[0],b=e[1];
      const spread=sel&&(a===sel||b===sel)?95:0;               // fan neighbours of selected out
      let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||.01;
      let k=(d-(a.r+b.r+40+spread))*0.02; a.vx+=dx/d*k; a.vy+=dy/d*k; b.vx-=dx/d*k; b.vy-=dy/d*k; }
    for(const n of SHOW){ if(n===drag)continue;
      n.vx=Math.max(-8,Math.min(8,n.vx*0.9)); n.vy=Math.max(-8,Math.min(8,n.vy*0.9));
      n.x+=n.vx*alpha; n.y+=n.vy*alpha;
      n.x=Math.max(n.r+4,Math.min(W-n.r-4,n.x)); n.y=Math.max(n.r+4,Math.min(H-n.r-4,n.y)); }
    if(alpha>0.25) alpha*=0.992;                               // settle, keep a little life
  }
  function appear(n){ return Math.min(1,Math.max(0,(performance.now()-born-n._b)/350)); }
  function draw(){
    ctx.clearRect(0,0,W,H);
    for(const e of SEDGES){ const a=e[0],b=e[1], note=a.type==='note'?a:b, hot=sel&&(a===sel||b===sel);
      const ap=Math.min(appear(a),appear(b)); if(ap<=0) continue;
      ctx.strokeStyle=colr(note.ci); ctx.globalAlpha=(hot?0.85:(sel?0.06:0.18))*ap; ctx.lineWidth=hot?1.6:0.9;
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); }
    ctx.globalAlpha=1;
    for(const n of SHOW){
      const ap=appear(n); if(ap<=0) continue;
      const c=colr(n.ci), dim=sel&&!isNbr(n);
      ctx.globalAlpha=(dim?0.28:1)*ap;
      ctx.beginPath(); ctx.arc(n.x,n.y,n.r*ap,0,6.283);
      if(n.type==='tag'){ ctx.fillStyle=c; ctx.fill(); }          // topics: solid
      else { ctx.fillStyle='#232323'; ctx.fill(); ctx.lineWidth=2.4; ctx.strokeStyle=c; ctx.stroke(); }  // notes: hollow ring on the charcoal graph
      ctx.globalAlpha=1;
    }
    for(const n of SHOW){                                        // labels on top
      if(appear(n)<1) continue;
      const dim=sel&&!isNbr(n);
      // big balls (topics) always labelled; small balls (notes) only when clicked/hovered
      const show = n.type==='tag' || n===hover || isNbr(n);
      if(!show) continue;
      const lab = n.type==='tag' ? n.label : n.full.replace(/^\d+\.\s*/,'');
      ctx.globalAlpha=dim?0.3:1;
      ctx.font=(n.type==='tag'?'600 12px':'500 11px')+' Inter,sans-serif';
      ctx.textAlign='center'; ctx.textBaseline='top';
      ctx.lineWidth=3; ctx.strokeStyle='#232323'; ctx.strokeText(lab,n.x,n.y+n.r+3);  // charcoal halo
      ctx.fillStyle='#ededed'; ctx.fillText(lab,n.x,n.y+n.r+3);                     // light labels
    }
    ctx.globalAlpha=1;
  }
  let visible=true;                                             // pause the loop off-screen
  new IntersectionObserver(es=>{ visible=es[0].isIntersecting; },{threshold:0}).observe(cv);
  function loop(){ if(visible && !document.hidden){ step(); draw(); } requestAnimationFrame(loop); } loop();

  function nodeAt(x,y){ for(let i=SHOW.length-1;i>=0;i--){const n=SHOW[i];
    if((x-n.x)**2+(y-n.y)**2<=(n.r+3)**2) return n;} return null; }
  function selectNode(n){
    sel=n; alpha=Math.max(alpha,0.9);
    const nbrs = adj[n._i].map(i=>N[i]);
    let h='<button class="pclose" title="close" aria-label="Close panel">✕</button>';
    if(n.type==='tag'){
      h+='<div class="ph"><b>'+n.label+'</b><span>'+n.count+' write-up'+(n.count>1?'s':'')+'</span></div>';
      h+=n.items.map(it=>'<a class="pitem" data-id="'+it.id+'"><span class="pt">'+it.title+'</span>'
        +(it.difficulty?'<span class="pill diff-'+it.difficulty+'">'+it.difficulty+'</span>':'')+'</a>').join('');
    } else {
      h+='<div class="ph"><b>'+n.full+'</b></div>';
      h+='<a class="pitem" data-open="'+n.cardId+'"><span class="pt">Read the write-up ▸</span></a>';
      h+='<div class="ph" style="margin-top:14px"><span>Topics</span></div>';
      h+=nbrs.filter(x=>x.type==='tag').map(x=>'<a class="pitem" data-tag="'+x._i+'"><span class="pt">'+x.label+'</span></a>').join('');
    }
    panel.innerHTML=h; panel.classList.add('open');
    panel.querySelector('.pclose').onclick=()=>{ panel.classList.remove('open'); sel=null; alpha=Math.max(alpha,0.7); };
    panel.querySelectorAll('.pitem').forEach(a=>a.onclick=()=>{
      if(a.dataset.id||a.dataset.open) window.expandCard(a.dataset.id||a.dataset.open);
      else if(a.dataset.tag) selectNode(N[+a.dataset.tag]);
    });
  }
  cv.addEventListener('mousemove',e=>{ const r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    if(drag){ drag.x=x; drag.y=y; drag.vx=drag.vy=0; return; }
    hover=nodeAt(x,y); cv.style.cursor=hover?'pointer':'grab'; });
  cv.addEventListener('mousedown',e=>{ const r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    const n=nodeAt(x,y); down={n,x,y,moved:false}; if(n){drag=n; alpha=Math.max(alpha,0.8);} });
  window.addEventListener('mousemove',e=>{ if(down&&!down.moved){ const r=cv.getBoundingClientRect();
    if(Math.abs(e.clientX-r.left-down.x)+Math.abs(e.clientY-r.top-down.y)>4) down.moved=true; } });
  window.addEventListener('mouseup',()=>{ if(down&&!down.moved){
      if(down.n) selectNode(down.n);
      else { sel=null; panel.classList.remove('open'); alpha=Math.max(alpha,0.6); } }
    drag=null; down=null; });
})();
</script>"""


def main():
    cards = collect()
    graph = build_graph(cards)
    solved = load_solved()
    contrib = load_contrib()
    OUT.write_text(page(cards, graph, solved, contrib), encoding="utf-8")
    n_lc = sum(1 for c in cards if c["domain"] == "leetcode")
    n_ai = sum(1 for c in cards if c["domain"] == "ai")
    print(f"Wrote {OUT}  ({len(cards)} cards: {n_lc} lc + {n_ai} ai, "
          f"{len(graph['nodes'])} nodes, {len(graph['edges'])} edges, "
          f"contrib={'yes' if contrib else 'no'})")


if __name__ == "__main__":
    main()
