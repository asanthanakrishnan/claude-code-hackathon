"""
Definition v4: Net Revenue Churn Rate

Rules:
- Numerator:   (MRR lost from cancellations + downgrades ≥20%) MINUS
               (MRR gained from expansions within the same calendar month).
               Net can be negative (net revenue expansion).
- Denominator: MRR of all subscriptions active on the first calendar day of the month.
- Period boundary: calendar-month boundary (same as v3).
- Downgrade threshold: same as v3 — reduction >= 20% of original MRR.
- Expansion: status=expanded, expanded_to_mrr - mrr > 0. Only the delta is counted.
- No grace period (same as v3).
- Excludes: rows flagged missing_mrr or missing_status or missing_subscription_end.
"""

from datetime import date
import calendar


def _month_boundary(period_start: date) -> tuple[date, date]:
    first = period_start.replace(day=1)
    last_day = calendar.monthrange(first.year, first.month)[1]
    return first, first.replace(day=last_day)


def calculate(rows: list[dict], period_start: date, period_end: date) -> dict:
    DOWNGRADE_THRESHOLD = 0.20

    month_start, month_end = _month_boundary(period_start)

    mrr_at_start: float = 0.0
    lost_mrr: float = 0.0
    expansion_mrr: float = 0.0
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

        elif status == "expanded" and cid in counted_customers:
            exp_str = row.get("expanded_to_mrr", "")
            if not exp_str:
                continue
            try:
                exp_mrr = float(exp_str)
            except ValueError:
                continue
            delta = exp_mrr - mrr
            if delta > 0:
                expansion_mrr += delta

    net_lost = lost_mrr - expansion_mrr

    return {
        "version": "v4",
        "label": "Net Revenue Churn Rate",
        "numerator": round(net_lost, 2),
        "denominator": round(mrr_at_start, 2),
        "value": round(net_lost / mrr_at_start, 6) if mrr_at_start > 0 else None,
        "period_start": month_start.isoformat(),
        "period_end": month_end.isoformat(),
        "parameters": {
            "grace_period_days": 0,
            "count_type": "mrr",
            "includes_downgrades": True,
            "includes_expansions": True,
            "downgrade_threshold_pct": 20,
            "boundary": "calendar_month",
        },
    }
