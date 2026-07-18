"""Tests for the random-draw helpers."""

import numpy as np

from foundry_pricing.distributions import sample_downtime_hours, truncated_normal


def test_truncated_normal_respects_lower_bound() -> None:
    rng = np.random.default_rng(0)
    draws = truncated_normal(rng, mean=0.5, sd=2.0, size=10_000, lower=0.1)
    assert draws.min() >= 0.1
    assert draws.shape == (10_000,)


def test_truncated_normal_zero_sd_returns_mean() -> None:
    rng = np.random.default_rng(0)
    draws = truncated_normal(rng, mean=1.5, sd=0.0, size=100, lower=0.0)
    assert np.allclose(draws, 1.5)


def test_truncated_normal_is_reproducible() -> None:
    a = truncated_normal(np.random.default_rng(42), 1.0, 0.5, 1000)
    b = truncated_normal(np.random.default_rng(42), 1.0, 0.5, 1000)
    assert np.array_equal(a, b)


def test_downtime_zero_probability_is_all_zero() -> None:
    rng = np.random.default_rng(1)
    draws = sample_downtime_hours(rng, probability=0.0, mean=16, sd=8, size=5000)
    assert np.all(draws == 0.0)


def test_downtime_full_probability_is_non_negative_and_positive_mean() -> None:
    rng = np.random.default_rng(1)
    draws = sample_downtime_hours(rng, probability=1.0, mean=16, sd=8, size=5000)
    assert draws.min() >= 0.0
    # With probability 1 and mean 16, the average downtime should be well above 0.
    assert draws.mean() > 5.0


def test_downtime_partial_probability_has_some_zeros_and_some_positive() -> None:
    rng = np.random.default_rng(2)
    draws = sample_downtime_hours(rng, probability=0.3, mean=16, sd=8, size=5000)
    zero_fraction = np.mean(draws == 0.0)
    # Roughly 70% of draws should be "no downtime".
    assert 0.6 < zero_fraction < 0.8
