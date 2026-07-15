---
id: lc-advanced-sql-patterns
domain: leetcode
title: Advanced SQL Cheatsheet — 進階 SQL 速查
tags: [sql, database, window-functions, joins]
difficulty: hard
status: learning
mastery: 1
visibility: public
source: https://leetcode.com/studyplan/top-sql-50/
---

<!-- ⚠️ PUBLISH CHECKLIST (before the first `## `, so build.py drops it — will NOT show on the site):
  To ship: 1) cd ~/github/Yuan-Hsuan.github.io && python3 site/build.py
           2) verify index.html renders it + the knowledge graph picked up `tags:`
           3) commit + push  → live site + contribution calendar refresh (the chain rule)
  KNOWLEDGE MAP = auto-built from `tags:` + [[wikilinks]]; keep tags meaningful, it self-updates.
  Adding problems: easy/conceptual → §1 Quick reference; hard → a pattern (when → template → example → gotcha).
  SPLIT WHEN IT GROWS: once window-function patterns land, split into sql-joins / sql-window-functions / sql-gotchas. -->

## What this is
A cheat sheet for the hard / gotcha end of SQL (**MySQL**). Basics assumed. Each pattern follows:
**when → template → example → gotcha**.

## Index
1. Quick reference — joins, `ON` vs `WHERE`, functions
2. Top-N per group
3. Anti-join — rows in A missing from B
4. Sargable dates — index-friendly comparisons
5. *Coming next: window functions · gaps & islands · pivot · Nth highest / median · recursive CTE*

---

## 1. Quick reference

### JOIN types — which rows survive, and where `ON` vs `WHERE` differ

| Join | Keeps | Unmatched rows | Filter in `ON` vs `WHERE` |
|---|---|---|---|
| `INNER JOIN` (`JOIN`) | only rows matched in both | dropped | **same result** |
| `LEFT JOIN` | all left + matched right | right cols `= NULL` | `ON` |
| `RIGHT JOIN` | all right + matched left | left cols `= NULL` | `ON` |
| `FULL OUTER JOIN` | all from both (MySQL: `LEFT ∪ RIGHT` via `UNION`) | either side |  `ON` |

- Explicit `JOIN … ON` **beats** comma-join `FROM a, b WHERE …`: same speed, but it separates join-logic from filters, avoids accidental cross joins, and comma-syntax can't do outer joins.
- **`ON` vs. `WHERE`**: `WHERE` drops the `NULL` rows → silently acts like INNER;keep it in `ON`. OUTER join 的過濾放 `WHERE` 會把沒配到的 `NULL` row 濾掉 → **默默變回 INNER join**；要保留就放 `ON`。

### Functions
- `CHAR_LENGTH(s)` → number of **characters** (unicode-safe) · `LENGTH(s)` → number of **bytes**
  （一個中文字 = 1 char 但 3 bytes；算長度用 `CHAR_LENGTH`）
- `COALESCE(a, b, …)` → first non-`NULL` · `IFNULL(a, b)` (MySQL) / `ISNULL(a, b)` (T-SQL)
- `DATEDIFF(a, b)` → **`a − b`, in days** (positive when `a` is the later date)
- `DATE_ADD(d, INTERVAL n DAY)` → **`d + n`** · `DATE_SUB(d, INTERVAL n DAY)` → **`d − n`**
- strings: `CONCAT` · `SUBSTRING` · `UPPER/LOWER` · `TRIM` · `REPLACE`

---

## 2. Top-N per group
**When:** "top 3 salaries per department", "top 2 per category", "latest N per user".

**Template:**
```sql
WITH ranked AS (
  SELECT *, DENSE_RANK() OVER (PARTITION BY group_col ORDER BY val DESC) AS rk
  FROM t
)
SELECT * FROM ranked WHERE rk <= N;
```

**Example — LC 185 Department Top Three Salaries:**
```sql
SELECT d.name AS Department, e.name AS Employee, e.salary AS Salary
FROM (
  SELECT *, DENSE_RANK() OVER (PARTITION BY departmentId ORDER BY salary DESC) AS rk
  FROM Employee
) e
JOIN Department d ON d.id = e.departmentId
WHERE e.rk <= 3;
```

**⚠️ Gotcha — pick the right ranking function:**
- `ROW_NUMBER()` → exactly N rows (ties broken arbitrarily)
- `RANK()` → gaps after ties (1, 1, 3, …)
- `DENSE_RANK()` → top-N **distinct** values (1, 1, 2, …) ← 「前 3 高**薪水**」通常是這個

---

## 3. Anti-join — rows in A missing from B
**When:** "visited but never transacted", "in A but not in B", "has no matching row".

**Three ways (prefer the NULL-safe first two):**
```sql
-- 1) LEFT JOIN ... IS NULL  (clear, safe)
SELECT v.customer_id, COUNT(*) AS count_no_trans
FROM Visits v
LEFT JOIN Transactions t ON t.visit_id = v.visit_id
WHERE t.transaction_id IS NULL
GROUP BY v.customer_id;

-- 2) NOT EXISTS  (usually fastest on large data)
SELECT v.customer_id, COUNT(*) AS count_no_trans
FROM Visits v
WHERE NOT EXISTS (SELECT 1 FROM Transactions t WHERE t.visit_id = v.visit_id)
GROUP BY v.customer_id;

-- 3) NOT IN  ⚠️ NULL trap
-- ... WHERE visit_id NOT IN (SELECT visit_id FROM Transactions)
```
**⚠️ Gotcha:** `NOT IN (subquery)` returns **zero rows if the subquery yields any `NULL`** (the whole
predicate goes UNKNOWN). Prefer `NOT EXISTS` or `LEFT JOIN … IS NULL`. LC 1581.
（`NOT IN` 只要子查詢冒出一個 `NULL` 就回 0 筆——別用。）

---

## 4. Sargable dates — keep comparisons index-friendly
**When:** "compare each row to the previous day / a shifted date" (LC 197 Rising Temperature).

**Rule:** never wrap the column you join/filter on inside a function — it blocks the index.
```sql
-- ✅ sargable: w1.recordDate stays a bare column → index seek
--    ON-condition means  w1 = w2 + 1 day   (w1 is the day AFTER w2)
SELECT w1.id
FROM Weather w1
JOIN Weather w2 ON w1.recordDate = DATE_ADD(w2.recordDate, INTERVAL 1 DAY)
WHERE w1.temperature > w2.temperature;

-- 🐢 not sargable: DATEDIFF wraps BOTH columns → full scan
--    DATEDIFF(w1.recordDate, w2.recordDate) = 1   means   w1 − w2 = 1 day
```
**Who-minus-who (memorize):**
- `DATEDIFF(a, b)` = **`a − b`** → `DATEDIFF(w1, w2) = 1` means **w1 is 1 day after w2**.
- `DATE_ADD(w2, INTERVAL 1 DAY)` = **`w2 + 1 day`** → `w1 = DATE_ADD(w2, …)` is the *same* condition
  (w1 is the day after w2), just written so `w1.recordDate` stays index-friendly.

**⚠️ Gotcha:** `DATEDIFF` is correct and readable but **not sargable**. Shift one side with
`DATE_ADD/DATE_SUB` so the target column stays bare. Also use `INNER JOIN` here — a `LEFT JOIN`
whose `WHERE` compares the right table behaves like INNER anyway.

---

## Coming next
window functions (running total / `LAG`-`LEAD`) · gaps & islands · pivot (conditional aggregation) ·
Nth highest / median · deduplication · recursive CTE
</content>
