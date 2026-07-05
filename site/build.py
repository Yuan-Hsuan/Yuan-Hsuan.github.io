#!/usr/bin/env python3
"""
build.py — static site generator for the "Learning in Public" portfolio.

Walks the public content folders, reads each file's YAML frontmatter (per ../SCHEMA.md),
renders ONLY `visibility: public` cards, and writes a single self-contained ../index.html.

No dependencies (stdlib only). No backend, no database — GitHub Pages serves the output.

Usage:
    python site/build.py
"""
from __future__ import annotations
import html
import json
import re
from pathlib import Path

# ---- config -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent          # repo root
CONTENT_DIRS = ["leetcode", "ai-knowledge"]            # public domains shown on the site
GITHUB_USER = "Yuan-Hsuan"
OUT = ROOT / "index.html"

DOMAIN_LABEL = {"leetcode": "LeetCode", "ai": "AI Knowledge"}


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
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)  # [t](url)
    return s


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        # fenced code
        if line.lstrip().startswith("```"):
            lang = line.lstrip()[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(html.escape(lines[i], quote=False)); i += 1
            i += 1  # skip closing fence
            cls = f' class="lang-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>" + "\n".join(buf) + "</code></pre>")
            continue
        # table
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
        # blockquote
        if line.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip()); i += 1
            out.append("<blockquote>" + _inline(" ".join(buf)) + "</blockquote>")
            continue
        # heading
        m = re.match(r"(#{1,6})\s+(.*)", line)
        if m:
            lvl = min(len(m.group(1)) + 1, 6)   # ## -> h3-ish; keep hierarchy under card title
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        # unordered list
        if re.match(r"\s*[-*]\s+", line):
            buf = []
            while i < n and re.match(r"\s*[-*]\s+", lines[i]):
                buf.append(re.sub(r"\s*[-*]\s+", "", lines[i], count=1)); i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ul>")
            continue
        # ordered list
        if re.match(r"\s*\d+\.\s+", line):
            buf = []
            while i < n and re.match(r"\s*\d+\.\s+", lines[i]):
                buf.append(re.sub(r"\s*\d+\.\s+", "", lines[i], count=1)); i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ol>")
            continue
        # blank
        if not line.strip():
            i += 1
            continue
        # paragraph
        buf = []
        while i < n and lines[i].strip() and not re.match(r"(#{1,6}\s|\s*[-*]\s|\s*\d+\.\s|>|\||```)", lines[i]):
            buf.append(lines[i]); i += 1
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


