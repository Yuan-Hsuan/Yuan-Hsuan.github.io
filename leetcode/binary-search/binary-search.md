---
id: lc-binary-search
domain: leetcode
title: Binary Search (the template)
tags: [binary-search, array]
difficulty: easy
status: new
mastery: 0
last_reviewed:
next_review:
source: https://leetcode.com/problems/binary-search/
visibility: public
---

## Problem
Given a sorted array and a target, return its index or -1. Must be O(log n).

## Pattern insight
**Halve the search space each step.** 每一步砍一半。
The real skill isn't this problem — it's the **template** you reuse for every "find the boundary"
variant (first/last position, search-insert, rotated array, or *any* monotonic answer space).
重點不是這題，是這個可以套到所有「找邊界」變體的模板。

## Solution
```python
def search(nums: list[int], target: int) -> int:
    lo, hi = 0, len(nums) - 1        # inclusive bounds
    while lo <= hi:
        mid = (lo + hi) // 2         # in Python no overflow; in C use lo + (hi-lo)//2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

## Complexity
- Time **O(log n)**, Space **O(1)**.

## The two traps 兩個坑
1. **Bounds consistency:** `hi = len-1` with `while lo <= hi` (inclusive). Mixing `hi = len` with `<=` loops forever.
2. **Monotonic thinking:** binary search applies whenever the predicate "is the answer ≥ x?" is monotonic — not only literal sorted arrays.

## Recall prompt
> Write binary search and state the invariant that keeps `lo`/`hi` consistent.
> (inclusive bounds + `while lo <= hi`; each step discards the half that can't contain the target)
