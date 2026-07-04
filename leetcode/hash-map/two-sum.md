---
id: lc-two-sum
domain: leetcode
title: Two Sum
tags: [hash-map, array]
difficulty: easy
status: learning
mastery: 3
last_reviewed: 2026-07-04
next_review: 2026-07-08
source: https://leetcode.com/problems/two-sum/
visibility: public
---

## Problem
Given an array `nums` and a target `t`, return the indices of the two numbers that add up to `t`.
Exactly one solution exists; can't reuse an element.

## Pattern insight
**Complement lookup with a hash map.** 用雜湊表存「還缺哪個數」。
As you scan, for each `x` you need `t - x`. Instead of searching the rest of the array (O(n)),
remember every number you've already seen in a hash map, so the lookup is O(1).
一邊掃、一邊把看過的數丟進 map；要找的補數直接 O(1) 查表，不用回頭再掃一次。

## Solution
```python
def two_sum(nums: list[int], t: int) -> list[int]:
    seen = {}                      # value -> index
    for i, x in enumerate(nums):
        if t - x in seen:          # complement already seen?
            return [seen[t - x], i]
        seen[x] = i
    return []
```

## Complexity
- Time **O(n)** — one pass.
- Space **O(n)** — the hash map.
- Key trade: spend O(n) memory to turn an O(n) inner search into O(1). 用空間換時間。

## Recall prompt
> Two Sum in one pass — what do you store in the map, and what do you look up for each element?
> (store: seen value→index; look up: `target - current`)