# ---- collect cards ----------------------------------------------------------
def collect():
    cards = []
    for d in CONTENT_DIRS:
        for path in sorted((ROOT / d).rglob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            if meta.get("visibility") != "public":      # SAFETY BELT
                continue
            cards.append({
                "id": meta.get("id", path.stem),
                "domain": meta.get("domain", d),
                "title": meta.get("title", path.stem),
                "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
                "difficulty": meta.get("difficulty", ""),
                "mastery": int(meta.get("mastery", 0) or 0),
                "source": meta.get("source", ""),
                "body_html": md_to_html(body),
            })
    return cards


# ---- LeetCode coverage panel (solved overview from site/solved.json) --------
def build_solved_section() -> str:
    """Self-contained (CSS+HTML+JS) coverage panel; '' if solved.json is absent."""
    path = ROOT / "site" / "solved.json"
    if not path.exists():
        return ""
    d = json.loads(path.read_text(encoding="utf-8"))
    c = d.get("counts", {})
    user = d.get("username", GITHUB_USER)
    rows = []
    for p in d.get("problems", []):
        diff = p.get("difficulty", "")
        title = html.escape(p.get("title", ""), quote=True)
        slug = p.get("slug", "")
        paid = ' <span class="paid">🔒</span>' if p.get("paid") else ""
        search = html.escape(f'{title} {p.get("id","")}'.lower(), quote=True)
        rows.append(
            f'<tr data-d="{diff}" data-t="{search}">'
            f'<td class="num">{p.get("id","")}</td>'
            f'<td><a href="https://leetcode.com/problems/{slug}/" target="_blank" rel="noopener">{title}</a>{paid}</td>'
            f'<td><span class="pill diff-{diff}">{diff}</span></td></tr>'
        )
    rows_html = "\n".join(rows)
    return f"""
<style>
  .coverage {{ padding:8px 0 4px; }}
  .coverage h2 {{ font-size:1.4rem; margin:0 0 4px; }}
  .c-easy {{ color:var(--easy); }} .c-medium {{ color:var(--medium); }} .c-hard {{ color:var(--hard); }}
  details.solved {{ margin:18px 0 0; }}
  details.solved > summary {{ cursor:pointer; padding:10px 14px; background:var(--card);
     border:1px solid var(--border); border-radius:10px; font-size:.95rem; user-select:none; }}
  .solved-controls {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin:14px 0 6px; }}
  .solved-controls input, .solved-controls select {{ padding:8px 10px; border-radius:9px;
     border:1px solid var(--border); background:var(--card); color:var(--fg); font-size:.9rem; }}
  #lc-count {{ color:var(--muted); font-size:.85rem; margin-left:auto; }}
  .solved-table-wrap {{ max-height:520px; overflow:auto; border:1px solid var(--border); border-radius:10px; }}
  #lc-table {{ border-collapse:collapse; width:100%; font-size:.9rem; }}
  #lc-table th {{ position:sticky; top:0; background:var(--bg); text-align:left; padding:8px 12px;
     border-bottom:1px solid var(--border); font-size:.8rem; color:var(--muted); }}
  #lc-table td {{ padding:7px 12px; border-bottom:1px solid var(--border); }}
  #lc-table td.num {{ color:var(--muted); font-variant-numeric:tabular-nums; width:56px; }}
  #lc-table a {{ text-decoration:none; }} #lc-table a:hover {{ text-decoration:underline; }}
  .paid {{ font-size:.7rem; }}
</style>
<section class="coverage">
  <h2>LeetCode Coverage</h2>
  <p class="tag-line"><b>{c.get('total',0)}</b> problems solved on
     <a href="https://leetcode.com/u/{user}/" target="_blank" rel="noopener">leetcode.com/u/{user}</a>
     — the write-up cards below are the deep-dive ones. 已解 {c.get('total',0)} 題，下面是精選詳解。</p>
  <div class="stats">
    <div class="stat"><b>{c.get('total',0)}</b><span>solved</span></div>
    <div class="stat"><b class="c-easy">{c.get('easy',0)}</b><span>Easy</span></div>
    <div class="stat"><b class="c-medium">{c.get('medium',0)}</b><span>Medium</span></div>
    <div class="stat"><b class="c-hard">{c.get('hard',0)}</b><span>Hard</span></div>
  </div>
  <details class="solved">
    <summary>Show all {c.get('total',0)} solved problems ▸</summary>
    <div class="solved-controls">
      <input id="lc-search" type="search" placeholder="search title / number…">
      <select id="lc-diff">
        <option value="">All difficulty</option>
        <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
      </select>
      <span id="lc-count"></span>
    </div>
    <div class="solved-table-wrap">
      <table id="lc-table">
        <thead><tr><th>#</th><th>Problem</th><th>Difficulty</th></tr></thead>
        <tbody>
{rows_html}
        </tbody>
      </table>
    </div>
  </details>
</section>
<script>
(function() {{
  var q = document.getElementById('lc-search'),
      d = document.getElementById('lc-diff'),
      cnt = document.getElementById('lc-count'),
      rows = [].slice.call(document.querySelectorAll('#lc-table tbody tr'));
  function apply() {{
    var s = (q.value || '').toLowerCase(), df = d.value, n = 0;
    rows.forEach(function(r) {{
      var ok = (!df || r.dataset.d === df) && (!s || r.dataset.t.indexOf(s) >= 0);
      r.style.display = ok ? '' : 'none'; if (ok) n++;
    }});
    cnt.textContent = n + ' / ' + rows.length;
  }}
  q.addEventListener('input', apply); d.addEventListener('change', apply); apply();
}})();
</script>
"""


# ---- render page ------------------------------------------------------------
def render(cards):
    data = json.dumps(cards, ensure_ascii=False)
    n_lc = sum(1 for c in cards if c["domain"] == "leetcode")
    n_ai = sum(1 for c in cards if c["domain"] == "ai")
    avg_mastery = round(sum(c["mastery"] for c in cards) / len(cards), 1) if cards else 0
    all_tags = sorted({t for c in cards for t in c["tags"]})
    return TEMPLATE.format(
        user=GITHUB_USER, data=data, n_total=len(cards), n_lc=n_lc, n_ai=n_ai,
        avg=avg_mastery, tags_json=json.dumps(all_tags, ensure_ascii=False),
        solved_section=build_solved_section(),
    )


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{user} · Learning in Public</title>
<style>
  :root {{
    --bg:#ffffff; --fg:#1a1a2e; --muted:#5b5b76; --card:#f6f7fb; --border:#e3e4ee;
    --accent:#4f46e5; --easy:#0a9d6e; --medium:#c98a00; --hard:#d1495b;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0f1020; --fg:#e8e9f3; --muted:#a0a1bd; --card:#1a1b30; --border:#2a2c47;
             --accent:#8b85ff; --easy:#34d399; --medium:#fbbf24; --hard:#fb7185; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang TC","Noto Sans TC",sans-serif;
          background:var(--bg); color:var(--fg); }}
  a {{ color:var(--accent); }}
  .wrap {{ max-width:960px; margin:0 auto; padding:0 20px; }}
  header {{ padding:56px 0 32px; }}
  h1 {{ font-size:2.2rem; margin:0 0 6px; }}
  .tag-line {{ color:var(--muted); font-size:1.05rem; margin:0 0 20px; }}
  .btns a {{ display:inline-block; margin:0 10px 8px 0; padding:8px 16px; border:1px solid var(--border);
             border-radius:10px; text-decoration:none; background:var(--card); }}
  .stats {{ display:flex; gap:14px; flex-wrap:wrap; margin:22px 0 0; }}
  .stat {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:12px 18px; }}
  .stat b {{ font-size:1.5rem; display:block; }}
  .stat span {{ color:var(--muted); font-size:.85rem; }}
  .controls {{ position:sticky; top:0; background:var(--bg); padding:16px 0; border-bottom:1px solid var(--border);
               display:flex; gap:10px; flex-wrap:wrap; align-items:center; z-index:5; }}
  select, .controls input {{ padding:8px 10px; border-radius:9px; border:1px solid var(--border);
             background:var(--card); color:var(--fg); font-size:.92rem; }}
  .count {{ color:var(--muted); font-size:.88rem; margin-left:auto; }}
  .grid {{ padding:20px 0 60px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:18px 20px; margin:0 0 16px; }}
  .card-top {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }}
  .card h3 {{ margin:0; font-size:1.15rem; flex:1 1 auto; }}
  .pill {{ font-size:.72rem; padding:3px 9px; border-radius:20px; border:1px solid var(--border); color:var(--muted); }}
  .diff-easy {{ color:var(--easy); border-color:var(--easy); }}
  .diff-medium {{ color:var(--medium); border-color:var(--medium); }}
  .diff-hard {{ color:var(--hard); border-color:var(--hard); }}
  .domain {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
  .tags {{ margin:10px 0 0; }}
  .tags span {{ font-size:.74rem; color:var(--muted); margin-right:8px; }}
  .prompt {{ margin:12px 0 0; padding:12px 14px; border-left:3px solid var(--accent); background:rgba(127,127,180,.08);
             border-radius:0 8px 8px 0; }}
  .prompt small {{ color:var(--muted); text-transform:uppercase; letter-spacing:.06em; font-size:.68rem; }}
  .reveal-btn {{ margin:12px 0 0; padding:8px 16px; border:1px solid var(--accent); color:var(--accent);
                 background:none; border-radius:9px; cursor:pointer; font-size:.9rem; }}
  .reveal-btn:hover {{ background:var(--accent); color:#fff; }}
  .body {{ display:none; margin-top:14px; border-top:1px dashed var(--border); padding-top:6px; }}
  .body.open {{ display:block; }}
  .body pre {{ background:rgba(127,127,180,.12); padding:12px 14px; border-radius:9px; overflow-x:auto; }}
  .body code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.86em; }}
  .body pre code {{ font-size:.82rem; }}
  .body table {{ border-collapse:collapse; width:100%; margin:10px 0; font-size:.9rem; display:block; overflow-x:auto; }}
  .body th, .body td {{ border:1px solid var(--border); padding:6px 10px; text-align:left; }}
  .body blockquote {{ margin:10px 0; padding:8px 14px; border-left:3px solid var(--muted); color:var(--muted); }}
  footer {{ color:var(--muted); font-size:.85rem; padding:30px 0; border-top:1px solid var(--border); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Yuan-Hsuan Wen</h1>
    <p class="tag-line">Learning in Public — a living log of my CS / AI / LeetCode practice.<br>
       學習日誌：真實、持續、看得到成長。</p>
    <div class="btns">
      <a href="https://github.com/{user}" target="_blank" rel="noopener">GitHub ↗</a>
      <a href="https://github.com/{user}?tab=repositories" target="_blank" rel="noopener">Repositories ↗</a>
    </div>
    <p style="margin:18px 0 6px; color:var(--muted); font-size:.85rem;">Contribution activity</p>
    <img src="https://ghchart.rshah.org/{user}" alt="GitHub contribution graph for {user}"
         loading="lazy" style="max-width:100%; border:1px solid var(--border); border-radius:10px; padding:8px; background:var(--card);">
    <div class="stats">
      <div class="stat"><b>{n_total}</b><span>cards</span></div>
      <div class="stat"><b>{n_lc}</b><span>LeetCode</span></div>
      <div class="stat"><b>{n_ai}</b><span>AI notes</span></div>
      <div class="stat"><b>{avg}</b><span>avg mastery /5</span></div>
    </div>
  </header>

  {solved_section}

  <h2 style="font-size:1.4rem; margin:26px 0 0;">Deep-dive write-ups</h2>
  <p class="tag-line" style="margin:4px 0 0;">Problems I wrote up in full — the reasoning, not just the code.</p>

  <div class="controls">
    <select id="domain"><option value="">All domains</option>
      <option value="leetcode">LeetCode</option><option value="ai">AI Knowledge</option></select>
    <select id="difficulty"><option value="">All difficulty</option>
      <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></select>
    <select id="tag"><option value="">All topics</option></select>
    <input id="search" type="search" placeholder="search…" style="flex:0 1 160px;">
    <span class="count" id="count"></span>
  </div>

  <div class="grid" id="grid"></div>
  <footer>Built from markdown by <code>site/build.py</code> — static, no backend. Only <code>visibility:public</code> cards shown.</footer>
</div>

<script>
const CARDS = {data};
const TAGS = {tags_json};
const grid = document.getElementById('grid');
const $ = id => document.getElementById(id);

const tagSel = $('tag');
TAGS.forEach(t => {{ const o = document.createElement('option'); o.value = t; o.textContent = t; tagSel.appendChild(o); }});

const diffPill = d => d ? `<span class="pill diff-${{d}}">${{d}}</span>` : '';
const domLabel = d => d === 'ai' ? 'AI' : 'LeetCode';

function render(list) {{
  grid.innerHTML = list.map((c, idx) => `
    <div class="card">
      <div class="card-top">
        <h3>${{c.title}}</h3>
        <span class="pill domain">${{domLabel(c.domain)}}</span>
        ${{diffPill(c.difficulty)}}
        <span class="pill">mastery ${{c.mastery}}/5</span>
      </div>
      <div class="tags">${{c.tags.map(t => `<span>#${{t}}</span>`).join('')}}</div>
      <button class="reveal-btn" data-i="${{idx}}">Reveal ▸</button>
      <div class="body" id="body-${{idx}}">${{c.body_html}}</div>
    </div>`).join('') || '<p style="color:var(--muted)">No cards match.</p>';
  $('count').textContent = list.length + ' / ' + CARDS.length + ' cards';
  grid.querySelectorAll('.reveal-btn').forEach(b => b.onclick = () => {{
    const body = $('body-' + b.dataset.i);
    body.classList.toggle('open');
    b.textContent = body.classList.contains('open') ? 'Hide ▾' : 'Reveal ▸';
  }});
}}

function apply() {{
  const d = $('domain').value, diff = $('difficulty').value, tag = $('tag').value;
  const q = $('search').value.toLowerCase();
  render(CARDS.filter(c =>
    (!d || c.domain === d) && (!diff || c.difficulty === diff) &&
    (!tag || c.tags.includes(tag)) &&
    (!q || (c.title + ' ' + c.tags.join(' ')).toLowerCase().includes(q))
  ));
}}
['domain','difficulty','tag','search'].forEach(id => $(id).addEventListener('input', apply));
render(CARDS);
</script>
</body>
</html>"""


def main():
    cards = collect()
    OUT.write_text(render(cards), encoding="utf-8")
    print(f"Wrote {OUT}  ({len(cards)} public cards)")


if __name__ == "__main__":
    main()
