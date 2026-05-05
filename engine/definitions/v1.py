"""
Definition v1: Logo Churn Rate

Rules:
- Numerator:   customers whose subscription ended within the period AND whose
               churned_at date falls within [subscription_end, subscription_end + 30 days].
               Status must be 'churned'. Downgrades do NOT count.
- Denominator: distinct customers with an active subscription on the first calendar
               day of the period (subscription_start <= period_start <= subscription_end).
- Grace period: 30 calendar days from subscription_end. A customer who renews within
                30 days is NOT churned.
- Excludes:    rows with data_quality_flags containing 'missing_status' or 'missing_mrr'.
- Period:      [period_start, period_end] inclusive, compared against subscription_end.
               Only subscriptions ending within the period are candidates for churn.
"""

from datetime import date, timedelta


def calculate(rows: list[dict], period_start: date, period_end: date) -> dict:
    GRACE_DAYS = 30

    active_at_start: set[str] = set()
    churned_customers: set[str] = set()

    for row in rows:
        if "missing_status" in (row.get("data_quality_flags") or ""):
            continue
        if "missing_subscription_end" in (row.get("data_quality_flags") or ""):
            continue

        try:
            sub_start = date.fromisoformat(row["subscription_start"])
            sub_end = date.fromisoformat(row["subscription_end"])
        except (ValueError, KeyError):
            continue

        cid = row.get("customer_id", "")

        # Active at period start = subscription spans the period start date
        if sub_start <= period_start <= sub_end:
            active_at_start.add(cid)

        # Churned = status is 'churned', sub ends within period, and churned_at
        # is within grace period
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
        if sub_end <= churned_at <= grace_deadline:
            churned_customers.add(cid)

    denominator = len(active_at_start)
    numerator = len(churned_customers & active_at_start)

    return {
        "version": "v1",
        "label": "Logo Churn Rate",
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 6) if denominator > 0 else None,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "parameters": {"grace_period_days": GRACE_DAYS, "count_type": "customers"},
    }
