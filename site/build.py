#!/usr/bin/env python3
"""
build.py — static site generator for the "Learning in Public" portfolio.

Walks the public content folders, reads each file's YAML frontmatter (per ../SCHEMA.md),
and writes a single self-contained ../index.html:

  1. an interactive **knowledge graph** (Obsidian-style, note + topic nodes),
  2. a **LeetCode coverage** panel (from site/solved.json), and
  3. the **deep-dive write-up cards** (only `visibility: public`).

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
from collections import Counter, defaultdict
from pathlib import Path

# ---- config -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent          # repo root
CONTENT_DIRS = ["leetcode", "ai-knowledge"]            # public domains shown on the site
GITHUB_USER = "Yuan-Hsuan"
OUT = ROOT / "index.html"

WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")             # [[note]] links, Obsidian-style

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
                      "r": round(7 + 7 * (c["words"] / maxw) ** 0.5, 1)})
    maxd = max((len(v) for v in tag_notes.values()), default=1) or 1
    for t in sorted(tag_notes):
        dom = tag_dom[t].most_common(1)[0][0]
        index["tag:" + t] = len(nodes)
        nodes.append({"id": "tag:" + t, "type": "tag", "label": t, "full": t,
                      "ci": DOM_CI.get(dom, 0), "count": len(tag_notes[t]), "items": tag_notes[t],
                      "r": round(12 + 16 * (len(tag_notes[t]) / maxd) ** 0.7, 1)})

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


# ---- HTML pieces ------------------------------------------------------------
def solved_html(solved):
    if not solved:
        return ""
    c = solved.get("counts", {})
    user = solved.get("username", GITHUB_USER)
    return f"""
  <section class="block" id="coverage">
    <h2>LeetCode coverage</h2>
    <p class="lede"><b>{c.get('total',0)}</b> problems solved on
      <a href="https://leetcode.com/u/{user}/" target="_blank" rel="noopener">leetcode.com/u/{user}</a>.
      The cards further down are the ones I wrote up in full.</p>
    <div class="tiles">
      <div class="tile"><b>{c.get('total',0)}</b><span>solved</span></div>
      <div class="tile"><b class="c-easy">{c.get('easy',0)}</b><span>Easy</span></div>
      <div class="tile"><b class="c-medium">{c.get('medium',0)}</b><span>Medium</span></div>
      <div class="tile"><b class="c-hard">{c.get('hard',0)}</b><span>Hard</span></div>
    </div>
  </section>"""


def page(cards, graph, solved):
    data = ("<script>\n"
            f"const CARDS = {json.dumps(cards, ensure_ascii=False)};\n"
            f"const GRAPH = {json.dumps(graph, ensure_ascii=False)};\n"
            f"const TAGS = {json.dumps(sorted({t for c in cards for t in c['tags']}), ensure_ascii=False)};\n"
            "</script>")
    n_lc = sum(1 for c in cards if c["domain"] == "leetcode")
    n_ai = sum(1 for c in cards if c["domain"] == "ai")
    legend = "".join(f'<span><i data-ci="{g["ci"]}"></i>{html.escape(g["label"])}</span>'
                     for g in graph["groups"])
    return (HEAD + "\n<body>\n"
            + HEADER.replace("__USER__", GITHUB_USER).replace("__LEGEND__", legend)
            + '\n  <div class="wrap">\n'
            + solved_html(solved)
            + CARDS_SECTION.replace("__NLC__", str(n_lc)).replace("__NAI__", str(n_ai))
            + FOOTER + "\n" + data + "\n" + SCRIPT + "\n</body>\n</html>")


# ---- static chunks ----------------------------------------------------------
HEAD = """<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Yuan-Hsuan Wen · Learning in Public</title>
<meta name="description" content="A living knowledge graph of my CS / AI / LeetCode practice.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
:root{  /* cream site (contentarchitecture #feature) + black graph */
  --bg:#f1eee7; --surface:#ffffff; --surface2:#f5f1e8; --border:#e3ddd0;
  --fg:#232323; --muted:#5b5a56; --accent:#40392e; --gold:#d6a878;
  --lc:#3a352c; --ai:#8a8378; --kg-link:#4d4d4d;
  --easy:#8a8a8a; --medium:#5b5a56; --hard:#232323;
  --serif:"Fraunces",Georgia,serif; --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;overflow-x:clip}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:16px;line-height:1.65;
  -webkit-font-smoothing:antialiased;}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
