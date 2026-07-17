---
id: lc-palindrome-number
domain: leetcode
title: 9. Palindrome Number
tags: [math]
difficulty: easy
status: review
mastery: 2
importance: 2
optimal: true
source: https://leetcode.com/problems/palindrome-number/
visibility: public
---

## 🎙️ Naive Solution
The first idea that comes to mind is to convert the number into a string and check whether that
string is a palindrome. But this requires extra, non-constant space just to build the string.

## 🚀 Pitch

### The Bottleneck Observation
I want to optimize for strictly **O(1)** space using pure math to read digits from both ends. The
main challenge is that while getting digits from the right side is trivial with `% 10`, it is hard
to extract the very first (leftmost) digit of an integer.

### The Strategy: Reversing the Right Half
By the definition of a palindrome, the left half perfectly mirrors the right half. Since pulling
digits off the right is easy with modulo 10, the idea is to continuously pop the trailing digits to
build a **reversed right half**, and then compare it against the remaining left half.

### The Precise Calculation / Execution
Before doing that we need a few defensive checks. We return `false` early if the number is negative
or ends in a zero, because reversing a trailing zero would silently drop a digit from the right half.
Finally, if the total length is odd, we simply discard the middle digit when comparing the two
halves (`x == reverse / 10`).

## 🛠️ Optimization
```c++
class Solution {
public:
    bool isPalindrome(int x) {

        if (x == 0) return true;
        if (x < 0 || x % 10 == 0) return false;

        int reverse = 0;

        while (x > reverse) {
            reverse = reverse * 10 + x % 10;
            x /= 10;
        }
        // 3. 奇偶合併處理
        return x == reverse || x == reverse / 10;
    }
};
```
