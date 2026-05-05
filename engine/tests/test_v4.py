"""Tests for v4: Net Revenue Churn Rate"""

import pytest
from engine.definitions.v4 import calculate
from .fixtures import (
    PERIOD_START, PERIOD_END,
    ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE,
    DOWNGRADE_LARGE, EXPANSION, DOWNGRADE_SMALL,
)


def calc(rows):
    return calculate(rows, PERIOD_START, PERIOD_END)


def test_result_tagged_v4():
    assert calc([ACTIVE_NO_CHURN])["version"] == "v4"


def test_expansion_offsets_churn():
    """Net churn = lost MRR - expansion MRR."""
    # CHURNED (399 lost) + EXPANSION (+500 gained) + ACTIVE (denom 399+399+399)
    r = calc([ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE, EXPANSION])
    # numerator = 399 - 500 = -101
    assert r["numerator"] == pytest.approx(-101.0)


def test_negative_net_churn_allowed():
    """Net revenue expansion (negative churn) is valid."""
    r = calc([ACTIVE_NO_CHURN, EXPANSION])
    assert r["value"] is not None
    assert r["value"] < 0


def test_downgrade_large_in_numerator():
    """Large downgrade increases lost_mrr."""
    r = calc([ACTIVE_NO_CHURN, DOWNGRADE_LARGE])
    assert r["numerator"] > 0


def test_downgrade_small_excluded():
    r = calc([ACTIVE_NO_CHURN, DOWNGRADE_SMALL])
    assert r["numerator"] == 0.0


def test_pure_churn_no_expansion():
    r = calc([ACTIVE_NO_CHURN, CHURNED_IN_PERIOD_WITHIN_GRACE])
    assert r["numerator"] == pytest.approx(399.0)
