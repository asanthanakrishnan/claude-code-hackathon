"""Shared test fixtures — deterministic rows covering all edge cases."""

from datetime import date

BASE = date(2024, 6, 1)
PERIOD_START = date(2024, 6, 1)
PERIOD_END = date(2024, 6, 30)


def row(
    cid: str,
    status: str,
    mrr: float,
    sub_start: str,
    sub_end: str,
    churned_at: str = "",
    downgraded_from_mrr: float | str = "",
    expanded_to_mrr: float | str = "",
    flags: str = "",
) -> dict:
    return {
        "subscription_id": f"sub_{cid}",
        "customer_id": cid,
        "customer_name": f"Customer {cid}",
        "customer_email": f"{cid}@example.com",
        "plan": "growth",
        "region": "us-east",
        "mrr": str(mrr),
        "subscription_start": sub_start,
        "subscription_end": sub_end,
        "status": status,
        "churned_at": churned_at,
        "downgraded_from_mrr": str(downgraded_from_mrr) if downgraded_from_mrr else "",
        "expanded_to_mrr": str(expanded_to_mrr) if expanded_to_mrr else "",
        "recorded_at": "2024-07-01T00:00:00+00:00",
        "source_file": "test",
        "data_quality_flags": flags,
    }


# --- Standard test scenarios ---

ACTIVE_NO_CHURN = row("c01", "active", 399, "2024-01-01", "2024-12-31")

CHURNED_IN_PERIOD_WITHIN_GRACE = row(
    "c02", "churned", 399, "2024-01-01", "2024-06-15", churned_at="2024-06-20"
)

CHURNED_OUTSIDE_GRACE = row(
    "c03", "churned", 399, "2024-01-01", "2024-06-15", churned_at="2024-07-20"
)  # churned_at > sub_end + 30 days

CHURNED_BEFORE_PERIOD = row(
    "c04", "churned", 399, "2023-06-01", "2024-05-31", churned_at="2024-06-01"
)  # sub_end outside June

DOWNGRADE_LARGE = row(
    "c05", "downgraded", 99, "2024-01-01", "2024-06-20",
    downgraded_from_mrr=399,
)  # 75% reduction — counts in v3/v4

DOWNGRADE_SMALL = row(
    "c06", "downgraded", 350, "2024-01-01", "2024-06-20",
    downgraded_from_mrr=399,
)  # 12.3% reduction — does NOT count in v3/v4

EXPANSION = row(
    "c07", "expanded", 399, "2024-01-01", "2024-06-20",
    expanded_to_mrr=899,
)  # +500 MRR expansion

MISSING_MRR = row("c08", "churned", 399, "2024-01-01", "2024-06-15",
                  churned_at="2024-06-20", flags="missing_mrr")

MISSING_STATUS = row("c09", "churned", 399, "2024-01-01", "2024-06-15",
                     churned_at="2024-06-20", flags="missing_status")

BOUNDARY_GRACE_EXACT = row(
    "c10", "churned", 399, "2024-01-01", "2024-06-15", churned_at="2024-07-15"
)  # churned_at == sub_end + exactly 30 days — still within grace

BOUNDARY_GRACE_ONE_OVER = row(
    "c11", "churned", 399, "2024-01-01", "2024-06-15", churned_at="2024-07-16"
)  # churned_at == sub_end + 31 days — outside grace

DOWNGRADE_EXACTLY_20PCT = row(
    "c12", "downgraded", 319, "2024-01-01", "2024-06-20",
    downgraded_from_mrr=399,
)  # 399 * 0.20 = 79.8; 399-319=80 → 80/399=20.05% ≥ 20% — counts