.wrap{max-width:880px;margin:0 auto;padding:0 24px}
code,.mono{font-family:var(--mono)}

/* header */
.top{position:sticky;top:0;z-index:20;backdrop-filter:blur(10px);
  background:color-mix(in srgb,var(--bg) 82%,transparent);border-bottom:1px solid var(--border)}
.top .wrap{display:flex;align-items:center;gap:16px;height:58px}
.brand{font-family:var(--serif);font-weight:600;font-size:1.05rem;letter-spacing:-.01em}
.top nav{margin-left:auto;display:flex;gap:20px;font-size:.9rem}
.top nav a{color:var(--muted)} .top nav a:hover{color:var(--fg);text-decoration:none}
.theme-btn{background:none;border:1px solid var(--border);color:var(--muted);border-radius:8px;
  width:34px;height:34px;cursor:pointer;font-size:.95rem}
.theme-btn:hover{color:var(--fg)}
header.hero{padding:80px 0 34px}
header.hero h1{font-family:var(--serif);font-weight:500;font-size:clamp(2.4rem,6vw,3.8rem);line-height:1.05;
  letter-spacing:-.02em;margin:0 0 18px}
header.hero .sub{font-size:1.15rem;color:var(--muted);max-width:40ch;margin:0}
header.hero .cn{color:var(--muted);opacity:.8;font-size:1rem;margin:8px 0 0}
.hero-links{margin:26px 0 0;display:flex;gap:12px;flex-wrap:wrap}
.hero-links a{border:1px solid var(--border);background:var(--surface);color:var(--fg);
  padding:9px 16px;border-radius:10px;font-size:.9rem}
.hero-links a:hover{border-color:var(--accent);text-decoration:none}

/* section shell */
.block{padding:52px 0 8px;scroll-margin-top:72px}
.hero2{scroll-margin-top:0}
.block h2{font-family:var(--serif);font-weight:500;font-size:1.9rem;letter-spacing:-.01em;margin:0 0 6px}
.lede{color:var(--muted);margin:0 0 22px;max-width:56ch}

/* knowledge graph */
.kg-shell{position:relative;border:1px solid var(--border);border-radius:16px;overflow:hidden;
  background:radial-gradient(120% 120% at 50% 0%,var(--surface) 0%,var(--bg) 100%);
  width:min(96vw,1320px);margin-left:50%;transform:translateX(-50%)}
#kg{display:block;width:100%;height:min(82vh,820px);cursor:grab}
.kg-legend{position:absolute;left:14px;top:12px;display:flex;gap:14px;font-size:.78rem;color:var(--muted);
  background:color-mix(in srgb,var(--bg) 60%,transparent);padding:6px 10px;border-radius:9px;pointer-events:none}
