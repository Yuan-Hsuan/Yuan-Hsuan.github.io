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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ---- config -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent          # repo root
CONTENT_DIRS = ["leetcode", "knowledge"]               # public domains shown on the site
GITHUB_USER = "Yuan-Hsuan"
LINKEDIN_URL = "https://www.linkedin.com/in/yuan-hsuan-wen/"
OUT = ROOT / "index.html"

WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")             # [[note]] links, Obsidian-style

# ---- curated picks (section 01 — DESIGN.md §6) --------------------------------
# id must exist in the collected cards; missing ids are skipped gracefully.
CURATED = [
    dict(id="ai-dev-workflow", meta="AI · Working method",
         why="My playbook for building with AI — synthesized from Anthropic, Harper Reed, "
             "and Osmani, down to the judgment call of when NOT to hand it to the model."),
    dict(id="lc-largest-rectangle-in-histogram", meta="LeetCode 84 · Hard",
         why="The monotonic-stack invariant, built up from the O(n²) version — how a "
             "trick becomes a reusable pattern."),
    dict(id="static-site-architecture", meta="Software engineering · This site",
         why="Why this site is one Python file with zero dependencies — build time vs "
             "runtime, and when not to reach for a framework."),
]

# ---- experience (section 02 — web-native résumé, DESIGN.md §6) ----------------
# Source of truth: mind/resume/resume.md (private). Public version: no contact info,
# bullets condensed to action + constraint + bold result.
EXPERIENCE = [
    dict(when="2026 — now", org="Currently",
         role="Independent study — AI infrastructure",
         bullets=[
            'Working through <b>Stanford CS224n</b> by hand — embeddings → Transformers, '
            '<b>minBERT in progress</b>. This site’s AI notes are the by-product.',
            'Digging into <b>agentic workflows and evals</b> — LangGraph, DSPy, automated '
            'evaluation — the next step after the NVIDIA engine’s adoption lesson.']),
    dict(when="May — Nov 2025 · Taipei", org="NVIDIA",
         role="Software Engineering Intern — AI diagnostic agent",
         bullets=[
            'Built an AI diagnostic agent for system-level bug analysis — a Python '
            '<b>AST engine</b> extracts control-flow features so the LLM reads structure, '
            'not raw logs. <span class="xp-hook">“I couldn’t scale the hardware, '
            'so I shrank the problem.”</span>',
            '<b>RAG pipeline</b> (LangChain + Milvus) and a Dockerized REST backend wired '
            'into the internal bug tracker, with a dashboard that visualizes the results.',
            '<b>Matched engineers’ own triage calls 82% of the time</b>; adopted as '
            'a permanent asset.']),
    dict(when="Jun — Aug 2024 · Hsinchu", org="Silicon Motion",
         role="Verification Engineer Intern",
         bullets=[
            'Cut manual test setup by <b>43%</b> with a full-stack device-management '
            'platform (React + Node.js) — remote chip power-cycling from the browser.']),
    dict(when="Jun 2022 — Dec 2023 · Hsinchu", org="Broadcom",
         role="Software Engineer",
         bullets=[
            'Led an automation suite that modulates chip voltage from real-time thermal '
            'and network data — <b>27% better power efficiency</b>.',
            'Automated IC programming (Python + Bash, Linux) with hardened firmware '
            'deployment — <b>45% less manual programming time</b>.']),
    dict(when="Mar 2021 — Jun 2022 · Hsinchu", org="Broadcom",
         role="Software Engineer Intern (Co-op)",
         bullets=[
            'Built a Python GUI running power-delivery-network (PDN) analysis from a '
            'loaded BOM — <b>halved per-run setup time</b> across ~4–5 boards a week; '
            'converted to full-time.']),
]

# Education lives as one quiet line in the pinned intro column, not a timeline entry.
EDUCATION_LINE = "M.S. Computer Science — USC (2024–25) · B.S. ECE, minor CS — NYCU"

# A verifiable credential, right under education (name matches the Skilljar verify page verbatim).
CERT = dict(name="Anthropic · AI Fluency: Framework & Foundations",
            url="https://verify.skilljar.com/c/ufyin5wu2gk3")

# ---- external AI notes (single source of truth: the CS224n study repo) -------
# The notes live in the sibling repo; we read them at build time so the site is
# never a stale copy — edit the note there, re-run build.py, done. (Images are
# copied into ROOT/imgs so GitHub Pages can serve them.) The notes carry the
# same SCHEMA.md frontmatter as everything else — the visibility safety belt
# and the CLI's mastery write-back apply to them like any other card.
CS224N_NOTES = ROOT.parent / "Standford-cs224n-nlp" / "notes" / "concepts"
CS224N_SOURCE = "https://web.stanford.edu/class/cs224n/"


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
    s = re.sub(r"\*(\S(?:[^*\n]*\S)?)\*", r"<em>\1</em>", s)           # *italic* (bold already gone)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",                            # ![alt](img)
               r'<img src="\2" alt="\1" style="max-width:100%;border-radius:8px;margin:10px 0">', s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)  # [t](url)
    return s


def render_body(md: str, base: str = "") -> str:
    """Markdown → HTML, protecting LaTeX math ($…$ / $$…$$) from the markdown pass so KaTeX
    (auto-render, loaded in <head>) can typeset it in the browser.

    `base` = the note's folder relative to ROOT (e.g. "leetcode"). Notes reference images by a
    path relative to their own .md (so IDE markdown preview finds them); we prepend `base` here so
    the same src resolves from the site root too. Absolute/http srcs are left untouched."""
    math = []
    def stash(m):
        math.append(m.group(0)); return f"@@MATH{len(math)-1}@@"
    md = re.sub(r"\$\$.*?\$\$", stash, md, flags=re.S)                 # display math
    md = re.sub(r"\$[^$\n]+?\$", stash, md)                            # inline math
    out = md_to_html(md)
    for i, m in enumerate(math):
        out = out.replace(f"@@MATH{i}@@", m)
    if base:                                                           # note-relative img src -> site-root
        out = re.sub(r'<img src="([^"]*)"',
                     lambda m: m.group(0) if m.group(1).startswith(("http://", "https://", "/"))
                     else f'<img src="{base}/{m.group(1)}"', out)
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
        BLOCK = r"(\s*[-*]\s+|\s*\d+\.\s+|#{1,6}\s|>|\||```)"        # a line that starts a new block
        if re.match(r"\s*[-*]\s+", line):                            # ul (folds lazy continuations)
            buf = []
            while i < n and re.match(r"\s*[-*]\s+", lines[i]):
                item = re.sub(r"\s*[-*]\s+", "", lines[i], count=1); i += 1
                while i < n and lines[i].strip() and not re.match(BLOCK, lines[i]):
                    item += " " + lines[i].strip(); i += 1
                buf.append(item)
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ul>")
            continue
        if re.match(r"\s*\d+\.\s+", line):                           # ol (folds lazy continuations)
            buf = []
            while i < n and re.match(r"\s*\d+\.\s+", lines[i]):
                item = re.sub(r"\s*\d+\.\s+", "", lines[i], count=1); i += 1
                while i < n and lines[i].strip() and not re.match(BLOCK, lines[i]):
                    item += " " + lines[i].strip(); i += 1
                buf.append(item)
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
                "source": str(meta.get("source", "") or ""),
                "body_html": render_body(body, str(path.parent.relative_to(ROOT))),
            })
    cards.extend(external_ai_cards())
    resolve_wikilinks(cards)
    return cards


def resolve_wikilinks(cards):
    """Turn [[slug]] cross-refs in note bodies into clickable links that open the
    target card in the reader. Unknown targets degrade to plain prettified text so a
    dangling link never shows raw [[ ]]. Runs after all cards exist so every id is known."""
    ids = {c["id"] for c in cards}

    def pretty(slug):
        return re.sub(r"^(ai|os|net|lc|sd)-", "", slug).replace("-", " ")

    def repl(m):
        slug = m.group(1).strip()
        if slug in ids:
            return (f'<a class="wl" href="#card-{esc(slug)}" '
                    f'onclick="expandCard(\'{esc(slug)}\');return false">{esc(pretty(slug))}</a>')
        return esc(pretty(slug))

    for c in cards:
        if "[[" in c["body_html"]:
            c["body_html"] = re.sub(r"\[\[([^\]]+)\]\]", repl, c["body_html"])


def strip_note_front(text: str):
    """Body = everything from the first real '## ' section onward, dropping the H1
    title, the '> …' source header, and the '## Contents' block. Robust to whether
    the note keeps '---' separators — the notes are hand-edited freely, so we can't
    rely on their punctuation (that once leaked Source/Contents into the site)."""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and not ln[3:].lstrip().startswith(("Contents", "目錄")):
            return "\n".join(lines[i:]).strip()
    parts = text.split("\n---\n", 2)                             # fallback: old --- split
    if len(parts) >= 3:
        return parts[2].strip()
    return re.sub(r"^#.*\n", "", text, count=1).strip()


def external_ai_cards():
    """Read the CS224n notes from the sibling repo at build time (single source of
    truth) and turn each into an AI card. Metadata comes from each note's own
    SCHEMA frontmatter, so the visibility safety belt applies here too and the
    CLI's mastery write-back is what the site renders. Returns [] if the repo
    isn't next door."""
    if not CS224N_NOTES.exists():
        return []
    (ROOT / "imgs").mkdir(exist_ok=True)                          # copy note images for Pages
    for img in (CS224N_NOTES / "imgs").glob("*.png"):
        shutil.copy(img, ROOT / "imgs" / img.name)
    cards = []
    for path in sorted(CS224N_NOTES.glob("*.md")):
        if path.name.lower() in ("readme.md", "_template.md"):
            continue
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("visibility") != "public":                    # SAFETY BELT
            continue
        domain = meta.get("domain", "ai")
        title = meta.get("title", path.stem)
        tags = meta.get("tags", []) if isinstance(meta.get("tags"), list) else []
        body = strip_note_front(body)                            # drop title + header + Contents
        body = WIKILINK.sub(r"\1", body)                          # strip [[ ]] the site can't resolve
        cards.append({
            "id": meta.get("id", path.stem), "domain": domain, "title": title,
            "label": short_label(domain, title), "tags": tags,
            "difficulty": meta.get("difficulty", ""),
            "mastery": int(meta.get("mastery", 0) or 0),
            "words": len(re.sub(r"```.*?```", " ", body, flags=re.S).split()),
            "related": [], "source": meta.get("source", CS224N_SOURCE),
            "body_html": render_body(body),
        })
    return cards


