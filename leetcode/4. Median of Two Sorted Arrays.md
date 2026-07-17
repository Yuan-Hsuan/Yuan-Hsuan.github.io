---
id: lc-median-of-two-sorted-arrays
domain: leetcode
title: 4. Median of Two Sorted Arrays
tags: [binary-search]
difficulty: hard
status: review
mastery: 5
importance: 5
optimal: true
source: https://leetcode.com/problems/median-of-two-sorted-arrays/
visibility: public
---

## 🎙️ Naive Solution
The straightforward approach merges the two sorted arrays into one and reads off the middle
element(s). That costs O(M + N) time and space — but the problem asks for O(log(M + N)), so we
need something sharper.

## 🚀 Pitch

### The Bottleneck Observation
**Find a perfect partition across both arrays (尋找完美的跨陣列切分線).** The median fundamentally
divides a dataset into two equal halves. In a single sorted array we simply cut in the center.
Since this problem gives us two arrays, our goal shifts to finding a perfect **partition (cut)**
across both arrays, such that the left half contains the same number of elements as the right half,
and all left elements are strictly smaller than the right elements.

### The Strategy: Binary Search on the Cut (刀口理論)
**The "Cut Theory" on the smaller array (在較短陣列應用刀口理論).** Because the total number of
elements in the left half is fixed, making a cut in Array A strictly determines the cut in Array B.
By applying Binary Search on the smaller array of length `m`, a cut simply represents the **number
of elements** we take for the left half. Our search space is strictly `[0, m]`, which mathematically
guarantees an O(log(min(M, N))) time complexity.

### The Precise Calculation / Execution
**Cross-checking the boundaries (交叉驗證切分線的合法性).** To verify a partition is correct, we only
need to cross-check the four elements immediately adjacent to the cuts: `L1 <= R2` and `L2 <= R1`.
If `L1 > R2`, our cut in A is too far right, so we move left. This monotonic property is exactly why
Binary Search works perfectly here.

## 🛠️ Optimization
```c++
class Solution {
public:
    double findMedianSortedArrays(vector<int>& nums1, vector<int>& nums2) {
        if (nums1.size() > nums2.size()) {
            return findMedianSortedArrays(nums2, nums1);
        }

        int m = nums1.size();
        int n = nums2.size();

        // 左半邊長度的「魔法公式」
        int half = (m + n + 1) / 2;

        int left = 0;
        // 切分線代表我們為左半邊拿取的「元素數量」。因為我們可以拿 0 到 m 個元素，搜尋空間嚴格界定在 [0, m]。
        // 這優雅地解釋了為什麼我們的二分搜尋是從 right = m 而非 m - 1 開始
        int right = m;
        while (left <= right) {
            int cut1 = left + (right - left) / 2;
            int cut2 = half - cut1;

            // 建立 4 根柱子 (L1, R1, L2, R2)
            int L1 = (cut1 == 0) ? INT_MIN : nums1[cut1 - 1];
            int R1 = (cut1 == m) ? INT_MAX : nums1[cut1];
            int L2 = (cut2 == 0) ? INT_MIN : nums2[cut2 - 1];
            int R2 = (cut2 == n) ? INT_MAX : nums2[cut2];

            if (L1 <= R2 && L2 <= R1) {
                if ((m + n) % 2 == 1) {
                    return max(L1, L2);
                } else {
                    return (max(L1, L2) + min(R1, R2)) / 2.0;
                }
            } else if (L1 > R2) {
                right = cut1 - 1; // nums1 切太右邊了，往左縮
            } else {
                left = cut1 + 1;  // nums1 切太左邊了，往右擴
            }
        }

        return -1.0;
    }
};
```