.kg-legend i{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px;vertical-align:middle}
.kg-hint{position:absolute;right:14px;bottom:12px;font-size:.74rem;color:#8a8a8a;pointer-events:none}
.kg-crumb{position:absolute;left:14px;top:12px;display:none;align-items:center;gap:10px;z-index:3}
.kg-crumb.show{display:flex}
.kg-crumb button{background:var(--surface);border:1px solid var(--border);color:var(--fg);
  border-radius:8px;padding:6px 12px;cursor:pointer;font:inherit;font-size:.82rem}
.kg-crumb button:hover{border-color:var(--accent);color:var(--accent)}
.kg-crumb span{font-family:var(--serif);font-size:1.05rem}
.kg-panel{position:absolute;right:0;top:0;bottom:0;width:min(320px,78%);background:var(--surface);
  border-left:1px solid var(--border);transform:translateX(101%);transition:transform .28s ease;
  overflow:auto;padding:18px 18px 24px}
.kg-panel.open{transform:none}
.kg-panel .ph{display:flex;align-items:baseline;gap:8px;margin:0 0 4px}
.kg-panel .ph b{font-family:var(--serif);font-weight:600;font-size:1.2rem}
.kg-panel .ph span{color:var(--muted);font-size:.82rem}
.kg-panel .pclose{position:absolute;right:12px;top:10px;background:none;border:none;color:var(--muted);
  font-size:1.1rem;cursor:pointer}
.kg-panel .pitem{display:flex;align-items:center;gap:8px;padding:9px 6px;border-bottom:1px solid var(--border);
  color:var(--fg);cursor:pointer}
.kg-panel .pitem:hover{color:var(--accent);text-decoration:none}
.kg-panel .pitem .pt{flex:1 1 auto;font-size:.9rem}

/* tiles */
.tiles{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 6px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 20px;min-width:96px}
.tile b{font-family:var(--serif);font-size:1.7rem;display:block;line-height:1.1}
.tile span{color:var(--muted);font-size:.82rem}
.c-easy{color:var(--easy)} .c-medium{color:var(--medium)} .c-hard{color:var(--hard)}

/* solved table */
.solved{margin:20px 0 0}
.solved>summary{cursor:pointer;padding:11px 16px;background:var(--surface);border:1px solid var(--border);
  border-radius:11px;font-size:.92rem;user-select:none;list-style:none}
.solved>summary::-webkit-details-marker{display:none}
.solved>summary::before{content:"▸ ";color:var(--muted)}
.solved[open]>summary::before{content:"▾ "}
.solved-controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0 8px}
.solved-controls input,.solved-controls select{padding:9px 12px;border-radius:9px;border:1px solid var(--border);
  background:var(--surface);color:var(--fg);font-size:.9rem;font-family:inherit}
#lc-count{color:var(--muted);font-size:.82rem;margin-left:auto}
.solved-wrap{max-height:520px;overflow:auto;border:1px solid var(--border);border-radius:11px}
#lc-table{border-collapse:collapse;width:100%;font-size:.9rem}
#lc-table th{position:sticky;top:0;background:var(--bg);text-align:left;padding:9px 14px;
  border-bottom:1px solid var(--border);font-size:.76rem;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
#lc-table td{padding:8px 14px;border-bottom:1px solid var(--border)}
#lc-table td.num{color:var(--muted);font-family:var(--mono);width:58px}
.paid{font-size:.7rem}

/* cards */
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 18px}
.controls select,.controls input{padding:9px 12px;border-radius:9px;border:1px solid var(--border);
  background:var(--surface);color:var(--fg);font-size:.9rem;font-family:inherit}
.controls .count{color:var(--muted);font-size:.82rem;margin-left:auto}
.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px 22px;margin:0 0 16px;
  transition:border-color .2s,transform .2s}
.card:hover{border-color:color-mix(in srgb,var(--accent) 50%,var(--border))}
.card.flash{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 22%,transparent)}
.card-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.card h3{font-family:var(--serif);font-weight:500;margin:0;font-size:1.2rem;flex:1 1 auto;letter-spacing:-.01em}
.pill{font-size:.7rem;padding:3px 9px;border-radius:20px;border:1px solid var(--border);color:var(--muted);
  text-transform:capitalize}
.pill.diff-easy{color:var(--easy);border-color:color-mix(in srgb,var(--easy) 55%,transparent)}
.pill.diff-medium{color:var(--medium);border-color:color-mix(in srgb,var(--medium) 55%,transparent)}
.pill.diff-hard{color:var(--hard);border-color:color-mix(in srgb,var(--hard) 55%,transparent)}
.pill.domain{background:var(--lc);color:var(--bg);border:none;font-weight:500}
.pill.domain.ai{background:var(--ai)}
.tags{margin:11px 0 0;display:flex;flex-wrap:wrap;gap:6px 12px}
.tags span{font-size:.74rem;color:var(--muted);font-family:var(--mono)}
.reveal-btn{margin:14px 0 0;padding:8px 16px;border:1px solid var(--border);color:var(--fg);background:var(--surface2);
  border-radius:9px;cursor:pointer;font-size:.88rem;font-family:inherit}
