---
id: lc-maximum-points-you-can-obtain-from-cards
domain: leetcode
title: 1423. Maximum Points You Can Obtain from Cards
tags: [sliding-window]
difficulty: medium
status: review
mastery: 3
importance: 3
optimal: true
source: https://leetcode.com/problems/maximum-points-you-can-obtain-from-cards/
visibility: public
---

## 🎙️ Naive Solution
Since we can only take cards from the extreme ends, a naive recursive approach checking all paths
would take **O(2^k)** time. Even with memoization, it would take **O(k^2)** time and extra space.

## 🚀 Pitch

### The Bottleneck Observation
The core insight is much easier than search. It fundamentally comes down to an **allocation
problem**: since we are forced to pick exactly `k` cards, the only question is how we distribute that
quota between the left side and the right side.

### The Strategy: Sliding Window
Use a **Sliding Window** over the ends. My initial window considers taking all `k` cards strictly
from the left side of the array, so I calculate the sum of these first `k` elements. If `k` equals
the total number of cards, I can return this sum immediately.

### The Precise Calculation / Execution
Then I slide the window. In each step I 'drop' the rightmost card from my left selection and 'pick
up' one card from the right end of the array. I repeat this process `k` times, updating the maximum
score found so far.

## 🛠️ Solution
**Complexity:**

- The Time Complexity is exactly **O(k)**, because we only iterate up to `k` times.
- The Space Complexity is **O(1)**, since we only maintain a few integer variables for the running
  sum and maximum score.
