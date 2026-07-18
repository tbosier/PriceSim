"""Tests for the pure pricing formula functions."""

import pytest

from foundry_pricing.pricing import (
    expedited_quote,
    parallelism_multiplier,
    retooling_multiplier,
    scarcity_multiplier,
    target_quote,
)


@pytest.mark.parametrize(
    ("utilization", "expected"),
    [
        (0.0, 0.85),
        (0.59, 0.85),
        (0.60, 1.00),
        (0.79, 1.00),
        (0.80, 1.25),
        (0.89, 1.25),
        (0.90, 1.60),
        (0.96, 1.60),
        (0.97, 2.25),
        (1.0, 2.25),
    ],
)
def test_scarcity_multiplier_thresholds(utilization: float, expected: float) -> None:
    assert scarcity_multiplier(utilization) == expected


@pytest.mark.parametrize(
    ("lines", "total", "expected"),
    [
        (1, 4, 1.00),  # share 0.25
        (2, 4, 1.15),  # share 0.50
        (3, 4, 1.35),  # share 0.75
        (4, 4, 1.75),  # share 1.00
    ],
)
def test_parallelism_multiplier_thresholds(lines: int, total: int, expected: float) -> None:
    assert parallelism_multiplier(lines, total) == expected


def test_retooling_multiplier_values() -> None:
    assert retooling_multiplier("low") == 0.85
    assert retooling_multiplier("medium") == 1.00
    assert retooling_multiplier("high") == 1.35
    assert retooling_multiplier("extreme") == 1.80


def test_retooling_multiplier_rejects_unknown() -> None:
    with pytest.raises(KeyError):
        retooling_multiplier("nonsense")


def test_target_quote_exceeds_floor_when_margin_positive() -> None:
    floor = 1_000_000.0
    assert target_quote(floor, target_margin=0.35) > floor


def test_target_quote_equals_floor_when_margin_zero() -> None:
    floor = 1_000_000.0
    assert target_quote(floor, target_margin=0.0) == floor


def test_expedited_quote_at_least_target_quote() -> None:
    tq = 1_000_000.0
    # Zero willingness-to-pay -> equal.
    assert expedited_quote(tq, expedite_wtp=0.0, parallelism_mult=1.75) == tq
    # Positive willingness-to-pay -> strictly greater.
    assert expedited_quote(tq, expedite_wtp=0.10, parallelism_mult=1.75) > tq