.reveal-btn:hover{border-color:var(--accent);color:var(--accent)}
.body{display:none;margin-top:16px;border-top:1px solid var(--border);padding-top:8px}
.body.open{display:block}
.body h3,.body h4,.body h5{font-family:var(--serif);font-weight:500;letter-spacing:-.01em}
.body pre{background:var(--bg);border:1px solid var(--border);padding:14px 16px;border-radius:10px;overflow-x:auto}
.body code{font-family:var(--mono);font-size:.86em}
.body pre code{font-size:.82rem}
.body .katex-display{overflow-x:auto;overflow-y:hidden;padding:2px 0}   /* long equations scroll in-card, not the page */
.body img{max-width:100%;height:auto}
.body table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.9rem;display:block;overflow-x:auto}
.body th,.body td{border:1px solid var(--border);padding:6px 10px;text-align:left}
.body blockquote{margin:12px 0;padding:8px 14px;border-left:3px solid var(--accent);color:var(--muted)}

footer{color:var(--muted);font-size:.85rem;padding:40px 0 60px;margin-top:40px;border-top:1px solid var(--border)}
@media (max-width:560px){ header.hero{padding:52px 0 24px} .block{padding:40px 0 8px} }

/* full-screen split hero: words + auto-advancing progress on the left, graph on the right */
.hero2{width:100%;display:flex;gap:0;align-items:center;height:100vh}
.hero2-left{flex:0 0 44%;min-width:0;display:flex;flex-direction:column;justify-content:center;
  padding:80px max(40px,4vw) 40px clamp(24px,5vw,88px)}
.hero2-right{flex:1 1 56%;align-self:stretch;position:relative;overflow:hidden;background:#232323}
.hero2-right #kg{position:absolute;inset:0;width:100%;height:100%;cursor:grab}
.hero2-head{font-family:var(--serif);font-weight:500;font-size:clamp(1.9rem,5vw,3.7rem);
  line-height:1.05;letter-spacing:-.02em;margin:14px 0 18px;overflow-wrap:break-word}
.sc-type{border-right:.06em solid var(--gold);padding-right:.04em;color:var(--gold)}
.sc-kicker{font-family:var(--mono);font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);display:flex;align-items:center;gap:8px}
.sc-kicker::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--gold)}
.sc-blurb{font-size:1.1rem;line-height:1.6;max-width:42ch;color:var(--muted)}
.sc-tags{margin:16px 0 0;display:flex;gap:8px 14px;flex-wrap:wrap;font-family:var(--mono);
  font-size:.76rem;color:var(--muted)}
.hero2-links{margin:22px 0 0;display:flex;gap:12px;flex-wrap:wrap}
.hero2-links a{border:1px solid var(--border);background:var(--surface);color:var(--fg);
  padding:9px 16px;border-radius:10px;font-size:.9rem}
.hero2-links a:hover{border-color:var(--accent);text-decoration:none}
.sc-tabs{display:flex;gap:14px;margin:36px 0 0}
.sc-tab{flex:1 1 0;cursor:pointer;opacity:.55;transition:opacity .3s;background:none;border:none;
  color:var(--fg);text-align:left;padding:0;font:inherit}
.sc-tab.active{opacity:1}
.sc-tab .tl{font-size:.86rem;margin:0 0 8px;font-weight:500}
.sc-track{height:3px;background:var(--border);border-radius:2px;overflow:hidden}
.sc-track i{display:block;height:100%;width:0;background:var(--gold);border-radius:2px}
@media(max-width:860px){ .hero2{flex-direction:column;height:auto;align-items:stretch}
  .hero2-left{flex:none;width:100%;padding:78px 24px 24px} .hero2-right{flex:none;width:100%;height:60vh} }

/* floating tab navigator (top-centred) */
.floatnav{position:fixed;left:50%;top:11px;transform:translateX(-50%);z-index:60;display:flex;gap:4px;
  padding:5px;background:color-mix(in srgb,var(--surface) 90%,transparent);border:1px solid var(--border);
  border-radius:999px;backdrop-filter:blur(12px);box-shadow:0 8px 26px rgba(0,0,0,.16)}
