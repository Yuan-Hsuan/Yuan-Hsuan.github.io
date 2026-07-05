---
id: lc-remove-nth-node-from-end-of-list
domain: leetcode
title: 19. Remove Nth Node From End of List
tags: [two-pointers]
difficulty: medium
status: review
mastery: 3
importance: 3
optimal: true
source: https://leetcode.com/problems/remove-nth-node-from-end-of-list/
visibility: public
---

## 🎙️ Naive Solution
The obvious approach is two passes: first walk the whole list to count its length `L`, then walk
again to the `(L - n)`-th node to unlink the target. It works, but it touches the list twice.

## 🚀 Pitch

### The Bottleneck Observation
"Nth from the end" is really a fixed **gap** from the tail. If two pointers keep a constant distance
of `n` between them, then when the leading pointer falls off the end, the trailing pointer is sitting
exactly where we need it — no length count required.

### The Strategy: Two Pointers with a Fixed Gap
Anchor a **dummy head** before the list so deleting the real head needs no special case. Advance the
`fast` pointer `n + 1` steps first, then move `fast` and `slow` together. When `fast` becomes null,
`slow` stops right before the node to remove.

### The Precise Calculation / Execution
- `fast` leads by `n + 1` from `dummy`, so `slow` lands on the predecessor of the target.
- Delete safely: mark the target, relink `slow->next` past it, then free the node.
- Return `dummy.next`.

## 🛠️ Optimization
```c++
class Solution {
public:
    ListNode* removeNthFromEnd(ListNode* head, int n) {
        ListNode dummy(0, head);
        ListNode* fast = &dummy;

        for (int i = 0; i <= n; i++) {
            fast = fast->next;
        }

        ListNode* slow = &dummy;

        while (fast) {
            fast = fast->next;
            slow = slow->next;
        }

        // 🌟 安全的刪除流程：先標記，再接線，最後釋放
        ListNode* toDelete = slow->next;
        slow->next = slow->next->next;
        delete toDelete;

        return dummy.next;
    }
};
```
