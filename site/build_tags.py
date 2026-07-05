#!/usr/bin/env python3
"""
build_tags.py — enrich site/solved.json with each problem's topic tags.

LeetCode's PUBLIC GraphQL returns topicTags per problem (no login needed), so we
fetch tags for every solved problem and write site/problems.json — the data source
for the big knowledge-graph render. Polite: small delay, retries, resumable.

    python3 site/build_tags.py
"""
from __future__ import annotations
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOLVED = ROOT / "site" / "solved.json"
OUT = ROOT / "site" / "problems.json"
GQL = "https://leetcode.com/graphql"
Q = ("query q($s:String!){question(titleSlug:$s){questionFrontendId title "
     "difficulty topicTags{slug}}}")


def fetch_tags(slug: str):
    body = json.dumps({"query": Q, "variables": {"s": slug}}).encode()
    req = urllib.request.Request(GQL, data=body, headers={
        "Content-Type": "application/json", "User-Agent": "Mozilla/5.0",
        "Referer": "https://leetcode.com"})
    with urllib.request.urlopen(req, timeout=20) as r:
        q = json.loads(r.read()).get("data", {}).get("question") or {}
    return [t["slug"] for t in q.get("topicTags", [])]


def main():
    solved = json.loads(SOLVED.read_text())["problems"]
    done = {p["slug"]: p for p in json.loads(OUT.read_text())} if OUT.exists() else {}
    out = []
    for i, p in enumerate(solved):
        slug = p["slug"]
        if slug in done and done[slug].get("tags"):
            out.append(done[slug]); continue
        tags = []
        for attempt in range(3):
            try:
                tags = fetch_tags(slug); break
            except Exception as e:
                time.sleep(0.5 * (attempt + 1))
        out.append({"id": p["id"], "title": p["title"], "slug": slug,
                    "difficulty": p["difficulty"], "tags": tags})
        if i % 25 == 0:
            OUT.write_text(json.dumps(out, ensure_ascii=False))
            print(f"{i+1}/{len(solved)} …", flush=True)
        time.sleep(0.08)
    OUT.write_text(json.dumps(out, ensure_ascii=False))
    tagged = sum(1 for p in out if p["tags"])
    print(f"Wrote {OUT}  ({len(out)} problems, {tagged} with tags)")


if __name__ == "__main__":
    main()