.floatnav a{padding:7px 18px;border-radius:999px;font-size:.86rem;color:var(--muted);text-decoration:none;
  transition:background .2s,color .2s;white-space:nowrap}
.floatnav a:hover{color:var(--fg)}
.floatnav a.active{background:var(--fg);color:var(--bg)}
@media(max-width:560px){ .floatnav{top:60px} .floatnav a{padding:7px 13px;font-size:.8rem} }
</style>
</head>"""

HEADER = """  <div class="top"><div class="wrap">
    <span class="brand">Yuan-Hsuan Wen</span>
  </div></div>

  <section class="hero2" id="top">
    <div class="hero2-left">
      <div class="sc-kicker" id="sc-kicker"></div>
      <h1 class="hero2-head">I work on <span class="sc-type" id="sc-type"></span></h1>
      <p class="sc-blurb" id="sc-blurb"></p>
      <div class="sc-tags" id="sc-tags"></div>
      <div class="hero2-links">
        <a href="#writeups">Write-ups</a>
        <a href="https://leetcode.com/u/__USER__/" target="_blank" rel="noopener">LeetCode</a>
        <a href="https://github.com/__USER__" target="_blank" rel="noopener">GitHub</a>
      </div>
      <div class="sc-tabs" id="sc-tabs"></div>
    </div>
    <div class="hero2-right">
      <canvas id="kg"></canvas>
      <div class="kg-hint">click to fan out · drag</div>
      <aside class="kg-panel" id="kg-panel"></aside>
    </div>
  </section>"""

SHOWCASE = """
  <section class="showcase" id="focus">
    <div class="inner">
      <div class="sc-kicker" id="sc-kicker"></div>
      <h2 class="sc-head">I work on <span class="sc-type" id="sc-type"></span></h2>
      <p class="sc-blurb" id="sc-blurb"></p>
      <div class="sc-tags" id="sc-tags"></div>
      <a class="sc-cta" id="sc-cta" href="#graph">Explore ▸</a>
      <div class="sc-tabs" id="sc-tabs"></div>
    </div>
  </section>"""

GRAPH_SECTION = """
  <section class="block" id="graph">
    <h2>Knowledge graph</h2>
    <p class="lede">Every topic and write-up I've made, linked together. Bigger topics = more
      content. Click any node to fan out its neighbours and list the related write-ups; click empty
      space to relax. Drag nodes to rearrange.</p>
    <div class="kg-shell">
      <canvas id="kg"></canvas>
      <div class="kg-legend">__LEGEND__</div>
      <div class="kg-hint">click to fan out · drag to move</div>
      <aside class="kg-panel" id="kg-panel"></aside>
    </div>
  </section>"""

CARDS_SECTION = """
  <section class="block" id="writeups">
    <h2>Deep-dive write-ups</h2>
    <p class="lede">The problems and concepts I wrote up in full — the reasoning, not just the code.
      <b>__NLC__</b> LeetCode · <b>__NAI__</b> AI notes.</p>
    <div class="controls">
      <select id="f-domain"><option value="">All domains</option>
        <option value="leetcode">LeetCode</option><option value="ai">AI Knowledge</option></select>
      <select id="f-diff"><option value="">All difficulty</option>
        <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></select>
      <select id="f-tag"><option value="">All topics</option></select>
      <input id="f-search" type="search" placeholder="search…" style="flex:0 1 160px">
      <span class="count" id="c-count"></span>
    </div>
    <div id="grid"></div>
  </section>"""

FOOTER = """
  <footer>Built from markdown by <code>site/build.py</code> — static, no backend, no tracking.
    Only <code>visibility:public</code> content is shown.</footer>
  </div>

  <nav class="floatnav" id="floatnav">
    <a href="#top" data-sec="top">Graph</a>
    <a href="#coverage" data-sec="coverage">LeetCode</a>
    <a href="#writeups" data-sec="writeups">Write-ups</a>
  </nav>"""

# ---- client logic (plain JS, no interpolation) ------------------------------
SCRIPT = r"""<script>
const $ = id => document.getElementById(id);

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

