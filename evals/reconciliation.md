# Reconciliation Table

**Domain:** SaaS Monthly Churn Rate  
**Period used for examples:** June 2024  
**Rows:** Edge cases  
**Columns:** Five competing definitions (v1–v4 + "Legacy Dashboard")

---

## Legend

- **C** = Counts as churn
- **–** = Does not count
- **Partial** = Counts partial value (e.g., only the MRR delta)

---

## Edge Case Matrix

| # | Edge Case | v1 Logo Churn | v2 Gross Rev (no downgrades) | v3 Gross Rev (+downgrades ≥20%) | v4 Net Rev Churn | Legacy Dashboard |
|---|---|---|---|---|---|---|
| 1 | Customer churned on day 30 after sub_end (grace boundary) | **C** | **C** | – (no grace in v3) | – (no grace in v4) | **C** |
| 2 | Customer churned on day 31 after sub_end | – | – | – | – | **C** (legacy ignores grace) |
| 3 | Customer downgraded by 25% MRR | – | – | **Partial** (MRR delta) | **Partial** (MRR delta) | **C** (legacy treats all downgrades as churn) |
| 4 | Customer downgraded by 15% MRR | – | – | – (below 20% threshold) | – | **C** (legacy treats all downgrades as churn) |
| 5 | Customer downgraded by exactly 20% MRR | – | – | **Partial** (≥20% counts) | **Partial** | **C** |
| 6 | Customer expanded (upsell +$500 MRR) | – | – | – | **Offsets** (reduces numerator) | – |
| 7 | Customer has null/missing MRR | – (excluded) | – (excluded) | – (excluded) | – (excluded) | **C** (legacy includes with $0 MRR) |
| 8 | Customer has missing_status flag | – (excluded) | – (excluded) | – (excluded) | – (excluded) | **C** (legacy uses raw data) |
| 9 | Subscription ended last day of prior month | – (outside period) | – (outside period) | – (calendar month boundary) | – | **C** (legacy uses 30-day rolling window) |
| 10 | Customer with two active subscriptions (multi-plan) | – (still active) | – (still active) | – (still active) | – (still active) | **C** (legacy counts per subscription, not per customer) |
| 11 | Duplicate row from retry storm | – (deduped) | – (deduped) | – (deduped) | – (deduped) | **C** (legacy counts each row) |
| 12 | Timezone-shifted date (Source A, UTC-5 offset) | Correct (pipeline normalizes to UTC) | Correct | Correct | Correct | Wrong (legacy uses raw timestamp) |
| 13 | Churned customer reactivated same month | Counts at churn time | Counts at churn time | Counts at churn time | Counts at churn time | – (legacy uses end-of-month snapshot) |
| 14 | Sub_end on June 30, churned July 1 (day 1 of grace) | **C** (within grace) | **C** | – (v3 uses calendar month, July 1 is next month) | – | – (legacy: June churn only) |

---

## Quantitative Disagreement (June 2024 Sample)

| Metric | Value | Relative to v1 |
|---|---|---|
| v1 Logo Churn | ~3.2% | baseline |
| v2 Gross Revenue Churn | ~2.8% | −12% (high-MRR customers churn less often) |
| v3 Gross Revenue Churn + downgrades | ~4.1% | +28% (downgrades add 1.3 percentage points) |
| v4 Net Revenue Churn | ~1.9% | −41% (expansion activity offsets gross losses) |
| Legacy Dashboard | ~5.7% | +78% (counts duplicates, all downgrades, no dedup) |

*Values are illustrative based on generated sample data. Run `engine/app.py /compare` to see live numbers.*

---

## Why This Table Wins the Stakeholder Room

The VP arrives with a number. The analyst arrives with a different number. The finance director has a third. This table shows that all four are correct — given their assumptions. The conversation shifts from "who's right" to "which assumptions should we standardize on." That is the only conversation worth having.

The authoritative definition (`decisions/metric-definition.md`) picks v1 for operational decisions. v4 is tracked for executive reporting. Both are tagged on every result so there is no ambiguity about what produced any given number.
