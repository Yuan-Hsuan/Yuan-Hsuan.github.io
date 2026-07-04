# site/ — static site generator (Phase 3)

`build.py` (coming in Phase 3) walks `../leetcode/` and `../ai-knowledge/`, reads the
frontmatter of every `visibility: public` file, and writes `../index.html` + `assets/`.

Design constraints:
- **Static only** — output is plain HTML/CSS/JS. No backend, no DB. GitHub Pages serves it free.
- **Interactive practice area** — LeetCode section is a browsable/filterable practice block
  (filter by pattern & difficulty; recall-then-reveal), not just a static list.
- **Safety belt** — only `visibility: public` files are ever rendered.

Run:
```
python site/build.py
```
