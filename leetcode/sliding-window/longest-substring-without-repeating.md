---
id: lc-longest-substring-no-repeat
domain: leetcode
title: Longest Substring Without Repeating Characters
tags: [sliding-window, hash-map, string]
difficulty: medium
status: new
mastery: 0
last_reviewed:
next_review:
source: https://leetcode.com/problems/longest-substring-without-repeating-characters/
visibility: public
---

## Problem
Given a string, find the length of the longest substring with no repeating characters.

## Pattern insight
**Sliding window with a last-seen map.** 可變長度的滑動視窗 + 記錄每個字最後出現位置。
Grow the window on the right; when the right char was seen *inside* the current window, jump the
left edge past its previous position. The window always holds a valid (unique) substring.
視窗右邊擴張，遇到重複就把左邊界跳到「上次出現位置的下一格」。

## Solution
```python
def length_of_longest_substring(s: str) -> int:
    last = {}          # char -> last index seen
    left = 0
    best = 0
    for right, c in enumerate(s):
        if c in last and last[c] >= left:
            left = last[c] + 1     # shrink window past the duplicate
        last[c] = right
        best = max(best, right - left + 1)
    return best
```

## Complexity
- Time **O(n)** — each index enters/leaves the window once.
- Space **O(min(n, charset))**.

## Recall prompt
> Longest substring with all-unique chars — window type and the key move on a duplicate?
> (variable-size sliding window; on a repeat inside the window, jump `left` to `last[c]+1`)
