# Metric Definition: SaaS Monthly Churn Rate

**Version:** v1 (authoritative)  
**Domain:** SaaS subscription revenue  
**Status:** Active — all downstream results must be tagged `version: v1`

---

## The Authoritative Definition

**Monthly Logo Churn Rate** = (customers who churned in the period) ÷ (customers active at the start of the period)

### Numerator: Churned Customers

A customer counts as churned in a period if ALL of the following are true:

1. Their `subscription_end` date falls within `[period_start, period_end]` (inclusive).
2. Their `status` is `churned`.
3. Their `churned_at` date falls within `[subscription_end, subscription_end + 30 calendar days]` (inclusive).
4. They do not appear as a distinct `customer_id` with a new subscription starting within the same 30-day window.

**Grace period:** exactly 30 calendar days. Day 0 = `subscription_end`. Day 30 is still within the grace period. Day 31 is not.

### Denominator: Active Customers at Period Start

A customer counts in the denominator if their subscription was active on `period_start`:
`subscription_start ≤ period_start ≤ subscription_end`

One row per `customer_id` — if a customer has multiple subscriptions, they count once.

---

## What Does NOT Count

| Scenario | Counts? | Reason |
|---|---|---|
| Customer downgraded their plan | No | Downgrade ≠ churn. Tracked separately. |
| Customer churned outside grace window | No | Treated as lapsed, not churned. |
| Customer's subscription_end is before period_start | No | Out of period. |
| Row has missing_status flag | No | Excluded as data quality issue. |
| Row has missing_mrr flag | No | Excluded (no impact on logo churn but excluded for consistency). |
| Customer churned but later returned | No | Counted at time of churn event. Reactivations tracked separately. |

---

## Boundary Examples

### Example 1: Within grace — counts
- `subscription_end`: 2024-06-15  
- `churned_at`: 2024-07-15  
- `period`: June 2024  
- **Result: CHURNED** (July 15 = June 15 + 30 days — inclusive boundary)

### Example 2: Outside grace — does not count
- `subscription_end`: 2024-06-15  
- `churned_at`: 2024-07-16  
- `period`: June 2024  
- **Result: NOT CHURNED** (July 16 = day 31 — outside grace period)

### Example 3: Downgrade — does not count
- `status`: downgraded  
- `subscription_end`: 2024-06-20  
- `period`: June 2024  
- **Result: NOT CHURNED** (downgrades are not churn in v1)

### Example 4: Multi-subscription customer
- Customer has two rows: one active, one churned  
- **Result: NOT CHURNED** (customer still has an active subscription)

---

## Why These Choices

**Why 30-day grace period?**  
Month-to-month SaaS subscriptions commonly have a 30-day billing retry period. A customer whose card fails on day 1 but successfully charges on day 20 is not churned. We chose 30 days to match our billing provider's retry window. This is a different assumption from v3 (no grace) — the disagreement is intentional and documented.

**Why logo churn, not revenue churn?**  
The ops team uses customer count to drive support capacity planning. Revenue churn (v2–v4) is tracked for finance. Logo churn is the authoritative metric for operational decisions.

**Why exclude downgrades?**  
Downgrades are tracked as a separate revenue efficiency metric. Including them in churn would inflate the rate and conflate two distinct operational signals.

---

## Competing Definitions (Why They Disagree)

| Version | Key Difference | Who uses it |
|---|---|---|
| v1 (this) | Logo count, 30-day grace, no downgrades | Ops, CS |
| v2 | Revenue-weighted, 30-day grace, no downgrades | Finance (conservative) |
| v3 | Revenue-weighted, no grace, includes downgrades ≥20% | Finance (aggressive) |
| v4 | Net revenue (churn minus expansion), no grace | Exec reporting |

The reconciliation table (`evals/reconciliation.md`) shows how each definition handles every edge case.

---

## Version History

| Version | Date | Change |
|---|---|---|
| v1 | 2024-01-01 | Initial definition. 30-day grace, logo count, no downgrades. |
