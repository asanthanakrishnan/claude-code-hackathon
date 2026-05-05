"""Tests for v1: Logo Churn Rate"""

from datetime import date
import pytest
from engine.definitions.v1 import calculate
from .fixtures import (
    PERIOD_START, PERIOD_END,
    ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE, CHURNED_OUTSIDE_GRACE,
    CHURNED_BEFORE_PERIOD, DOWNGRADE_LARGE, EXPANSION,
    MISSING_MRR, MISSING_STATUS, BOUNDARY_GRACE_EXACT, BOUNDARY_GRACE_ONE_OVER,
)


def calc(rows):
    return calculate(rows, PERIOD_START, PERIOD_END)


def test_result_tagged_v1():
    r = calc([ACTIVE_NO_CHURN])
    assert r["version"] == "v1"


def test_no_churn_returns_zero():
    r = calc([ACTIVE_NO_CHURN])
    assert r["value"] == 0.0
    assert r["numerator"] == 0


def test_churned_within_grace_counts():
    r = calc([ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE])
    assert r["numerator"] == 1
    assert r["denominator"] == 2


def test_churned_outside_grace_excluded():
    r = calc([ACTIVE_NO_CHURN, CHURNED_OUTSIDE_GRACE])
    assert r["numerator"] == 0


def test_churned_before_period_excluded():
    r = calc([CHURNED_BEFORE_PERIOD])
    assert r["numerator"] == 0


def test_downgrade_not_counted():
    r = calc([ACTIVE_NO_CHURN, DOWNGRADE_LARGE])
    assert r["numerator"] == 0


def test_expansion_not_counted():
    r = calc([ACTIVE_NO_CHURN, EXPANSION])
    assert r["numerator"] == 0


def test_missing_status_row_excluded():
    r = calc([ACTIVE_NO_CHURN, MISSING_STATUS])
    assert r["denominator"] == 1  # MISSING_STATUS row excluded from denominator too


def test_empty_rows_returns_none():
    r = calc([])
    assert r["value"] is None
    assert r["denominator"] == 0


def test_grace_boundary_exact_counts():
    """churned_at == sub_end + 30 is still within grace (inclusive)."""
    r = calc([BOUNDARY_GRACE_EXACT])
    assert r["numerator"] == 1


def test_grace_boundary_one_over_excluded():
    """churned_at == sub_end + 31 is outside grace."""
    r = calc([BOUNDARY_GRACE_ONE_OVER])
    assert r["numerator"] == 0


def test_rate_calculation():
    rows = [ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE]
    r = calc(rows)
    assert r["value"] == pytest.approx(0.5, abs=1e-5)
