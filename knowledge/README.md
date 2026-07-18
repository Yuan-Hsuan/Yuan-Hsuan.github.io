# knowledge — my public learning notes 公開學習筆記

Durable notes from lectures / YouTube / reading — any domain (`domain:` in the
frontmatter says which: `ai`, `software-engineering`, …). Each note here, when
`visibility: public`, becomes **(1)** a card in the site's notes section and **(2)** a node
on the homepage **knowledge globe** — clustered by its `tags`, linked to related notes by
`[[wikilinks]]`. So this folder *is* my visual knowledge map, published.
這個資料夾就是我「發佈出去」的知識地圖。

(The CS224n concept notes live in their own repo — `../Standford-cs224n-nlp/notes/concepts/`
— and reach the site the same way at build time; new domains don't need new folders here,
just a `domain:` value.)

## When I learn something new 學到新東西時

1. Copy `_template.md` → `<topic>/<slug>.md`. (Make a topic folder only once you actually
   have a note for it — don't pre-invent categories. 有筆記了再開資料夾，別空想分類。)
2. Fill the frontmatter — **`tags` are the topics** that group the note on the globe; add `source`.
3. Write it: **Idea → Why → Example → Recall prompt**.
4. Link neighbours with `[[ai-…]]` ids so it joins the graph. 用 `[[ ]]` 連鄰居，讓它加入圖。
5. Set `visibility: public` when ready → the next site build puts it on the map.

- **Schema contract:** `../SCHEMA.md` (the one frontmatter all content shares).
- **How it reaches the site:** `site/build.py` reads this folder at build time (only
  `visibility: public` renders — the safety belt).
- **Private career notes live in `../../mind/`, never here.** 私人求職內容放 mind/，不放這。