/* ---- hero left column: typed word + auto-advancing topic with progress ---- */
(function(){
  const tabsEl=$('sc-tabs'); if(!tabsEl) return;
  const ITEMS=[
    {kicker:'Algorithms',
     words:['clean algorithms','the right data structure','O(1) insight'],
     blurb:'466 LeetCode problems solved, 27 written up in full — the reasoning and trade-offs, not just the code.',
     tags:['two-pointers','dynamic-programming','graphs','binary-search']},
    {kicker:'AI / NLP',
     words:['NLP from scratch','word2vec by hand','attention'],
     blurb:'Working through Stanford CS224n by hand — embeddings, seq2seq, Transformers, minBERT — in PyTorch.',
     tags:['pytorch','transformers','embeddings','backprop']},
    {kicker:'Systems',
     words:['learning in public','static tooling','clean pipelines'],
     blurb:'A two-repo learning-in-public system with a dependency-free static-site generator and a Notion pipeline.',
     tags:['python','static-site','automation']},
  ];
  const kicker=$('sc-kicker'),typeEl=$('sc-type'),blurb=$('sc-blurb'),tagsEl=$('sc-tags');
  tabsEl.innerHTML=ITEMS.map((it,i)=>'<button class="sc-tab" data-i="'+i+'"><div class="tl">'
    +it.kicker+'</div><div class="sc-track"><i></i></div></button>').join('');
  const tabs=[].slice.call(tabsEl.querySelectorAll('.sc-tab'));
  const bars=[].slice.call(tabsEl.querySelectorAll('.sc-track i'));
  let idx=0,paused=false,prog=0,last=0;const DUR=6500;
  function render(i){const it=ITEMS[i];
    kicker.textContent=it.kicker; blurb.textContent=it.blurb;
    tagsEl.innerHTML=it.tags.map(t=>'<span>#'+t+'</span>').join('');
    tabs.forEach((t,j)=>t.classList.toggle('active',j===i)); startType(it.words);}
  function go(i){idx=(i+ITEMS.length)%ITEMS.length; prog=0; bars.forEach(b=>b.style.width='0'); render(idx);}
  tabs.forEach(t=>{t.onclick=()=>go(+t.dataset.i);
    t.onmouseenter=()=>paused=true; t.onmouseleave=()=>paused=false;});
  function tick(ts){ if(!last)last=ts; const dt=ts-last; last=ts;
    if(!paused){ prog+=dt; bars[idx].style.width=Math.min(prog/DUR*100,100)+'%';
      if(prog>=DUR) go(idx+1); }
    requestAnimationFrame(tick); }
  let tTimer=null,words=[],wi=0,ci=0,del=false;
  function startType(w){words=w;wi=0;ci=0;del=false;clearTimeout(tTimer);typeLoop();}
  function typeLoop(){const word=words[wi%words.length];
    if(!del){ci++;typeEl.textContent=word.slice(0,ci);
      if(ci>=word.length){del=true;tTimer=setTimeout(typeLoop,1500);return;}}
    else{ci--;typeEl.textContent=word.slice(0,ci); if(ci<=0){del=false;wi++;}}
    tTimer=setTimeout(typeLoop,del?40:75);}
  go(0); requestAnimationFrame(tick);
})();


