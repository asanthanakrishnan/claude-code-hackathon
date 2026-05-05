"""
Definition v2: Gross Revenue Churn Rate (cancellations only)

Rules:
- Numerator:   sum of MRR for subscriptions that churned within the period (status=churned,
               subscription_end within period, churned_at within 30-day grace period).
               Downgrades do NOT count. Uses the MRR value at time of subscription.
- Denominator: sum of MRR for all subscriptions active on the first calendar day of the period.
- Grace period: 30 calendar days from subscription_end.
- Excludes:    rows flagged missing_mrr, missing_status, or missing_subscription_end.
- Period:      [period_start, period_end] inclusive.
"""

from datetime import date, timedelta


def calculate(rows: list[dict], period_start: date, period_end: date) -> dict:
    GRACE_DAYS = 30

    mrr_at_start: float = 0.0
    churned_mrr: float = 0.0
    counted_customers: set[str] = set()
    churned_customers: set[str] = set()

    for row in rows:
        flags = row.get("data_quality_flags") or ""
        if any(f in flags for f in ("missing_mrr", "missing_status", "missing_subscription_end")):
            continue

        try:
            mrr = float(row["mrr"])
            sub_start = date.fromisoformat(row["subscription_start"])
            sub_end = date.fromisoformat(row["subscription_end"])
        except (ValueError, KeyError):
            continue

        cid = row.get("customer_id", "")

        if sub_start <= period_start <= sub_end and cid not in counted_customers:
            mrr_at_start += mrr
            counted_customers.add(cid)

        if row.get("status") != "churned":
            continue
        if not (period_start <= sub_end <= period_end):
            continue

        churned_at_str = row.get("churned_at", "")
        if not churned_at_str:
            continue
        try:
            churned_at = date.fromisoformat(churned_at_str)
        except ValueError:
            continue

        grace_deadline = sub_end + timedelta(days=GRACE_DAYS)
        if sub_end <= churned_at <= grace_deadline and cid not in churned_customers:
            # Only count if customer was active at period start
            if cid in counted_customers:
                churned_mrr += mrr
                churned_customers.add(cid)

    return {
        "version": "v2",
        "label": "Gross Revenue Churn Rate (cancellations only)",
        "numerator": round(churned_mrr, 2),
        "denominator": round(mrr_at_start, 2),
        "value": round(churned_mrr / mrr_at_start, 6) if mrr_at_start > 0 else None,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "parameters": {
            "grace_period_days": GRACE_DAYS,
            "count_type": "mrr",
            "includes_downgrades": False,
        },
    }
