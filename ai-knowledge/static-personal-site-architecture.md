---
id: static-site-architecture
domain: software-engineering
title: Static Personal Site Architecture 靜態個人網頁架構
tags: [web, static-site, frontend, zero-dependency, build-tooling]
mastery: 2
source: built my own site (Yuan-Hsuan.github.io/site/build.py)
visibility: public
---

## 1. Core Concept: Shift Compute to Build Time
A **static personal site** ships a pre-built `index.html` (HTML/CSS/JS) served directly by a file host — no server-side logic, no database queries at runtime. 

* **The Core Move:** Take the work a backend would normally do on **every request** (read files, fetch data, assemble the page) and **do it once at build time**, baking the results into a static file.
* **The Result:** 線上零伺服器邏輯 (zero server logic in production) → fast, free, and practically impossible to bring down.

## 2. The Architectural Lifecycle
分清楚「誰在什麼時候跑」是理解整個架構的關鍵.

| Phase | Environment | Core Action |
| :--- | :--- | :--- |
| **1. Build** | Local (Laptop) | `build.py` reads Markdown + GitHub data, writes `index.html`. Runs once then exits — **neither frontend nor backend**. |
| **2. Serve** | CDN / GitHub Pages | Ships the static files to the client. Zero compute, effectively infinite scale. |
| **3. Runtime** | Client Browser | Parses HTML/CSS, runs JavaScript for interaction + animation. **This is the pure frontend.** |

## 3. Implementation Details
The site is built on a philosophy of minimizing external dependencies and matching the tool's weight to the problem size.

### Build-Time: Zero-Dependency Python
The generator (`build.py`) uses **only Python's standard library** (只依賴標準函式庫) — nothing to install.
* **The Trick:** An `f-string` *is* a template engine. A template engine just fills placeholders. `f"<h1>{name}</h1>"` achieves exactly what Jinja2's `<h1>{{name}}</h1>` does, making an external library unnecessary overhead.
* **The Trade-off:** For a small, stable, single-author site, an external dependency is a liability (zero-dep = zero maintenance). At a larger scale, this flips — mature libraries save the cost of reinventing the wheel. It's a system design judgment call, not a dogma.

### Runtime: Vanilla JS + Canvas Rendering
No React/Vue — built purely on browser-native APIs.
* **Vanilla JS (「原味」JavaScript):** Plain browser JavaScript with no framework. It matches the spirit of the build step: use the language directly, install nothing.
* **Canvas vs. DOM (Immediate vs. Retained Mode):** The knowledge globe is drawn on a `<canvas>` using **immediate-mode rendering**. You paint pixels every frame (`ctx.arc()`, `ctx.stroke()` — 用 JS 下指令畫圓、畫線). 
* **Performance:** Compared to animating dozens of HTML `<div>` elements (**retained mode**, where the browser manages a live DOM tree), canvas is far cheaper for **scenes that fully redraw each frame**, like a spinning graph of dots and edges.

```javascript
const ctx = canvas.getContext('2d');   // the "brush"
ctx.arc(x, y, 5, 0, 6.28);             // draw a circle (one node)
ctx.stroke();                          // draw a line (an edge)

```

## 4. The Core Trade-off: Static vs. Dynamic

The whole distinction comes down to **when** the compute happens and **where** the state lives.

| Feature | Static Website | Dynamic (Active) Website |
| --- | --- | --- |
| **Compute Phase** | Build time (Ahead-of-Time) | Request time (Just-In-Time) |
| **Server Role** | Pure I/O — distributes pre-baked files via CDN | Compute node — intercepts requests, runs logic |
| **System State** | Client-side only (browser memory / DOM) | Server-side (DB, session) + client-side |
| **Failure Domains** | Minimal — no backend logic to crash | High — DB timeouts, memory leaks, traffic spikes |
| **Content Updates** | Requires re-running the build pipeline | Instant — changes the moment a DB record changes |

**Summary:**

* **Static Architecture** trades **real-time flexibility** for **stability and speed**. Fixing a typo means running `build.py` again and pushing the new file.
* **Dynamic Architecture** trades **compute overhead** for **instant flexibility**. Fixing a typo is just a DB-row update, and the next visitor sees it immediately.