def build_graph(cards):
    """Bipartite graph for the hero knowledge map: every note and every topic is a node;
    notes link to their topics (+ any [[wikilinks]]). `dom` buckets each node into one of
    four domains — the JS packs each domain into its own cluster."""
    DOM_I = {"leetcode": 0, "ai": 1, "systems": 2, "software-engineering": 3}
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
                      "full": c["title"], "dom": DOM_I.get(c["domain"], 0), "cardId": c["id"],
                      "difficulty": c["difficulty"],
                      "r": round(5 + 5 * (c["words"] / maxw) ** 0.5, 1)})
    maxd = max((len(v) for v in tag_notes.values()), default=1) or 1
    for t in sorted(tag_notes):
        dom = tag_dom[t].most_common(1)[0][0]
        index["tag:" + t] = len(nodes)
        nodes.append({"id": "tag:" + t, "type": "tag", "label": t, "full": t,
                      "dom": DOM_I.get(dom, 0), "count": len(tag_notes[t]), "items": tag_notes[t],
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

    # Node order no longer drives position: the JS groups by `dom` and packs each cluster
    # itself, so the old md5 shuffle (which broke the fibonacci sphere's latitude banding)
    # is gone with the sphere.
    return {"nodes": nodes, "edges": edges}


def load_solved():
    """The hero's LeetCode total. Auto-fetched from LeetCode's PUBLIC GraphQL (no cookie),
    cached in site/solved.json, offline-safe — same shape as load_contrib(). The per-problem
    `problems` list (populated by build_solved.py from a cookie'd dump) isn't rendered, so we
    only refresh `counts`/`username` here and keep whatever list is already cached."""
    cache = ROOT / "site" / "solved.json"
    data = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {
        "username": GITHUB_USER, "counts": {}, "problems": []}
    try:
        body = json.dumps({
            "query": "query($u:String!){matchedUser(username:$u){"
                     "submitStatsGlobal{acSubmissionNum{difficulty count}}}}",
            "variables": {"u": GITHUB_USER}}).encode("utf-8")
        req = urllib.request.Request(
            "https://leetcode.com/graphql", data=body,
            headers={"Content-Type": "application/json", "Referer": "https://leetcode.com",
                     "User-Agent": "Mozilla/5.0 (build.py)"})
        r = json.loads(urllib.request.urlopen(req, timeout=12).read().decode("utf-8"))
        nums = r["data"]["matchedUser"]["submitStatsGlobal"]["acSubmissionNum"]
        by = {x["difficulty"].lower(): x["count"] for x in nums}   # all/easy/medium/hard
        data["counts"] = {"total": by.get("all", 0), "easy": by.get("easy", 0),
                          "medium": by.get("medium", 0), "hard": by.get("hard", 0)}
        cache.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception as exc:                                        # offline / blocked → cache
        print(f"  (leetcode fetch failed: {exc}; using cached solved.json)")
    return data if data.get("counts") else None


# ---- GitHub contribution calendar (section 03) --------------------------------
# Fetched at build time from GitHub's public contributions endpoint (no token),
# cached in site/contrib.json so offline builds still work. Section is omitted
# entirely if neither the network nor the cache yields data.
CONTRIB_WEEKS = 6          # June–July window while the public streak is young


def load_activity():
    """Per-day detail (repo → commits/events) from the public Events API, cached.
    Only PUBLIC repos ever appear here, so mind/ stays invisible by construction."""
    cache = ROOT / "site" / "activity.json"
    events = None
    try:
        req = urllib.request.Request(
            f"https://api.github.com/users/{GITHUB_USER}/events/public?per_page=100",
            headers={"User-Agent": "build.py", "Accept": "application/vnd.github+json"})
        events = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
        cache.write_text(json.dumps(events), encoding="utf-8")
    except Exception as exc:
        print(f"  (activity fetch failed: {exc}; trying cache)")
        if cache.exists():
            events = json.loads(cache.read_text(encoding="utf-8"))
    if not events:
        return {}
    agg = {}
    for ev in events:
        ts = ev.get("created_at", "")
        repo = ev.get("repo", {}).get("name", "").split("/")[-1]
        if not ts or not repo:
            continue
        # created_at is UTC; the contribution calendar counts by LOCAL day —
        # convert, or evening pushes drift onto the next day's (empty) cell.
        d = (datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
             .replace(tzinfo=timezone.utc).astimezone().date().isoformat())
        r = agg.setdefault(d, {}).setdefault(repo, [0, 0])   # [pushes, other events]
        if ev.get("type") == "PushEvent":
            r[0] += 1        # unauthenticated payloads omit the commit list, so count pushes
        else:
            r[1] += 1
    return agg


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
            i = re.search(r'id="([^"]+)"', td)
            if d and l:
                found[d.group(1)] = {"level": int(l.group(1)),
                                     "id": i.group(1) if i else "", "count": 0}
        tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', page_html))
        for v in found.values():                      # "3 contributions on July 3rd."
            m = re.match(r"(\d+)", tips.get(v["id"], "").strip())
            v["count"] = int(m.group(1)) if m else 0
        if found:
            days = [{"date": k, "level": v["level"], "count": v["count"]}
                    for k, v in sorted(found.items())]
            cache.write_text(json.dumps({"days": days}), encoding="utf-8")
    except Exception as exc:                                     # offline → cache
        print(f"  (contributions fetch failed: {exc}; trying cache)")
    if days is None and cache.exists():
        days = json.loads(cache.read_text(encoding="utf-8")).get("days")
    if not days:
        return None
    days = days[-(CONTRIB_WEEKS * 7):]                  # anchor the window to TODAY
    off = (date.fromisoformat(days[0]["date"]).weekday() + 1) % 7   # align col 1 to Sunday
    days = days[(7 - off) % 7:]                         # trim the front only — never the tail
    last = date.fromisoformat(days[-1]["date"])
    future = 0
    while future < 14 or len(days) % 7:                     # two weeks ahead, whole columns
        future += 1
        days.append({"date": (last + timedelta(days=future)).isoformat(),
                     "level": -1, "count": 0})
    act = load_activity()
    out = []
    for d in days:
        e = {"d": d["date"], "l": d["level"], "c": d.get("count", 0)}
        if d["date"] in act:
            e["a"] = [[repo, v[0], v[1]] for repo, v in act[d["date"]].items()]
        out.append(e)
    months, seen = [], None
    for i in range(0, len(days), 7):
        m = date.fromisoformat(days[i]["date"]).strftime("%b")
        months.append(m if m != seen else "")
        seen = m
    return {"days": out, "months": months}


# ---- HTML section builders ----------------------------------------------------
def esc(s):
    return html.escape(str(s), quote=True)


def hero_html(cards, solved):
    n_cs = sum(1 for c in cards if c["domain"] == "ai"
               and c.get("source") == CS224N_SOURCE)
    n_claude = sum(1 for c in cards if c["domain"] == "ai"
                   and c.get("source") != CS224N_SOURCE)
    n_sys = sum(1 for c in cards if c["domain"] == "systems")
    n_lc = sum(1 for c in cards if c["domain"] == "leetcode")
    n_se = sum(1 for c in cards if c["domain"] == "software-engineering")
    total = (solved or {}).get("counts", {}).get("total", 0)
    user = (solved or {}).get("username", GITHUB_USER)
    return f"""
  <header class="hero2" id="top">
    <div class="hero2-left">
      <p class="kicker rv" style="--d:0s"><span>Yuan-Hsuan Wen</span><span aria-hidden="true">·</span><span>Learning in public</span><span aria-hidden="true">·</span><span>Updated __BUILD_MONTH__<span class="ping" aria-hidden="true"></span></span></p>
      <h1 class="rv" style="--d:.15s">I work on<br><span class="h1-cyc" id="typed">clean algorithms</span></h1>
      <p class="hero-sub rv" style="--d:.3s">Systems engineer, moving into AI infrastructure.
      The practice, logged honestly — mistakes included.</p>
      <div class="stats rv" style="--d:.45s">
        <div class="sgroup">
          <div class="sl">AI</div>
          <div class="srow">
            <div class="stat"><div class="n odo" data-n="{n_cs}">0</div><div class="l">cs224n notes</div></div>
            <div class="stat"><div class="n odo" data-n="{n_claude}">0</div><div class="l">claude courses</div></div>
          </div>
        </div>
        <div class="vdiv" aria-hidden="true"></div>
        <div class="sgroup">
          <div class="sl">Systems / SWE</div>
          <div class="srow">
            <div class="stat"><div class="n odo" data-n="{n_sys}">0</div><div class="l">os · network</div></div>
            <div class="stat"><div class="n odo" data-n="{n_se}">0</div><div class="l">engineering</div></div>
          </div>
        </div>
        <div class="vdiv" aria-hidden="true"></div>
        <div class="sgroup">
          <div class="sl">LeetCode · <a href="https://leetcode.com/u/{user}/" target="_blank" rel="noopener">profile ↗</a></div>
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
    <div class="hero2-right hud">
      <canvas id="kg" aria-label="Knowledge graph of write-ups and topics"></canvas>
      <div class="kg-hint" id="kg-hud">click a topic</div>
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
            f'<a class="cardk rv" style="--d:{i*0.1:.1f}s" href="#card-{esc(c["id"])}" '
            f'onclick="expandCard(\'{esc(c["id"])}\');return false;">'
            f'<div class="meta">{esc(pick["meta"])}</div>'
            f'<h3>{esc(c["title"])}</h3>'
            f'<p class="why">{esc(pick["why"])}</p>'
            f'<div class="foot"><span>{esc(tags)}</span><span class="go">Read</span></div></a>')
    if not items:
        return ""
    return ('\n  <section class="band" id="start">\n    <div class="wrap wide start-grid">\n'
            '      <div class="cards3">' + "".join(items) + '</div>\n'
            '      <div class="sec-head rv">\n'
            '        <p class="kicker"><span class="idx">01</span><span class="dec">Start here</span></p>\n'
            '        <h2>Three write-ups that show how I think.</h2>\n'
            '        <p>Hand-picked. Ten minutes, three reads.</p>\n'
            '      </div>\n'
            '    </div>\n  </section>')


def experience_html():
    rows = []
    for i, e in enumerate(EXPERIENCE):
        lis = "".join(f"<li>{b}</li>" for b in e["bullets"])
        side = "L" if i % 2 == 0 else "R"
        rows.append(
            f'<div class="xp-item {side}" data-step="{i}">'
            f'<div class="xp-when">{esc(e["when"])}</div>'
            f'<h3>{esc(e["org"])}</h3>'
            f'<p class="xp-role">{esc(e["role"])}</p>'
            f'<ul>{lis}</ul></div>')
    return f"""
  <section class="band dark xp-pin" id="xp">
    <div class="xp-stage">
      <div class="wrap wide xp-grid">
        <div class="xp-left">
          <p class="kicker"><span class="idx">02</span><span class="dec">Experience</span></p>
          <h2>Systems engineer,<br>moving into AI infrastructure.</h2>
          <p class="pitch">“I want to build the
          engine that makes them fast and reliable.”</p>
          <div class="xp-cta">
            <a class="btn primary" href="{LINKEDIN_URL}" target="_blank" rel="noopener">Connect me on LinkedIn ↗</a>
          </div>
          <p class="xp-edu">{EDUCATION_LINE}</p>
          <p class="xp-cert">Certified · <a href="{CERT['url']}" target="_blank" rel="noopener">{esc(CERT['name'])} ↗</a></p>
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
        <p class="kicker"><span class="idx">03</span><span class="dec">Activity</span></p>
        <h2>Showing up, in public.</h2>
        <p>Every gold square is a commit to this log or its notes — pulled from GitHub at build time.</p>
        <p class="gh-note">Started logging publicly in spring 2026 — the streak is young on purpose.</p>
      </div>
      <div class="gh rv">
        <div class="gh-head">
          <a class="gh-title" href="https://github.com/{GITHUB_USER}" target="_blank" rel="noopener">github.com/{GITHUB_USER}</a>
          <span class="gh-title">click a day for details</span>
        </div>
        <div class="gh-flex">
          <div class="gh-cal">
            <div class="gh-months" id="ghmonths" aria-hidden="true"></div>
            <div class="gh-grid" id="ghgrid" role="img" aria-label="GitHub contribution calendar, last {CONTRIB_WEEKS} weeks"></div>
            <div class="gh-foot">
              <span class="gh-leg">Less
                <i style="background:var(--gh0)"></i><i style="background:var(--gh1)"></i><i style="background:var(--gh2)"></i><i style="background:var(--gh3)"></i><i style="background:var(--gh4)"></i>
              More</span>
            </div>
          </div>
          <div class="gh-act" id="ghact"><span class="dim">select a day —</span></div>
        </div>
      </div>
    </div>
  </section>"""


# ---- the system (section 04): a working mini-editor over REAL project files ----
# Every pane is read from the actual repo at build time — nothing is hand-typed,
# so the editor can never drift from the code it shows.
_PY_KW = re.compile(r"\b(def|return|for|in|if|elif|else|while|continue|break|import|"
                    r"from|class|with|as|not|and|or|lambda|yield|None|True|False)\b")

def _hl_py(s: str) -> str:
    s = html.escape(s, quote=False)
    if "#" in s:
        head, _, tail = s.partition("#")
        return _hl_py_code(head) + '<i class="c">#' + tail + "</i>"
    return _hl_py_code(s)

def _hl_py_code(s: str) -> str:
    s = re.sub(r'("[^"]*")', r'<i class="s">\1</i>', s)
    s = _PY_KW.sub(r'<i class="k">\1</i>', s)
    return s

def _hl_md(s: str) -> str:
    s = html.escape(s, quote=False)
    if s.strip() == "---":
        return f'<i class="c">{s}</i>'
    if s.startswith("#"):
        return f'<i class="k">{s}</i>'
    return re.sub(r"^(\s*)([\w-]+)(:)", r'\1<i class="f">\2</i>\3', s)

def _hl_html(s: str) -> str:
    s = html.escape(s, quote=False)
    return re.sub(r"(&lt;/?[a-zA-Z!][^&]*?&gt;)", r'<i class="k">\1</i>', s)

def _pane(key: str, lines: list, start: int, hl) -> str:
    out = []
    for j, raw in enumerate(lines):
        cur = '<span class="cursor" aria-hidden="true"></span>' if j == len(lines) - 1 else ""
        out.append(f'<span class="ln" style="--d:{min(0.05 + j*0.05, 0.85):.2f}s">'
                   f'<span class="no">{start + j}</span>{hl(raw.rstrip())}{cur}</span>')
    hidden = "" if key == "build" else " hidden"
    return f'<div class="code" data-pane="{key}"{hidden}><pre>{"".join(out)}</pre></div>'


def _file_lines(path: Path, start: int, count: int):
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[start - 1:start - 1 + count]


def system_html():
    panes, tabs = [], []

    def add(key, label, path_label, path=None, lines=None, start=1, hl=_hl_md, note=""):
        if path is not None:
            if not path.exists():
                return
            lines = _file_lines(path, start, 150)
        tabs.append((key, label, path_label, note))
        panes.append(_pane(key, lines, start, hl))

    add("note", "leetcode/15. 3Sum.md", "leetcode/15. 3Sum.md — a write-up's source",
        path=ROOT / "leetcode" / "15. 3Sum.md", hl=_hl_md)
    add("note2", "leetcode/84. Largest Rectangle….md",
        "leetcode/84. Largest Rectangle in Histogram.md — a hard write-up's source",
        path=ROOT / "leetcode" / "84. Largest Rectangle in Histogram.md", hl=_hl_md)
    add("ainote", "cs224n/…/05-backprop.md",
        "Standford-cs224n-nlp/notes/concepts/05-backprop-matrix-calculus.md — an AI note (sibling repo)",
        path=CS224N_NOTES / "05-backprop-matrix-calculus.md", hl=_hl_md)
    add("schema", "SCHEMA.md", "SCHEMA.md — the metadata contract both repos share",
        path=ROOT / "SCHEMA.md", hl=_hl_md)
    add("readme", "site/README.md", "site/README.md — how this generator works",
        path=ROOT / "site" / "README.md", hl=_hl_md)
    src = Path(__file__).read_text(encoding="utf-8").splitlines()
    belt = next((i for i, l in enumerate(src) if "SAFETY BELT" in l and "if meta" in l), None)
    if belt is not None:
        start = belt - 7
        add("build", "site/build.py ●", "site/build.py — this generator, reading itself",
            lines=src[:150], start=1, hl=_hl_py)
    add("out", "index.html", "index.html — the generated output GitHub Pages serves",
        lines=HEAD.splitlines()[:80], start=1, hl=_hl_html, note="← output")

    tree_rows = []
    for i, (k, lbl, pl, n) in enumerate(tabs):
        sel = " sel" if k == "build" else ""
        pre = "└" if i == len(tabs) - 1 else "├"
        extra = ' <i class="lock">' + esc(n) + "</i>" if n else ""
        tree_rows.append(
            f'<button class="titem{sel}" data-pane="{k}" data-name="{esc(pl)}" role="tab" '
            f'aria-selected="{"true" if sel else "false"}">{pre} {esc(lbl)}{extra}</button>')
    tree = "".join(tree_rows)

    default_name = next((pl for k, lbl, pl, n in tabs if k == "build"), tabs[0][2] if tabs else "")
    return f"""
  <section class="band" id="sys">
    <div class="wrap wide">
      <div class="sec-head rv">
        <p class="kicker"><span class="idx">04</span><span class="dec">The system</span></p>
        <h2>This site is itself a project.</h2>
        <p>One Python script, zero dependencies. Every file below is read live from the repo — click around.</p>
      </div>
      <div class="frame rv crop">
        <div class="win" id="win">
          <div class="win-bar">
            <div class="dots" aria-hidden="true"><i></i><i></i><i></i></div>
            <span class="fname" id="win-fname">{esc(default_name)}</span>
          </div>
          <div class="win-body">
            <div class="tree" role="tablist" aria-label="Project files">
              <div class="troot">Yuan-Hsuan.github.io/</div>
              {tree}
            </div>
            {"".join(panes)}
          </div>
        </div>
      </div>
      <p class="win-cap rv">Markdown in → one Python script (stdlib only) → static HTML out.
      No backend, cookieless analytics. Only <code>visibility: public</code> files ever render.</p>
    </div>
  </section>"""


def ai_notes_html(cards):
    ai = [c for c in cards if c["domain"] == "ai"]
    if not ai:
        return ""
    # theory track (cs224n) first, tool track (claude courses) after
    ai = ([c for c in ai if c.get("source") == CS224N_SOURCE]
          + [c for c in ai if c.get("source") != CS224N_SOURCE])
    rows = []
    for i, c in enumerate(ai):
        track = "cs224n" if c.get("source") == CS224N_SOURCE else "claude 101"
        rows.append(
            f'<a class="row rv" style="--d:{i*0.06:.2f}s" href="#card-{esc(c["id"])}" '
            f'onclick="expandCard(\'{esc(c["id"])}\');return false;">'
            f'<span class="i">{i+1:02d}</span><span class="t">{esc(c["title"])}</span>'
            f'<span class="d">{track}</span></a>')
    return ('\n  <section class="band" id="ai">\n    <div class="wrap wide split">\n'
            '      <div class="sec-head rv">\n'
            '        <p class="kicker"><span class="idx">05</span><span class="dec">AI notes</span></p>\n'
            '        <h2>Theory by hand, tools by habit.</h2>\n'
            '        <p>Stanford CS224n worked through on paper — the math before the PyTorch. '
            'And Anthropic’s Claude courses, because I build with AI every day, '
            'so I study how to drive it well.</p>\n'
            '      </div>\n      <div class="rows">' + "".join(rows) + '</div>\n'
            '    </div>\n  </section>')


DOMAIN_LABELS = {"leetcode": "LeetCode", "ai": "AI Knowledge",
                 "software-engineering": "Software Eng", "systems": "Systems"}


# ---- section 06: workflow flowchart (native, web-designed; DESIGN.md §11) ------
# A clear flow architecture (before-code row + the loop) drawn in HTML/CSS — click
# any phase to read its detail. Not the imported .svg (that stays in the note).
PHASES = [
    dict(key="explore", num="01", name="Explore", teaser="read first, write nothing",
         title="Read the code first",
         beats=["Trace deps, find prior art in the repo.",
                "AI explores; it writes nothing yet.",
                "Greenfield project → skip straight to Spec."]),
    dict(key="spec", num="02", name="Spec", teaser="AI interviews you", spec=True,
         title="AI interviews you → spec.md",
         beats=["One question at a time until the idea is sharp (20–30 min).",
                "Stop when a stranger could build it without asking you.",
                "The output is a filled spec."]),
    dict(key="plan", num="03", name="Plan", teaser="right-size the chunks",
         title="Right-size the chunks",
         beats=["Small enough to build + verify safely.",
                "Big enough to move the project forward.",
                "Output = an ordered checklist."]),
    dict(key="build", num="04", name="Build", teaser="one chunk only", loop=True,
         title="Build ONE chunk only",
         beats=["Never hand over the whole plan at once.",
                "Deterministic bits → script, not the model.",
                "Spend the model on what needs reasoning."]),
    dict(key="verify", num="05", name="Verify", teaser="machine + your eyes", loop=True,
         title="Machine check + your eyes",
         beats=["A concrete pass/fail: tests · lint · screenshot · numbers.",
                "Machine pass ≠ done — read the diff yourself.",
                "Fail → feed the error back, fix, re-verify."]),
    dict(key="commit", num="06", name="Commit", teaser="green = rollback anchor", loop=True,
         title="Commit the green chunk",
         beats=["Every green chunk is a rollback anchor.",
                "Then the next chunk — that's the loop.",
                "Todo empty → ship it."]),
]


WORKFLOW_SVG = ROOT / "knowledge" / "claude" / "ai-dev-workflow.svg"


def build_html():
    if not WORKFLOW_SVG.exists():
        return ""
    svg = WORKFLOW_SVG.read_text(encoding="utf-8")
    details, rail = [], []
    for i, ph in enumerate(PHASES):
        beats = "".join(f"<li>{esc(b)}</li>" for b in ph["beats"])
        extra = ""
        if ph.get("spec"):
            extra = ('<p class="wf-fields"><a href="#card-ai-spec-template" '
                     'onclick="expandCard(\'ai-spec-template\');return false">'
                     'The fields I fill: Problem statement · Goals · Scope · Design · '
                     'Tasks · Non-goals · Roles ↗</a></p>')
        details.append(
            f'<div class="wf-detail" data-phase="{ph["key"]}"{"" if i == 0 else " hidden"}>'
            f'<p class="wf-eyebrow">Phase {ph["num"]} · {esc(ph["name"])}</p>'
            f'<h3>{esc(ph["title"])}</h3><ul>{beats}</ul>{extra}</div>')
        rail.append(
            f'<button class="wf-tab" data-phase="{ph["key"]}" role="tab" '
            f'aria-selected="{"true" if i == 0 else "false"}" '
            f'aria-label="Phase {ph["num"]}, {esc(ph["name"])}">{ph["num"]}</button>')
    return f"""
  <section class="band" id="build" tabindex="-1">
    <div class="wrap wide">
      <div class="sec-head rv">
        <p class="kicker"><span class="idx">06</span><span class="dec">How I build</span></p>
        <h2>How I build software with AI.</h2>
        <p>My repeatable <a href="#card-ai-dev-workflow" onclick="expandCard('ai-dev-workflow');return false">method</a>
        as a flowchart — spec first, then a build → verify → commit <b>loop</b>, one chunk at a time.
        </p>
      </div>
      <div class="wf rv">
        <div class="wf-map crop">{svg}</div>
        <div class="wf-side">
          <div class="wf-details">{''.join(details)}</div>
          <div class="wf-controls">
            <button class="wf-btn" id="wf-prev" aria-label="Previous phase">←</button>
            <div class="wf-rail" role="tablist" aria-label="Workflow phases">{''.join(rail)}</div>
            <button class="wf-btn" id="wf-next" aria-label="Next phase">→</button>
            <span class="wf-chunk" id="wf-chunk" aria-live="polite" hidden>chunk 1</span>
          </div>
        </div>
      </div>
    </div>
  </section>"""


def log_html(cards, solved):
    dom_opts = "".join(
        f'<option value="{esc(d)}">{esc(DOMAIN_LABELS.get(d, d.title()))}</option>'
        for d in sorted({c["domain"] for c in cards}))
    return f"""
  <section class="band" id="log">
    <div class="wrap wide">
      <div class="sec-head rv">
        <p class="kicker"><span class="idx">07</span><span class="dec">Write-ups</span></p>
        <h2>Everything, written up.</h2>
        <p>All {len(cards)} articles — LeetCode patterns, CS224n notes, engineering
        deep-dives. Click a card to read.</p>
      </div>
      <div class="controls rv">
        <select id="f-domain" aria-label="Filter by domain"><option value="">All domains</option>
          {dom_opts}</select>
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

  <div class="progress" aria-hidden="true"><i id="prog"></i></div>
  <nav class="floatnav" id="floatnav" aria-label="Sections">
    <a class="fn-brand" href="#top">Yuan-Hsuan Wen</a>
    <a href="#start" data-sec="start">Start here</a>
    <a href="#xp" data-sec="xp">Résumé</a>
    <a href="#ai" data-sec="ai">AI notes</a>
    <a href="#build" data-sec="build">How I build</a>
    <a href="#log" data-sec="log">Write-ups</a>
    <a class="ext" href="https://github.com/{GITHUB_USER}" target="_blank" rel="noopener">GitHub ↗</a>
    <a class="ext" href="{LINKEDIN_URL}" target="_blank" rel="noopener">LinkedIn ↗</a>
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
           + system_html()
           + ai_notes_html(cards)
           + build_html()
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
<title>Yuan-Hsuan Wen — The reasoning, not just the code.</title>
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
<meta property="og:title" content="Yuan-Hsuan Wen — The reasoning, not just the code.">
<meta property="og:description" content="LeetCode write-ups, CS224n NLP notes, and system-design study — learning CS &amp; AI in public.">
<meta property="og:url" content="https://yuan-hsuan.github.io/">
<meta property="og:image" content="https://yuan-hsuan.github.io/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Yuan-Hsuan Wen — engineer &amp; writer learning in public: LeetCode, CS224n/NLP notes, system design.">
<!-- Twitter / X card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Yuan-Hsuan Wen — The reasoning, not just the code.">
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
  --gh0:#e6e0d2; --gh1:#e8c99a; --gh2:#d9a866; --gh3:#c0863c; --gh4:#8f5f26;
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
.wrap{max-width:1080px;margin:0 auto;padding:0 clamp(20px,4vw,56px)}
.wrap.wide{max-width:1680px}
code{font-family:var(--mono)}
h1,h2,h3{text-wrap:balance}

/* ---- full-bleed band rhythm ---- */
.band{padding-block:clamp(4rem,9vw,8.5rem);scroll-margin-top:56px}
.band + .band:not(.dark){border-top:1px solid var(--border)}
.band.dark{background:var(--panel);
  --fg:#f1eee7; --muted:#a8a49c; --border:#413e37;
  --surface:#2a2823; --surface2:#1d1c19; --accent:#e8dcc6;
  color:var(--fg)}

/* ---- motion system (DESIGN.md §7) ---- */
.rv{opacity:0;transform:translateY(10px);
  transition:opacity .38s var(--ease),transform .38s var(--ease);
  transition-delay:calc(var(--d,0s)*.6)}
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
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .rv{opacity:1;transform:none;transition:none}
  .cursor,.ping::after,.cue{animation:none}
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
  font-size:clamp(2.3rem,4.2vw,3.7rem);line-height:1.1;letter-spacing:-.01em;margin:0}
.hero2 h1 em{font-style:italic;font-weight:600;
  background:linear-gradient(transparent 70%,color-mix(in srgb,var(--gold) 42%,transparent) 70%)}
.hero-sub{color:var(--muted);max-width:34rem;margin:0;font-size:1.05rem}
.h1-cyc{color:var(--gold);border-right:.07em solid var(--gold);padding-right:.08em}
.stats{display:flex;gap:2.2rem;border-top:1px solid var(--border);padding-top:1.2rem;flex-wrap:wrap}
.sgroup{display:flex;flex-direction:column;gap:.5rem}
.sgroup .sl{font-family:var(--mono);font-size:.62rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--muted)}
.sgroup .sl a{color:var(--muted)}
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
.btn:focus-visible,.row:focus-visible{outline:none;
  box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--gold)}