/* ---- deep-dive cards ---- */
(function(){
  const grid=$('grid'); if(!grid) return;
  const tagSel=$('f-tag');
  TAGS.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;tagSel.appendChild(o);});
  const diffPill=d=>d?'<span class="pill diff-'+d+'">'+d+'</span>':'';
  const domLabel=d=>d==='ai'?'AI':'LeetCode';
  function cardHTML(c,i){
    return '<article class="card" id="card-'+c.id+'">'
      +'<div class="card-top"><h3>'+c.title+'</h3>'
      +'<span class="pill domain'+(c.domain==='ai'?' ai':'')+'">'+domLabel(c.domain)+'</span>'
      +diffPill(c.difficulty)+'<span class="pill">mastery '+c.mastery+'/5</span></div>'
      +'<div class="tags">'+c.tags.map(t=>'<span>#'+t+'</span>').join('')+'</div>'
      +'<button class="reveal-btn" data-i="'+i+'">Reveal write-up</button>'
      +'<div class="body" id="body-'+c.id+'">'+c.body_html+'</div></article>';
  }
  function renderMath(){ if(window.renderMathInElement) renderMathInElement(grid,{delimiters:[
    {left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false}); }
  window.addEventListener('load',renderMath);
  function draw(list){
    grid.innerHTML=list.map(cardHTML).join('')||'<p style="color:var(--muted)">No cards match.</p>';
    $('c-count').textContent=list.length+' / '+CARDS.length;
    grid.querySelectorAll('.reveal-btn').forEach(b=>b.onclick=()=>{
      const body=grid.querySelectorAll('.card')[b.dataset.i].querySelector('.body');
      const open=body.classList.toggle('open'); b.textContent=open?'Hide write-up':'Reveal write-up';
    });
    renderMath();
  }
  function apply(){
    const d=$('f-domain').value,diff=$('f-diff').value,tag=$('f-tag').value,q=$('f-search').value.toLowerCase();
    draw(CARDS.filter(c=>(!d||c.domain===d)&&(!diff||c.difficulty===diff)&&(!tag||c.tags.includes(tag))
      &&(!q||(c.title+' '+c.tags.join(' ')).toLowerCase().includes(q))));
  }
  ['f-domain','f-diff','f-tag','f-search'].forEach(id=>$(id).addEventListener('input',apply));
  draw(CARDS);
  window.expandCard=function(id){
    const el=$('card-'+id); if(!el) return;
    const body=el.querySelector('.body'), btn=el.querySelector('.reveal-btn');
    if(body&&!body.classList.contains('open')){body.classList.add('open'); if(btn)btn.textContent='Hide write-up';}
    el.scrollIntoView({behavior:'smooth',block:'center'});
    el.classList.add('flash'); setTimeout(()=>el.classList.remove('flash'),1200);
  };
  window.addEventListener('load',()=>{ if(location.hash.indexOf('#card-')===0) window.expandCard(location.hash.slice(6)); });
})();

/* ---- solved-table filter ---- */
(function(){
  const q=$('lc-search'),d=$('lc-diff'),cnt=$('lc-count'); if(!q) return;
  const rows=[].slice.call(document.querySelectorAll('#lc-table tbody tr'));
  function apply(){ const s=(q.value||'').toLowerCase(),df=d.value; let n=0;
    rows.forEach(r=>{const ok=(!df||r.dataset.d===df)&&(!s||r.dataset.t.indexOf(s)>=0);
      r.style.display=ok?'':'none'; if(ok)n++;}); cnt.textContent=n+' / '+rows.length; }
  q.addEventListener('input',apply); d.addEventListener('change',apply); apply();
})();

