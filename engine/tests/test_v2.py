"""Tests for v2: Gross Revenue Churn Rate (cancellations only)"""

import pytest
from engine.definitions.v2 import calculate
from .fixtures import (
    PERIOD_START, PERIOD_END,
    ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE, CHURNED_OUTSIDE_GRACE,
    DOWNGRADE_LARGE, EXPANSION, MISSING_MRR,
    BOUNDARY_GRACE_EXACT, BOUNDARY_GRACE_ONE_OVER,
)


def calc(rows):
    return calculate(rows, PERIOD_START, PERIOD_END)


def test_result_tagged_v2():
    assert calc([ACTIVE_NO_CHURN])["version"] == "v2"


def test_no_churn_zero_rate():
    r = calc([ACTIVE_NO_CHURN])
    assert r["value"] == 0.0


def test_churned_mrr_in_numerator():
    r = calc([ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE])
    assert r["numerator"] == pytest.approx(399.0)
    assert r["denominator"] == pytest.approx(798.0)


def test_downgrade_not_counted():
    r = calc([ACTIVE_NO_CHURN, DOWNGRADE_LARGE])
    assert r["numerator"] == 0.0


def test_expansion_not_counted():
    r = calc([ACTIVE_NO_CHURN, EXPANSION])
    assert r["numerator"] == 0.0


def test_outside_grace_excluded():
    r = calc([ACTIVE_NO_CHURN, CHURNED_OUTSIDE_GRACE])
    assert r["numerator"] == 0.0


def test_missing_mrr_excluded():
    r = calc([MISSING_MRR])
    assert r["denominator"] == 0.0


def test_grace_boundary_exact_counts():
    r = calc([BOUNDARY_GRACE_EXACT])
    assert r["numerator"] == pytest.approx(399.0)


def test_grace_boundary_one_over_excluded():
    r = calc([BOUNDARY_GRACE_ONE_OVER])
    assert r["numerator"] == 0.0
