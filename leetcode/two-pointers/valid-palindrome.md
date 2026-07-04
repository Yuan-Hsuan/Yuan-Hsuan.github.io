---
id: lc-valid-palindrome
domain: leetcode
title: Valid Palindrome
tags: [two-pointers, string]
difficulty: easy
status: new
mastery: 0
last_reviewed:
next_review:
source: https://leetcode.com/problems/valid-palindrome/
visibility: public
---

## Problem
Given a string, return True if it reads the same forward and backward, considering only
alphanumeric characters and ignoring case.

## Pattern insight
**Two pointers from both ends, walking inward.** 左右兩個指標往中間夾。
No extra string needed — compare `s[l]` and `s[r]`, skip non-alphanumeric, move inward.
Anytime you compare a sequence with its mirror, two-pointers beats building a reversed copy (O(1) space).

## Solution
```python
def is_palindrome(s: str) -> bool:
    l, r = 0, len(s) - 1
    while l < r:
        while l < r and not s[l].isalnum(): l += 1
        while l < r and not s[r].isalnum(): r -= 1
        if s[l].lower() != s[r].lower():
            return False
        l += 1; r -= 1
    return True
```

## Complexity
- Time **O(n)**, Space **O(1)** — no reversed copy.

## Recall prompt
> Check a palindrome ignoring punctuation/case with O(1) space — what technique, and how do you
> handle the non-alphanumeric chars? (two pointers inward; inner while-loops skip non-alnum)
