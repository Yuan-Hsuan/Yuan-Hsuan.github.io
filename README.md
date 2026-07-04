# Yuan-Hsuan Wen — Learning in Public 學習日誌

> A living log of my CS / AI / LeetCode practice.
> 這不是一個假裝完整的作品集，而是我實際在學、在練的公開紀錄。

**Live site → https://yuan-hsuan.github.io** (built from this repo by GitHub Pages)

This repo is the **public** half of a two-repo system:

| repo | visibility | holds |
|------|-----------|-------|
| **`Yuan-Hsuan.github.io`** (this one) | 🌐 public | the HR-facing site + LeetCode solutions + AI notes |
| `mind` | 🔒 private | resume, behavioral (BQ) stories, personal review state |

Both repos share one metadata contract — see [`SCHEMA.md`](./SCHEMA.md).

## What's here 內容

- **`leetcode/`** — solved problems grouped by pattern. Each is one markdown file with
  the problem, the pattern insight, my solution, and complexity. Steady commits here also
  grow my GitHub contribution graph. 持續 commit = 綠格 + 練習紀錄。
- **`ai-knowledge/`** — my AI / ML concept notes (some grown from Stanford CS224n).
- **`site/`** — the static site generator: walks `leetcode/` + `ai-knowledge/` and builds
  `index.html`. No backend, no database — pure static, served free by GitHub Pages.

## Why "learning in public"？

I'm early in my journey and don't have polished shipped projects yet — so instead of a fake
empty portfolio, this site shows the real thing: **consistency, growth, and how I think.**
An honest practice log an HR can actually browse beats a hollow shell. 誠實的練習日誌 > 空殼作品集。

## How the site is built 網站怎麼產生

```
python site/build.py        # reads visibility:public files → writes index.html
```

The generator only renders files marked `visibility: public` (see SCHEMA.md safety belt).