.btn.primary{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.btn.primary:hover{background:var(--accent);border-color:var(--accent)}
.band.dark .btn.primary{background:#f1eee7;color:#232323;border-color:#f1eee7}
.band.dark .btn.primary:hover{background:var(--gold);border-color:var(--gold)}
.hero2-right{flex:1 1 53%;align-self:stretch;position:relative;overflow:hidden;background:var(--panel)}
.hero2-right #kg{position:absolute;inset:0;width:100%;height:100%;cursor:default}
.kg-hint{position:absolute;right:14px;bottom:12px;font-family:var(--mono);font-size:.62rem;
  letter-spacing:.08em;text-transform:uppercase;color:#8a8a8a;pointer-events:none;
  font-variant-numeric:tabular-nums}
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
@media(max-width:860px){ .split{grid-template-columns:1fr;gap:1.6rem} }

/* ---- section heads ---- */
.sec-head{margin:0 0 2.2rem}
.sec-head h2, .band h2{font-family:var(--serif);font-weight:600;font-optical-sizing:auto;
  font-size:clamp(1.7rem,3vw,2.5rem);letter-spacing:-.008em;line-height:1.15;margin:.5rem 0 0}
.sec-head p{margin:.5rem 0 0;color:var(--muted);max-width:44rem}

/* ---- start-here: three article columns left, head column right ---- */
.start-grid{display:grid;grid-template-columns:2.7fr 1fr;gap:clamp(2rem,4vw,4rem);align-items:center}
.start-grid .sec-head{margin:0}
.cards3{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
@media(max-width:1080px){ .cards3{grid-template-columns:1fr;gap:16px} }
@media(max-width:900px){
  .start-grid{grid-template-columns:1fr;gap:1.6rem}
  .start-grid .sec-head{order:-1}
  .cards3{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
}
.cardk{background:var(--panel);border:1px solid #3a3835;border-radius:0;
  padding:1.3rem 1.4rem 1.1rem;display:flex;flex-direction:column;gap:.55rem;
  text-decoration:none;color:#f1eee7;transition:border-color .15s,transform .15s,box-shadow .15s}
.cardk:hover{text-decoration:none;border-color:var(--gold);
  box-shadow:0 10px 28px rgba(35,35,35,.18)}
.cardk:focus-visible{outline:none;box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--gold)}
.cardk .meta{font-family:var(--mono);font-size:.65rem;letter-spacing:.07em;
  text-transform:uppercase;color:var(--gold)}
.cardk h3{font-family:var(--serif);font-weight:600;margin:0;font-size:1.18rem;line-height:1.3;color:#f1eee7}
.cardk .why{color:#a8a49c;font-size:.9rem;margin:0}
.cardk .foot{font-family:var(--mono);font-size:.7rem;color:#8f8b84;
  display:flex;justify-content:space-between;border-top:1px solid rgba(255,255,255,.1);padding-top:.65rem}
.cardk .foot .go{color:#f1eee7}
.cardk .foot .go::after{content:"→";display:inline-block;margin-left:.35em;
  transition:transform .15s var(--ease)}
@media(hover:hover){ .cardk:hover .foot .go::after{transform:translateX(4px)} }

/* digital crop marks — corner ticks OUTSIDE the block boundary (數位感邊框) */
.cardk,.tile,.crop{position:relative}
.cardk::after,.tile::after,.crop::after{content:"";position:absolute;inset:-6px;pointer-events:none;
  --tk:11px;--tw:1.5px;
  background-image:
    linear-gradient(var(--tick),var(--tick)),linear-gradient(var(--tick),var(--tick)),
    linear-gradient(var(--tick),var(--tick)),linear-gradient(var(--tick),var(--tick)),
    linear-gradient(var(--tick),var(--tick)),linear-gradient(var(--tick),var(--tick)),
    linear-gradient(var(--tick),var(--tick)),linear-gradient(var(--tick),var(--tick));
  background-position:left top,left top,right top,right top,
    left bottom,left bottom,right bottom,right bottom;
  background-size:var(--tk) var(--tw),var(--tw) var(--tk),var(--tk) var(--tw),var(--tw) var(--tk),
    var(--tk) var(--tw),var(--tw) var(--tk),var(--tk) var(--tw),var(--tw) var(--tk);
  background-repeat:no-repeat;transition:opacity .15s}
.cardk::after{--tick:#8a8378}
.cardk:hover::after{--tick:var(--gold)}
.tile::after{--tick:var(--gold);opacity:0}
.tile:hover::after{opacity:1}
.crop::after{--tick:rgba(214,168,120,.55)}

/* ---- experience: pinned scrollytelling on black ---- */
.xp-pin{height:380vh;position:relative;padding-block:0}
.xp-stage{position:sticky;top:0;min-height:100svh;display:flex;align-items:center}
.xp-grid{display:grid;grid-template-columns:minmax(230px,.72fr) 1.6fr;
  gap:clamp(2rem,4vw,4rem);align-items:center;width:100%;padding-block:clamp(2.5rem,5vh,4rem)}
.pitch{font-family:var(--serif);font-style:italic;font-size:clamp(1.1rem,1.6vw,1.3rem);
  line-height:1.45;margin:1.2rem 0 1.5rem;border-left:3px solid var(--gold);padding-left:1.1rem}
.xp-cta .btn{display:inline-block;margin-bottom:.8rem}
.xp-right{position:relative}
.rail{position:absolute;left:50%;top:6px;bottom:6px;width:2px;margin-left:-1px;background:rgba(255,255,255,.14)}
.rail i{position:absolute;left:0;top:0;width:100%;height:0%;background:var(--gold)}
.xp-item{position:relative;width:calc(50% - 1.9rem);padding:0 0 1.2rem;
  opacity:.15;transform:translateY(26px);
  transition:opacity .6s var(--ease),transform .6s var(--ease)}
.xp-item.on{opacity:1;transform:none}
.xp-item.L{margin-right:auto}
.xp-item.R{margin-left:auto}
.xp-item + .xp-item{margin-top:-2.4rem}
.xp-item::before{content:"";position:absolute;top:4px;width:9px;height:9px;border-radius:50%;
  background:var(--gold);opacity:.5;transition:opacity .3s}
.xp-item.on::before{opacity:1}
.xp-item.L::before{right:-1.9rem;transform:translateX(50%)}
.xp-item.R::before{left:-1.9rem;transform:translateX(-50%)}
.xp-left h2{font-size:clamp(1.4rem,2vw,1.9rem)}
.xp-edu{font-family:var(--mono);font-size:.68rem;letter-spacing:.05em;color:var(--muted);
  margin:1.4rem 0 0;text-transform:uppercase}
.xp-cert{font-family:var(--mono);font-size:.68rem;letter-spacing:.05em;color:var(--muted);
  margin:.5rem 0 0;text-transform:uppercase}
.xp-cert a{color:var(--gold);text-decoration:none}
.xp-cert a:hover{text-decoration:underline}
.xp-when{font-family:var(--mono);font-size:.68rem;letter-spacing:.07em;
  text-transform:uppercase;color:var(--gold)}
.xp-item h3{font-family:var(--serif);font-weight:600;margin:.25rem 0 0;font-size:1.15rem}
.xp-role{font-family:var(--mono);font-size:.68rem;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);margin:.15rem 0 .4rem}
.xp-item ul{margin:.15rem 0 0;padding-left:1.05rem;color:var(--muted);font-size:.88rem;line-height:1.5}
.xp-item li{margin:.25rem 0}
.xp-item li b{color:var(--fg);font-weight:600}
.xp-hook{font-family:var(--serif);font-style:italic;color:var(--gold)}
@media(max-width:900px),(max-height:600px){
  .xp-pin{height:auto;padding-block:clamp(4rem,9vw,8.5rem)}
  .xp-stage{position:static;display:block;min-height:0}
  .xp-grid{display:block;padding-block:0}
  .xp-right{margin-top:2rem;padding-left:1.6rem}
  .xp-item{opacity:1;transform:none;width:100%;margin:0;padding:1rem 0}
  .xp-item + .xp-item{margin-top:0;border-top:1px solid rgba(255,255,255,.1)}
  .xp-item::before{display:none}
  .rail{left:0;margin-left:0}
}
@media (prefers-reduced-motion:reduce){ .xp-item{opacity:1;transform:none;transition:none} }

/* ---- the system: deep device frame on black ---- */
.frame{background:#141311;border:1px solid rgba(255,255,255,.09);
  border-radius:0;padding:clamp(8px,1.2vw,14px);box-shadow:0 24px 70px rgba(0,0,0,.45)}
.win{background:#232323;border-radius:0;overflow:hidden;border:1px solid rgba(255,255,255,.08)}
.win-bar{display:flex;align-items:center;gap:1rem;padding:.8rem 1.1rem;
  border-bottom:1px solid rgba(255,255,255,.08)}
.win-bar .dots{display:flex;gap:7px}
.win-bar .dots i{width:11px;height:11px;border-radius:50%;background:#4a463f}
.win-bar .fname{font-family:var(--mono);font-size:.72rem;color:#a8a49c;letter-spacing:.04em}
.win-body{display:grid;grid-template-columns:290px 1fr;min-height:340px}
.tree{border-right:1px solid rgba(255,255,255,.08);padding:1rem 0;
  font-family:var(--mono);font-size:.76rem;color:#8f8b84;display:flex;flex-direction:column}
.tree .troot{color:#f1eee7;padding:.35rem 1.1rem}
.tree .lock{color:var(--gold);font-style:normal}
.titem{display:block;width:100%;text-align:left;background:none;border:none;cursor:pointer;
  font:inherit;color:#8f8b84;padding:.35rem 1.1rem;white-space:nowrap;
  transition:color .15s,background .15s}
.titem:hover{color:#f1eee7}
.titem.sel{background:#2f2c27;color:#f1eee7}
.titem:focus-visible{outline:none;box-shadow:inset 0 0 0 2px var(--gold)}
.code{padding:1.1rem 1.3rem;overflow:auto;max-height:clamp(300px,58svh,720px)}
.code pre{margin:0;font-family:var(--mono);font-size:.8rem;line-height:1.85;color:#c9c5bd}
.ln{display:block;opacity:0;transform:translateX(8px);
  transition:opacity .45s var(--ease),transform .45s var(--ease);transition-delay:var(--d,0s)}
.code.in .ln{opacity:1;transform:none}
.ln .no{display:inline-block;min-width:2.4em;color:#565248;user-select:none;
  font-variant-numeric:tabular-nums}
.k{color:var(--gold)} .s{color:#a8b78c} .c{color:#79746a;font-style:italic}
.f{color:#e8d5b5} .hl{background:#33302a;border-radius:3px;padding:0 .2em}
@media(max-width:760px){ .win-body{grid-template-columns:1fr;min-height:0} .tree{flex-direction:row;
  flex-wrap:wrap;border-right:none;border-bottom:1px solid rgba(255,255,255,.08);padding:.5rem}
  .tree .troot{display:none} .titem{width:auto;border-radius:6px} }
@media (prefers-reduced-motion:reduce){ .ln{opacity:1;transform:none;transition:none} }
.win-cap{font-family:var(--mono);font-size:.7rem;color:var(--muted);margin:1rem 0 0}

/* ---- github activity ---- */
.gh{padding:2.4rem 0 0;overflow-x:auto;position:relative}
.gh-grid i:hover{outline:1.5px solid var(--gold);outline-offset:1px}
.gh-tip{position:absolute;z-index:5;background:#232323;color:#f1eee7;
  font-family:var(--mono);font-size:.68rem;letter-spacing:.03em;padding:.45em .8em;
  white-space:nowrap;pointer-events:none;opacity:0;transform:translate(-50%,-135%);
  transition:opacity .12s;font-variant-numeric:tabular-nums}
.gh-tip.show{opacity:1}
.gh-head{display:flex;justify-content:space-between;align-items:baseline;
  gap:1rem;margin-bottom:1.1rem;flex-wrap:wrap}
.gh-title{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted)}
a.gh-title:hover{color:var(--fg);text-decoration:none}
.gh-months{display:flex;font-family:var(--mono);font-size:.62rem;color:var(--muted);margin:0 0 .45rem}
.gh-months span{width:24px;flex:none}
.gh-grid{display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,20px);gap:4px;width:max-content}
.gh-grid i{width:20px;height:20px;border-radius:0;background:var(--gh0);
  transform:scale(.4);opacity:0;
  transition:transform .4s var(--ease),opacity .4s var(--ease);transition-delay:var(--d,0s)}
.gh-grid.in i{transform:scale(1);opacity:1}
.gh-grid i.l1{background:var(--gh1)} .gh-grid i.l2{background:var(--gh2)}
.gh-grid i.l3{background:var(--gh3)} .gh-grid i.l4{background:var(--gh4)}
.gh-grid i.f{background:transparent;border:1px dashed #d5cdbc}
.gh-grid i.sel{outline:2px solid var(--gold);outline-offset:1px}
.gh-flex{display:flex;gap:2rem;align-items:stretch}
.gh-act{font-family:var(--mono);font-size:.72rem;color:var(--muted);flex:1;min-width:200px;
  border-left:1px solid var(--border);padding:.2rem 0 .2rem 1.6rem;
  font-variant-numeric:tabular-nums;line-height:2}
.gh-act .dim{opacity:.55}
@media(max-width:700px){ .gh-flex{flex-direction:column;gap:1.2rem}
  .gh-act{border-left:none;border-top:1px solid var(--border);padding:1rem 0 0} }
.gh-act b{color:var(--fg);font-weight:600}
.gh-act .r{color:var(--gold)}
.gh-foot{display:flex;justify-content:space-between;align-items:center;
  margin-top:1rem;gap:1rem;flex-wrap:wrap}
.gh-note{font-family:var(--mono);font-size:.68rem;color:var(--muted)}
.gh-leg{display:flex;align-items:center;gap:4px;font-family:var(--mono);
  font-size:.62rem;color:var(--muted)}
.gh-leg i{width:11px;height:11px;border-radius:0;display:inline-block}
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

/* ---- section 06: workflow stepper (inline hand-made SVG · click a phase) ---- */
.wf{display:grid;gap:1.4rem;margin-top:1.5rem}
@media(min-width:1080px){ .wf{grid-template-columns:1.55fr 1fr;align-items:center} }
.wf-map{background:var(--bg);padding:10px}
.wf-map svg{width:100%;height:auto;display:block}
.wf-map .wf-box{cursor:pointer}
.wf-map .wf-box rect{transition:fill .25s var(--ease),stroke .25s var(--ease)}
.wf-map .wf-box:not(.active){opacity:.45;transition:opacity .25s var(--ease)}
.wf-map .wf-box.active rect{fill:#f6ecda;stroke:var(--gold);stroke-width:2.5}
.wf-map svg.wf-looping .wf-loop-arrow{animation:wfpulse 1.5s ease-in-out infinite}
@keyframes wfpulse{50%{stroke-width:3.6;opacity:.5}}
.wf-side{display:flex;flex-direction:column;gap:1.1rem}
.wf-eyebrow{font-family:var(--mono);font-size:.7rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--gold);margin:0}
.wf-detail h3{font-family:var(--serif);font-weight:600;font-size:1.35rem;margin:.25rem 0 .55rem}
.wf-detail ul{margin:0;padding-left:1.1rem;color:var(--fg)}
.wf-detail li{margin:.25rem 0}
.wf-fields{margin:.7rem 0 0}
.wf-fields a{font-family:var(--mono);font-size:.76rem;color:var(--accent);
  border-bottom:1px dotted var(--gold);text-decoration:none}
.wf-fields a:hover{color:var(--gold)}
.wf-controls{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap}
.wf-btn{border:1px solid var(--border);background:var(--surface);border-radius:999px;
  width:42px;height:42px;cursor:pointer;font-size:1.05rem;color:var(--fg);transition:border-color .15s}
.wf-btn:hover{border-color:var(--gold)}
.wf-rail{display:flex;gap:6px}
.wf-tab{border:1px solid var(--border);background:transparent;border-radius:999px;
  width:36px;height:36px;font-family:var(--mono);font-size:.72rem;cursor:pointer;
  color:var(--muted);transition:background .15s,color .15s}
.wf-tab[aria-selected="true"]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.wf-chunk{font-family:var(--mono);font-size:.74rem;color:var(--gold);margin-left:auto;
  font-variant-numeric:tabular-nums}
@media (prefers-reduced-motion:reduce){ .wf-map svg.wf-looping .wf-loop-arrow{animation:none} }

/* ---- write-up archive: shopping-grid tiles + reader overlay ---- */
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 18px}
.controls select,.controls input{padding:9px 12px;border-radius:9px;border:1px solid var(--border);
  background:var(--surface);color:var(--fg);font-size:1rem;font-family:inherit}
.controls .count{color:var(--muted);font-size:.82rem;margin-left:auto;font-variant-numeric:tabular-nums}
.tilegrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:20px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:0;
  padding:1.1rem 1.2rem 1rem;display:flex;flex-direction:column;gap:.6rem;cursor:pointer;
  user-select:none;transition:border-color .15s,transform .15s,box-shadow .15s;
  animation:tileIn .45s var(--ease) both;animation-delay:var(--d,0s)}
@keyframes tileIn{from{opacity:0;transform:translateY(10px)}}
/* no transform on hover — a lift moves the edge away from the cursor and
   causes a hover/unhover flicker loop at the boundary. Border + shadow only. */
.tile:hover{border-color:var(--gold);box-shadow:0 8px 24px rgba(35,35,35,.07)}
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
.reader-panel{position:relative;background:var(--bg);border:1px solid var(--border);border-radius:2px;
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
.rbody a.wl{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--gold)}
.rbody a.wl:hover{color:var(--gold)}
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
.floatnav .fn-brand{font-family:var(--serif);font-weight:600;font-size:.95rem;
  letter-spacing:-.01em;color:#232323;padding:7px 10px 7px 15px}
.floatnav .fn-brand:hover{color:#232323}
.floatnav .ext{color:#8a8378}
@media(max-width:640px){ .floatnav a{padding:7px 11px;font-size:.78rem}
  .floatnav .ext,.floatnav .fn-brand{display:none} }

/* ---- digital instrument layer (數位感): dot grid, HUD corners, scan, decode ---- */
body{background-image:radial-gradient(color-mix(in srgb,var(--fg) 9%,transparent) 1px,transparent 1px);
  background-size:26px 26px}
.band.dark{background-image:radial-gradient(rgba(241,238,231,.05) 1px,transparent 1px);
  background-size:26px 26px}
.progress{position:fixed;top:0;left:0;right:0;height:2px;z-index:70;pointer-events:none}
.progress i{display:block;height:100%;background:var(--gold);transform-origin:left;transform:scaleX(0)}
.hud{position:relative}
.hud::before,.hud::after{content:"";position:absolute;width:14px;height:14px;
  pointer-events:none;opacity:.65;z-index:2}
.hud::before{top:9px;left:9px;border-top:1.5px solid var(--gold);border-left:1.5px solid var(--gold)}
.hud::after{bottom:9px;right:9px;border-bottom:1.5px solid var(--gold);border-right:1.5px solid var(--gold)}
.win{position:relative}
.win::after{content:"";position:absolute;left:0;right:0;top:-15%;height:44px;pointer-events:none;
  background:linear-gradient(180deg,transparent,color-mix(in srgb,var(--gold) 9%,transparent),transparent);
  animation:scan 7s linear infinite}
@keyframes scan{from{top:-12%} to{top:112%}}
@media (prefers-reduced-motion:reduce){ .win::after{animation:none;display:none} }
</style>
</head>"""


# ---- client logic (plain JS, no interpolation) ------------------------------
SCRIPT = r"""<script>
const $ = id => document.getElementById(id);
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---- floating tab nav: highlight the section in view ---- */
(function(){
  const nav=$('floatnav'); if(!nav) return;
  const links=[].slice.call(nav.querySelectorAll('a[data-sec]'));
  const secs=links.map(a=>$(a.dataset.sec)).filter(Boolean);
  const io=new IntersectionObserver(es=>{ es.forEach(e=>{ if(e.isIntersecting){
    links.forEach(a=>a.classList.toggle('active',a.dataset.sec===e.target.id)); } }); },
    {rootMargin:'-45% 0px -45% 0px'});
  secs.forEach(s=>io.observe(s));
})();

/* ---- motion system: typewriter, reveals, odometers, scrolly, gh grid ---- */
(function(){
  /* h1 "I work on <word>" — classic typewriter loop: type → hold → delete → next */
  const typed=$('typed');
  if(typed){
    const WORDS=['clean algorithms','the right data structure','NLP from scratch',
                 'AI infrastructure','learning in public'];
    if(REDUCED){ typed.textContent=WORDS[0]; }
    else{
      let wi=0,ci=0,del=false;
      (function tick(){
        const w=WORDS[wi%WORDS.length];
        if(!del){ ci++; typed.textContent=w.slice(0,ci);
          if(ci>=w.length){ del=true; setTimeout(tick,1700); return; } }
        else{ ci--; typed.textContent=w.slice(0,ci);
          if(ci<=0){ del=false; wi++; } }
        setTimeout(tick,del?38:72);
      })();
    }
  }

  /* scroll progress meter */
  const prog=$('prog');
  if(prog){
    let raf=false;
    function up(){ raf=false; const h=document.documentElement;
      const p=h.scrollTop/Math.max(1,h.scrollHeight-h.clientHeight);
      prog.style.transform='scaleX('+p+')'; }
    addEventListener('scroll',()=>{ if(!raf){raf=true;requestAnimationFrame(up);} },{passive:true});
    up();
  }

  /* kicker type-in (digital layer): types out after the fade so it's actually visible */
  function decode(el){
    if(el._dec) return; el._dec=true;
    const orig=el.textContent;
    if(REDUCED) return;
    el.textContent='';
    let i=0;
    setTimeout(function step(){
      el.textContent=orig.slice(0,++i);
      if(i<orig.length) setTimeout(step,52);
    },300);
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
    if(e.target.classList.contains('dec')) decode(e.target);
    e.target.querySelectorAll('.odo').forEach(count);
    e.target.querySelectorAll('.dec').forEach(decode);
    if(e.target.id==='win'){ const p=e.target.querySelector('.code:not([hidden])');
      if(p) p.classList.add('in'); }
    io.unobserve(e.target); } } },{threshold:.2});
  document.querySelectorAll('.band .rv, footer .rv, .gh-grid, .xp-left .dec').forEach(el=>io.observe(el));
  const win=$('win'); if(win) io.observe(win);

  /* the-system editor: file tree switches real panes, line reveal replays */
  if(win){
    const items=win.querySelectorAll('.titem');
    const panes=win.querySelectorAll('.code');
    const fname=$('win-fname');
    items.forEach(b=>b.onclick=()=>{
      items.forEach(x=>{ x.classList.toggle('sel',x===b);
        x.setAttribute('aria-selected',x===b?'true':'false'); });
      panes.forEach(p=>{ const on=p.dataset.pane===b.dataset.pane;
        p.hidden=!on;
        if(on){ p.classList.remove('in'); void p.offsetWidth;
          if(REDUCED) p.classList.add('in');
          else requestAnimationFrame(()=>p.classList.add('in')); } });
      if(fname&&b.dataset.name) fname.textContent=b.dataset.name;
    });
  }

  /* résumé pinned scrollytelling (sticky stage + scroll progress) */
  const pin=$('xp');
  if(pin){
    const items=pin.querySelectorAll('.xp-item');
    const rail=$('railfill');
    const n=items.length;
    const T=[...items].map((_,i)=> n>1 ? 0.04+i*0.82/(n-1) : 0.04);
    function xp(){
      if(matchMedia('(max-width:900px), (max-height:600px)').matches || REDUCED){
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
  if(grid && typeof CONTRIB!=='undefined' && CONTRIB && CONTRIB.days){
    let cells='';
    CONTRIB.days.forEach((day,i)=>{
      const w=Math.floor(i/7), d=i%7;
      cells+='<i class="'+(day.l<0?'f':'l'+day.l)+'" data-i="'+i+'" style="--d:'+(w*30+d*8)+'ms"></i>';
    });
    grid.innerHTML=cells;
    const months=$('ghmonths');
    if(months) months.innerHTML=CONTRIB.months.map(m=>'<span>'+m+'</span>').join('');
    /* GitHub-style hover tooltip with the real count */
    const box=grid.closest('.gh');
    const tip=document.createElement('div'); tip.className='gh-tip'; box.appendChild(tip);
    const MN=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    grid.addEventListener('mouseover',e=>{
      const c=e.target.closest('i'); if(!c||!c.dataset.i) return;
      const day=CONTRIB.days[+c.dataset.i]; if(!day) return;
      const dt=new Date(day.d+'T00:00:00');
      tip.textContent=(day.l<0?'upcoming':(day.c===1?'1 contribution':day.c+' contributions'))
        +' · '+MN[dt.getMonth()]+' '+dt.getDate();
      const r=c.getBoundingClientRect(), b=box.getBoundingClientRect();
      tip.style.left=(r.left-b.left+r.width/2)+'px';
      tip.style.top=(r.top-b.top)+'px';
      tip.classList.add('show');
    });
    grid.addEventListener('mouseout',()=>tip.classList.remove('show'));
    /* click a day -> its contribution activity (from the public events API) */
    const act=$('ghact');
    grid.addEventListener('click',e=>{
      const c=e.target.closest('i'); if(!c||!c.dataset.i||!act) return;
      const day=CONTRIB.days[+c.dataset.i]; if(!day||day.l<0) return;
      grid.querySelectorAll('.sel').forEach(x=>x.classList.remove('sel'));
      if(act.dataset.d===day.d){
        act.innerHTML='<span class="dim">select a day —</span>'; act.dataset.d=''; return; }
      c.classList.add('sel'); act.dataset.d=day.d;
      const dt=new Date(day.d+'T00:00:00');
      let h='<b>'+MN[dt.getMonth()]+' '+dt.getDate()+'</b> — '
        +(day.c===1?'1 contribution':day.c+' contributions');
      if(day.a && day.a.length){
        h+=day.a.map(([repo,pushes,events])=>{
          const bits=[];
          if(pushes) bits.push(pushes+(pushes===1?' push':' pushes'));
          if(events) bits.push(events+(events===1?' event':' events'));
          return '<br><span class="r">▸ '+repo+'</span> — '+bits.join(' · ');
        }).join('');
      } else {
        h+='<br>no public details (private repo, or older than the events window)';
      }
      act.innerHTML=h;
    });
  }
})();

/* ---- write-up archive: shopping-grid tiles + reader overlay ---- */
(function(){
  const grid=$('grid'); if(!grid) return;
  const tagSel=$('f-tag');
  TAGS.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;tagSel.appendChild(o);});
  const diffPill=d=>d?'<span class="pill diff-'+d+'">'+d+'</span>':'';
  const DOM_LABEL={leetcode:'LeetCode',ai:'AI','software-engineering':'Software Eng',systems:'Systems'};
  const domPill=d=>'<span class="pill domain'+(d==='ai'?' ai':'')+'">'+(DOM_LABEL[d]||d)+'</span>';
  function tileHTML(c,i){
    return '<article class="tile" id="card-'+c.id+'" data-id="'+c.id+'" tabindex="0" role="button" '
      +'aria-haspopup="dialog" style="--d:'+((i%12)*40)+'ms">'
      +'<div class="t-top">'+domPill(c.domain)+diffPill(c.difficulty)+'</div>'
      +'<h3>'+c.title+'</h3>'
      +'<div class="tags">'+c.tags.slice(0,3).map(t=>'<span>#'+t+'</span>').join('')+'</div>'
      +'<div class="t-foot"><span>~'+c.words+' words</span><span class="go">Read</span></div></article>';
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

/* ---- section 06: workflow stepper — click a phase box in the inline SVG ---- */
(function(){
  const sec=$('build'); if(!sec) return;
  const PH=['explore','spec','plan','build','verify','commit'], LOOP=3;
  const details=[].slice.call(sec.querySelectorAll('.wf-detail'));
  const boxes=[].slice.call(sec.querySelectorAll('.wf-box'));
  const tabs=[].slice.call(sec.querySelectorAll('.wf-tab'));
  const svg=sec.querySelector('.wf-map svg'), chunkEl=$('wf-chunk');
  let phase=0, chunk=1;
  function render(){
    const key=PH[phase], inLoop=phase>=LOOP;
    details.forEach(d=>d.hidden=d.dataset.phase!==key);
    boxes.forEach(b=>b.classList.toggle('active',b.dataset.phase===key));
    tabs.forEach(t=>t.setAttribute('aria-selected',t.dataset.phase===key?'true':'false'));
    if(svg) svg.classList.toggle('wf-looping',inLoop);
    if(chunkEl){ chunkEl.hidden=!inLoop; chunkEl.textContent='chunk '+chunk; }
  }
  function go(p){ if(p>=0&&p<PH.length){ phase=p; render(); } }
  function next(){ if(phase===PH.length-1){ phase=LOOP; chunk++; } else phase++; render(); }
  function prev(){ if(phase===LOOP&&chunk>1){ phase=PH.length-1; chunk--; } else if(phase>0){ phase--; } render(); }
  $('wf-next').onclick=next; $('wf-prev').onclick=prev;
  boxes.forEach(b=>{ b.style.cursor='pointer'; b.addEventListener('click',()=>go(PH.indexOf(b.dataset.phase))); });
  tabs.forEach(t=>t.addEventListener('click',()=>go(PH.indexOf(t.dataset.phase))));
  sec.addEventListener('keydown',e=>{
    if(e.key==='ArrowRight'){ next(); e.preventDefault(); }
    else if(e.key==='ArrowLeft'){ prev(); e.preventDefault(); } });
  render();
})();

/* ---- knowledge map: four domain clusters packed into one round mass ---- */
(function(){
  const cv=$('kg'); if(!cv||typeof GRAPH==='undefined'||!GRAPH.nodes) return;
  const ctx=cv.getContext('2d'), panel=$('kg-panel'), hud=$('kg-hud');
  const N=GRAPH.nodes, E=GRAPH.edges;
  N.forEach((n,i)=>n._i=i);
  const adj=N.map(()=>[]); E.forEach(e=>{adj[e[0]].push(e[1]); adj[e[1]].push(e[0]);});
  if(hud) hud.textContent='nodes '+N.length+' · edges '+E.length+' · click a topic';
  let W=0,H=0,DPR=Math.min(window.devicePixelRatio||1,2);
  function resize(){ const r=cv.getBoundingClientRect(); W=r.width; H=r.height;
    cv.width=W*DPR; cv.height=H*DPR; ctx.setTransform(DPR,0,0,DPR,0,0); }
  new ResizeObserver(resize).observe(cv); resize();

  /* force-directed community graph: springs pull linked nodes together, every pair repels
     (within range), and each node drifts toward its domain's home — the four domains loosely
     group but nodes are draggable and the whole thing settles into a spread mass. */
  const DOMS=[{name:'LeetCode'},{name:'AI'},{name:'Systems'},{name:'Software'}];
  const DC=[[0.449,0.453],[0.551,0.447],[0.461,0.577],[0.544,0.565]];
  const counts=[0,0,0,0]; N.forEach(n=>counts[n.dom]++);
  DOMS.forEach((d,i)=>d.count=counts[i]);
  const deg=adj.map(a=>a.length);
  function mulberry32(a){ return function(){ a|=0; a=a+0x6D2B79F5|0;
    let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t;
    return ((t^t>>>14)>>>0)/4294967296; }; }
  const rnd=mulberry32(424242);
  const byDom=[[],[],[],[]]; N.forEach(n=>byDom[n.dom].push(n));
  byDom.forEach(arr=>{                                   // seed order → initial packed positions
    arr.sort((a,b)=> a.type===b.type ? (b.count||0)-(a.count||0) : (a.type==='tag'?-1:1));
    const K=arr.length;
    arr.forEach((n,j)=>{ n.u=Math.pow((j+0.5)/K,0.48); n.th=j*2.399963267;
      n.ox=(rnd()-0.5)*0.20; n.oy=(rnd()-0.5)*0.20; });
  });

  /* --- physics (constants tuned offline to fill the panel without escaping) --- */
  const REPEL=-90, R2=160*160, SPRING=0.30, REST=28, GRAV=0.09, VD=0.60, VMAX=14;
  let alpha=0, alphaTarget=0, inited=false, dragging=null, hover=null, sel=null;
  const AD=0.021, AMIN=0.004;
  const isNbr=(m,n)=>m&&(n===m||adj[m._i].indexOf(n._i)>=0);

  function initPos(){
    for(const n of N){ const cx=DC[n.dom][0]*W, cy=DC[n.dom][1]*H,
        R=Math.sqrt(counts[n.dom])*Math.min(W,H)*0.05;
      n.x=cx+(n.u*Math.cos(n.th)+n.ox)*R; n.y=cy+(n.u*Math.sin(n.th)+n.oy)*R; n.vx=0; n.vy=0; }
    inited=true;
  }
  function tick(){
    alpha += (alphaTarget-alpha)*AD;
    for(const n of N){ n.fx=0; n.fy=0; }
    for(let i=0;i<N.length;i++){ const a=N[i];             // repulsion (capped range)
      for(let j=i+1;j<N.length;j++){ const b=N[j];
        let dx=b.x-a.x, dy=b.y-a.y, d2=dx*dx+dy*dy;
        if(d2>R2) continue; if(d2<1) d2=1;
        const w=REPEL*alpha/d2;
        a.fx+=dx*w; a.fy+=dy*w; b.fx-=dx*w; b.fy-=dy*w; } }
    for(const e of E){ const a=N[e[0]], b=N[e[1]];         // link springs (degree-biased)
      let dx=b.x-a.x, dy=b.y-a.y, dist=Math.hypot(dx,dy)||1;
      const l=(dist-REST)/dist*SPRING*alpha, ba=deg[a._i]/(deg[a._i]+deg[b._i]), bb=1-ba;
      if(a!==dragging){ a.x+=dx*l*bb; a.y+=dy*l*bb; }
      if(b!==dragging){ b.x-=dx*l*ba; b.y-=dy*l*ba; } }
    const mgx=W*0.06, mgy=H*0.06;
    for(const n of N){
      if(n===dragging){ n.vx=0; n.vy=0; continue; }
      n.fx+=(DC[n.dom][0]*W-n.x)*GRAV*alpha; n.fy+=(DC[n.dom][1]*H-n.y)*GRAV*alpha;
      n.vx=(n.vx+n.fx)*VD; n.vy=(n.vy+n.fy)*VD;
      const sp=Math.hypot(n.vx,n.vy); if(sp>VMAX){ n.vx*=VMAX/sp; n.vy*=VMAX/sp; }
      n.x+=n.vx; n.y+=n.vy;
      if(n.x<mgx){ n.x=mgx; n.vx*=-0.3; } else if(n.x>W-mgx){ n.x=W-mgx; n.vx*=-0.3; }
      if(n.y<mgy){ n.y=mgy; n.vy*=-0.3; } else if(n.y>H-mgy){ n.y=H-mgy; n.vy*=-0.3; }
    }
    if(!dragging){ let mx=0,my=0; for(const n of N){ mx+=n.x; my+=n.y; }   // recenter centroid
      const sx=W/2-mx/N.length, sy=H/2-my/N.length;
      for(const n of N){ n.x+=sx; n.y+=sy; } }
  }
  const born=performance.now();

  function draw(t){
    if(!inited && W>0){ initPos();
      if(REDUCED){ alpha=1; for(let k=0;k<320;k++) tick(); alpha=0; }   // pre-settle, no anim
      else alpha=1; }
    if(alpha>AMIN || dragging) tick();
    ctx.clearRect(0,0,W,H);
    const birth=REDUCED?1:Math.min(1,(t-born)/1000);
    const focus=hover||sel;
    for(const e of E){ const a=N[e[0]],b=N[e[1]];
      const hot=focus&&(a===focus||b===focus);
      ctx.strokeStyle=hot?'#d6a878':'#8f8b84';
      ctx.globalAlpha=(hot?0.85:(focus?0.04:(a.dom!==b.dom?0.07:0.13)))*birth;
      ctx.lineWidth=hot?1.2:0.6;
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); }
    for(const n of N){
      const nb=focus&&isNbr(focus,n);
      const base=n.type==='tag'?(2.4+0.05*(n.count||1)):1.6;
      ctx.globalAlpha=(focus?(nb?1:0.15):(n.type==='note'?0.5:0.9))*birth;
      ctx.fillStyle=(n===focus)?'#d6a878':(nb?'#f1eee7':'#ededed');
      ctx.beginPath(); ctx.arc(n.x,n.y,nb?base*1.7:base,0,6.283); ctx.fill();
      if(n===focus){ ctx.globalAlpha=birth; ctx.strokeStyle='#232323'; ctx.lineWidth=1.6; ctx.stroke(); }
    }
    /* labels: hub topics at rest; with a focus, only it + its neighbours stay readable */
    ctx.textAlign='center'; ctx.textBaseline='top';
    for(const n of N){
      let a;
      if(focus){ a = (n===focus||isNbr(focus,n)) ? 1 : 0.05; }
      else if(n.type==='tag'){
        if((n.count||0)<2) continue;          // singleton topics: label on focus only
        a = 0.72; }
      else continue;                          // notes stay unlabeled until a topic is focused
      if(a<=0.06) continue;
      const lab=n.type==='tag'?n.label:n.full.replace(/^\d+\.\s*/,'');
      ctx.font=(n===focus?'600 12px ':(n.type==='tag'?'500 10px ':'400 9px '))+'"JetBrains Mono",monospace';
      ctx.globalAlpha=a*birth;
      ctx.lineWidth=3; ctx.strokeStyle='#232323'; ctx.strokeText(lab,n.x,n.y+7);
      ctx.fillStyle=n===focus?'#d6a878':'#c9c5bd'; ctx.fillText(lab,n.x,n.y+7);
    }
    /* domain names, sitting just outside each cluster's live centroid */
    const cs=[[0,0,0],[0,0,0],[0,0,0],[0,0,0]];
    for(const n of N){ const c=cs[n.dom]; c[0]+=n.x; c[1]+=n.y; c[2]++; }
    for(const c of cs){ if(c[2]){ c[0]/=c[2]; c[1]/=c[2]; } }
    const rad=[0,0,0,0];
    for(const n of N){ const d=Math.hypot(n.x-cs[n.dom][0],n.y-cs[n.dom][1]); if(d>rad[n.dom]) rad[n.dom]=d; }
    ctx.textBaseline='alphabetic';
    DOMS.forEach((d,di)=>{ const c=cs[di]; if(!c[2]) return;
      let dx=c[0]-W/2, dy=c[1]-H/2, m=Math.hypot(dx,dy)||1; dx/=m; dy/=m;
      const lx=c[0]+dx*(rad[di]+18), ly=c[1]+dy*(rad[di]+18);
      ctx.textAlign=dx<-0.25?'right':(dx>0.25?'left':'center');
      ctx.globalAlpha=(focus?0.4:1)*birth;
      ctx.font='600 15px "Fraunces",Georgia,serif';
      ctx.lineWidth=4; ctx.strokeStyle='#232323'; ctx.strokeText(d.name,lx,ly);
      ctx.fillStyle='#a9a49a'; ctx.fillText(d.name,lx,ly);
      ctx.font='500 9px "JetBrains Mono",monospace'; ctx.fillStyle='#767068';
      ctx.fillText(d.count+' nodes',lx,ly+13); });
    ctx.textAlign='center'; ctx.globalAlpha=1;
  }
  let visible=true;                                     // pause the loop off-screen
  new IntersectionObserver(es=>{ visible=es[0].isIntersecting; },{threshold:0}).observe(cv);
  (function loop(t){
    if(visible && !document.hidden) draw(t||performance.now());
    requestAnimationFrame(loop);
  })();

  /* topics are the first layer for SELECTION: only they open the panel at rest, and a note
     opens only while its topic is selected. Dragging, though, grabs ANY dot. */
  const targetable=n=>n.type==='tag'||(sel&&sel.type==='tag'&&isNbr(sel,n));
  function nodeAt(x,y,all){ let best=null,bd=196;       // 14px hit radius
    for(const n of N){ if(!all && !targetable(n)) continue;
      const d=(x-n.x)*(x-n.x)+(y-n.y)*(y-n.y);
      if(d<bd){ bd=d; best=n; } }
    return best; }
  function selectNode(n){
    sel=n;
    const nbrs=adj[n._i].map(i=>N[i]);
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
    panel.querySelector('.pclose').onclick=()=>{ panel.classList.remove('open'); sel=null; };
    panel.querySelectorAll('.pitem').forEach(a=>a.onclick=()=>{
      if(a.dataset.id||a.dataset.open) window.expandCard(a.dataset.id||a.dataset.open);
      else if(a.dataset.tag) selectNode(N[+a.dataset.tag]);
    });
  }
  let down=null;                                        // {x,y,moved}
  function reheat(){ alpha=Math.max(alpha,0.3); alphaTarget=0.3; }
  function pDown(x,y){ const g=nodeAt(x,y,true);
    down={x,y,moved:false}; if(g){ dragging=g; reheat(); cv.style.cursor='grabbing'; } }
  function pMove(x,y){
    if(dragging){ dragging.x=x; dragging.y=y; dragging.vx=0; dragging.vy=0;
      if(down && Math.abs(x-down.x)+Math.abs(y-down.y)>4) down.moved=true; reheat(); return; }
    hover=nodeAt(x,y,false);
    cv.style.cursor=(hover||nodeAt(x,y,true))?'grab':'default'; }
  function pUp(x,y){
    if(down && !down.moved){ const t=nodeAt(x,y,false);
      if(t) selectNode(t); else { sel=null; panel.classList.remove('open'); } }
    dragging=null; down=null; alphaTarget=0; cv.style.cursor='grab'; }

  cv.addEventListener('mousemove',e=>{ const r=cv.getBoundingClientRect(); pMove(e.clientX-r.left,e.clientY-r.top); });
  cv.addEventListener('mousedown',e=>{ const r=cv.getBoundingClientRect(); pDown(e.clientX-r.left,e.clientY-r.top); });
  window.addEventListener('mouseup',e=>{ if(!down) return; const r=cv.getBoundingClientRect(); pUp(e.clientX-r.left,e.clientY-r.top); });
  cv.addEventListener('mouseleave',()=>{ hover=null; });
  /* touch: one finger drags a dot, a tap selects */
  cv.addEventListener('touchstart',e=>{ const t=e.touches[0],r=cv.getBoundingClientRect(); pDown(t.clientX-r.left,t.clientY-r.top); },{passive:true});
  cv.addEventListener('touchmove',e=>{ if(!dragging) return; const t=e.touches[0],r=cv.getBoundingClientRect();
    pMove(t.clientX-r.left,t.clientY-r.top); e.preventDefault(); },{passive:false});
  cv.addEventListener('touchend',e=>{ const t=e.changedTouches[0],r=cv.getBoundingClientRect(); pUp(t.clientX-r.left,t.clientY-r.top); },{passive:true});
})();
</script>"""


def main():
    cards = collect()
    # tile order: AI + engineering notes first, LeetCode write-ups last
    cards = ([c for c in cards if c["domain"] != "leetcode"]
             + [c for c in cards if c["domain"] == "leetcode"])
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
