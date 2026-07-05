#!/usr/bin/env python3
"""
build_solved.py — turn a raw LeetCode API dump into site/solved.json.

The public site shows a "LeetCode Coverage" panel (total solved + a filterable list).
That data comes from LeetCode's own `GET https://leetcode.com/api/problems/all/`, which
returns the full problem set annotated with the logged-in user's status ("ac" = solved).

Refresh flow (run in YOUR OWN terminal so the cookie stays local):

    curl -s 'https://leetcode.com/api/problems/all/' \
      -H 'Cookie: LEETCODE_SESSION=<your session cookie>' -o ~/leetcode-all.json
    python3 site/build_solved.py ~/leetcode-all.json
    python3 site/build.py            # rebuild index.html

solved.json is committed; the raw dump and the cookie are NOT.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "solved.json"
LEVEL = {1: "easy", 2: "medium", 3: "hard"}


def main(raw_path: str) -> None:
    data = json.loads(Path(raw_path).expanduser().read_text(encoding="utf-8"))
    pairs = data.get("stat_status_pairs", [])
    solved = []
    for p in pairs:
        if p.get("status") != "ac":
            continue
        s = p["stat"]
        solved.append({
            "id": s["frontend_question_id"],
            "title": s["question__title"],
            "slug": s["question__title_slug"],
            "difficulty": LEVEL.get(p["difficulty"]["level"], ""),
            "paid": bool(p.get("paid_only")),
        })
    solved.sort(key=lambda x: x["id"])
    counts = {
        "total": len(solved),
        "easy": sum(1 for x in solved if x["difficulty"] == "easy"),
        "medium": sum(1 for x in solved if x["difficulty"] == "medium"),
        "hard": sum(1 for x in solved if x["difficulty"] == "hard"),
    }
    payload = {
        "username": data.get("user_name", ""),
        "counts": counts,
        "problems": solved,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wrote {OUT}  ({counts['total']} solved: "
          f"{counts['easy']}E / {counts['medium']}M / {counts['hard']}H)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 site/build_solved.py <path-to-leetcode-all.json>")
    main(sys.argv[1])
