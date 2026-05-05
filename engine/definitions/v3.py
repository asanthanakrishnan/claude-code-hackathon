"""
Definition v3: Gross Revenue Churn Rate (cancellations + significant downgrades)

Rules:
- Numerator:   MRR lost from cancellations (status=churned, subscription_end within period)
               PLUS MRR delta for downgrades where the reduction is >= 20% of the
               original MRR (downgraded_from_mrr - mrr >= 0.20 * downgraded_from_mrr).
- Denominator: MRR of all subscriptions active on the first calendar day of the period.
- Period boundary: calendar-month boundary — period is defined by the calendar month;
                   a subscription_end on the last day of the prior month does NOT count.
- No grace period: a customer who does not renew by subscription_end is churned.
                   churned_at is ignored in this version.
- Downgrade threshold: a reduction of exactly 20.0% of original MRR counts (>=20%).
                       A reduction of 19.99% does NOT count.
- Excludes: rows flagged missing_mrr or missing_status or missing_subscription_end.
"""

from datetime import date
import calendar


def _month_boundary(period_start: date) -> tuple[date, date]:
    """Return (first_day, last_day) of the calendar month containing period_start."""
    first = period_start.replace(day=1)
    last_day = calendar.monthrange(first.year, first.month)[1]
    last = first.replace(day=last_day)
    return first, last


def calculate(rows: list[dict], period_start: date, period_end: date) -> dict:
    DOWNGRADE_THRESHOLD = 0.20  # >= 20% MRR reduction counts as churn

    month_start, month_end = _month_boundary(period_start)

    mrr_at_start: float = 0.0
    lost_mrr: float = 0.0
    counted_customers: set[str] = set()

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
        status = row.get("status", "")

        if sub_start <= month_start <= sub_end and cid not in counted_customers:
            mrr_at_start += mrr
            counted_customers.add(cid)

        if not (month_start <= sub_end <= month_end):
            continue

        if status == "churned" and cid in counted_customers:
            lost_mrr += mrr

        elif status == "downgraded" and cid in counted_customers:
            orig_str = row.get("downgraded_from_mrr", "")
            if not orig_str:
                continue
            try:
                orig_mrr = float(orig_str)
            except ValueError:
                continue
            reduction = orig_mrr - mrr
            if orig_mrr > 0 and (reduction / orig_mrr) >= DOWNGRADE_THRESHOLD:
                lost_mrr += reduction

    return {
        "version": "v3",
        "label": "Gross Revenue Churn Rate (cancellations + downgrades ≥20%)",
        "numerator": round(lost_mrr, 2),
        "denominator": round(mrr_at_start, 2),
        "value": round(lost_mrr / mrr_at_start, 6) if mrr_at_start > 0 else None,
        "period_start": month_start.isoformat(),
        "period_end": month_end.isoformat(),
        "parameters": {
            "grace_period_days": 0,
            "count_type": "mrr",
            "includes_downgrades": True,
            "downgrade_threshold_pct": 20,
            "boundary": "calendar_month",
        },
    }