/* ---- knowledge graph (all-visible; click a node to fan out its neighbours) ---- */
(function(){
  const cv=$('kg'); if(!cv||typeof GRAPH==='undefined'||!GRAPH.nodes) return;
  const ctx=cv.getContext('2d'), panel=$('kg-panel');
  const MONO='#ededed';                // single monochrome node colour on black
  const colr=ci=>MONO;
  function css(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}
  const N=GRAPH.nodes, E=GRAPH.edges;
  N.forEach((n,i)=>n._i=i);
  const adj=N.map(()=>[]); E.forEach(e=>{adj[e[0]].push(e[1]); adj[e[1]].push(e[0]);});
  const edgeObjs=E.map(e=>[N[e[0]],N[e[1]]]);
  let W=0,H=0,DPR=Math.min(window.devicePixelRatio||1,2),alpha=1,hover=null,sel=null,drag=null,down=null;
  function resize(){ const r=cv.getBoundingClientRect(); W=r.width; H=r.height;
    cv.width=W*DPR; cv.height=H*DPR; ctx.setTransform(DPR,0,0,DPR,0,0); }
  new ResizeObserver(resize).observe(cv); resize();
  N.forEach((n,i)=>{ const a=i*2.399, R=Math.min(W,H)*(0.12+0.28*Math.sqrt((i%23)/23));
    n.x=W/2+Math.cos(a)*R + (n.ci? -120:120); n.y=H/2+Math.sin(a)*R; n.vx=0; n.vy=0; });
  const isNbr=n=>sel&&(n===sel||adj[sel._i].indexOf(n._i)>=0);

  function step(){
    const cx=W/2,cy=H/2;
    for(const n of N){ n.vx+=(cx-n.x)*0.004; n.vy+=(cy-n.y)*0.004; }
    for(let i=0;i<N.length;i++)for(let j=i+1;j<N.length;j++){
      const a=N[i],b=N[j]; let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||.01,d=Math.sqrt(d2);
      let f=Math.min((a.r*b.r*11)/d2,40); a.vx+=dx/d*f; a.vy+=dy/d*f; b.vx-=dx/d*f; b.vy-=dy/d*f; }
    for(const e of edgeObjs){ const a=e[0],b=e[1];
      const spread=sel&&(a===sel||b===sel)?95:0;               // fan neighbours of selected out
      let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||.01;
      let k=(d-(a.r+b.r+40+spread))*0.02; a.vx+=dx/d*k; a.vy+=dy/d*k; b.vx-=dx/d*k; b.vy-=dy/d*k; }
    for(const n of N){ if(n===drag)continue;
      n.vx=Math.max(-8,Math.min(8,n.vx*0.9)); n.vy=Math.max(-8,Math.min(8,n.vy*0.9));
      n.x+=n.vx*alpha; n.y+=n.vy*alpha;
      n.x=Math.max(n.r+4,Math.min(W-n.r-4,n.x)); n.y=Math.max(n.r+4,Math.min(H-n.r-4,n.y)); }
    if(alpha>0.25) alpha*=0.992;                               // settle, keep a little life
  }
  function draw(){
    ctx.clearRect(0,0,W,H);
    for(const e of edgeObjs){ const a=e[0],b=e[1], note=a.type==='note'?a:b, hot=sel&&(a===sel||b===sel);
      ctx.strokeStyle=colr(note.ci); ctx.globalAlpha=hot?0.85:(sel?0.06:0.18); ctx.lineWidth=hot?1.6:0.9;
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); }
    ctx.globalAlpha=1;
    for(const n of N){
      const c=colr(n.ci), dim=sel&&!isNbr(n);
      ctx.globalAlpha=dim?0.28:1;
      ctx.beginPath(); ctx.arc(n.x,n.y,n.r,0,6.283);
      if(n.type==='tag'){ ctx.fillStyle=c; ctx.fill(); }          // topics: solid
      else { ctx.fillStyle='#232323'; ctx.fill(); ctx.lineWidth=2.4; ctx.strokeStyle=c; ctx.stroke(); }  // notes: hollow ring on the charcoal graph
      ctx.globalAlpha=1;
    }
    for(const n of N){                                          // labels on top
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
  function loop(){ step(); draw(); requestAnimationFrame(loop); } loop();

  function nodeAt(x,y){ for(let i=N.length-1;i>=0;i--){const n=N[i];
    if((x-n.x)**2+(y-n.y)**2<=(n.r+3)**2) return n;} return null; }
  function selectNode(n){
    sel=n; alpha=Math.max(alpha,0.9);
    const nbrs = adj[n._i].map(i=>N[i]);
    let h='<button class="pclose" title="close">✕</button>';
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
  window.kgRecolor=function(){ document.querySelectorAll('.kg-legend i[data-ci]').forEach(el=>{
    el.style.background=colr(+el.dataset.ci); }); };
  window.kgRecolor();
})();
</script>"""


def main():
    cards = collect()
    graph = build_graph(cards)
    OUT.write_text(page(cards, graph, load_solved()), encoding="utf-8")
    print(f"Wrote {OUT}  ({len(cards)} cards, {len(graph['nodes'])} nodes, {len(graph['edges'])} edges)")


if __name__ == "__main__":
    main()
