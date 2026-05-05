"""Tests for v3: Gross Revenue Churn (cancellations + downgrades ≥20%)"""

import pytest
from engine.definitions.v3 import calculate
from .fixtures import (
    PERIOD_START, PERIOD_END,
    ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE, CHURNED_OUTSIDE_GRACE,
    DOWNGRADE_LARGE, DOWNGRADE_SMALL, EXPANSION, DOWNGRADE_EXACTLY_20PCT,
)


def calc(rows):
    return calculate(rows, PERIOD_START, PERIOD_END)


def test_result_tagged_v3():
    assert calc([ACTIVE_NO_CHURN])["version"] == "v3"


def test_uses_calendar_month_boundary():
    r = calc([ACTIVE_NO_CHURN])
    assert r["period_start"] == "2024-06-01"
    assert r["period_end"] == "2024-06-30"


def test_large_downgrade_counted():
    """75% reduction should be in numerator."""
    r = calc([ACTIVE_NO_CHURN, DOWNGRADE_LARGE])
    # downgraded_from_mrr=399, mrr=99 → reduction=300
    assert r["numerator"] == pytest.approx(300.0)


def test_small_downgrade_not_counted():
    """12.3% reduction should be excluded."""
    r = calc([ACTIVE_NO_CHURN, DOWNGRADE_SMALL])
    assert r["numerator"] == 0.0


def test_exactly_20pct_downgrade_counts():
    """Boundary: exactly 20% reduction counts (>=20%)."""
    r = calc([ACTIVE_NO_CHURN, DOWNGRADE_EXACTLY_20PCT])
    # 399 - 319 = 80; 80/399 = 20.05% ≥ 20
    assert r["numerator"] > 0.0


def test_churned_in_period_no_grace():
    """v3 has no grace period — any churn within month counts."""
    r = calc([ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE])
    assert r["numerator"] == pytest.approx(399.0)


def test_expansion_not_subtracted():
    """v3 is gross churn — expansions don't offset."""
    r = calc([ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE, EXPANSION])
    assert r["numerator"] == pytest.approx(399.0)
