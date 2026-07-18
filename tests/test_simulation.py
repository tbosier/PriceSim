"""Tests for the Monte Carlo simulation engine."""

import pandas as pd

from foundry_pricing.models import FoundryConfig, JobScenario, SimulationSettings
from foundry_pricing.simulation import (
    RESULT_COLUMNS,
    simulate_many,
    simulate_scenario,
    summarize_results,
)


def _config() -> FoundryConfig:
    return FoundryConfig(
        n_lines=4,
        hours_per_line_week=168,
        base_line_hour_cost=900,
        base_line_hour_value=1600,
        engineering_hour_cost=175,
        current_utilization=0.88,
        target_margin=0.35,
        risk_percentile=0.80,
        downtime_probability=0.12,
        downtime_hours_mean=16,
        downtime_hours_sd=8,
    )


def _scenario(
    name: str = "s", lines: int = 2, weeks: float = 2.0, wtp: float = 0.05
) -> JobScenario:
    return JobScenario(
        name=name,
        lines_requested=lines,
        production_weeks=weeks,
        tooling_weeks_mean=1.5,
        tooling_weeks_sd=0.5,
        debug_weeks_mean=0.75,
        debug_weeks_sd=0.35,
        engineering_hours_mean=300,
        engineering_hours_sd=100,
        tooling_parts_cost_mean=250000,
        tooling_parts_cost_sd=75000,
        expected_units=250000,
        revenue_per_unit=8.0,
        variable_cost_per_unit=2.75,
        yield_alpha=35,
        yield_beta=8,
        expedite_willingness_to_pay=wtp,
        retooling_complexity="medium",
    )


def _settings(n: int = 4000, seed: int = 42) -> SimulationSettings:
    return SimulationSettings(n_sims=n, random_seed=seed)


def test_simulate_scenario_has_expected_columns_and_rowcount() -> None:
    df = simulate_scenario(_scenario(), _config(), _settings(n=1000))
    assert list(df.columns) == list(RESULT_COLUMNS)
    assert len(df) == 1000


def test_simulate_many_rowcount_is_nsims_times_scenarios() -> None:
    scenarios = [_scenario("a"), _scenario("b"), _scenario("c")]
    df = simulate_many(scenarios, _config(), _settings(n=1000))
    assert len(df) == 1000 * 3
    assert set(df["scenario"].unique()) == {"a", "b", "c"}


def test_same_seed_returns_identical_summary() -> None:
    scenarios = [_scenario("a"), _scenario("b")]
    cfg, st = _config(), _settings()
    s1 = summarize_results(simulate_many(scenarios, cfg, st), cfg, scenarios)
    s2 = summarize_results(simulate_many(scenarios, cfg, st), cfg, scenarios)
    pd.testing.assert_frame_equal(s1, s2)


def test_no_negative_direct_costs() -> None:
    df = simulate_scenario(_scenario(), _config(), _settings())
    assert (df["direct_cost"] >= 0).all()


def test_good_units_between_zero_and_expected() -> None:
    scn = _scenario()
    df = simulate_scenario(scn, _config(), _settings())
    assert (df["good_units"] >= 0).all()
    assert (df["good_units"] <= scn.expected_units).all()


def test_effective_yield_within_unit_interval() -> None:
    df = simulate_scenario(_scenario(), _config(), _settings())
    assert (df["effective_yield"] >= 0).all()
    assert (df["effective_yield"] <= 1).all()


def test_expedited_quote_at_least_target_quote() -> None:
    df = simulate_scenario(_scenario(wtp=0.10), _config(), _settings())
    assert (df["expedited_quote"] >= df["target_quote"]).all()


def test_summary_target_quote_above_economic_floor_median() -> None:
    scn = _scenario()
    cfg, st = _config(), _settings()
    summary = summarize_results(simulate_many([scn], cfg, st), cfg, [scn])
    row = summary.iloc[0]
    assert row["suggested_target_quote"] > row["p50_economic_floor"]


def test_higher_utilization_raises_target_quote() -> None:
    scn = _scenario()
    low = _config().model_copy(update={"current_utilization": 0.65})
    high = _config().model_copy(update={"current_utilization": 0.95})
    st = _settings()
    q_low = summarize_results(simulate_many([scn], low, st), low, [scn]).iloc[0][
        "suggested_target_quote"
    ]
    q_high = summarize_results(simulate_many([scn], high, st), high, [scn]).iloc[0][
        "suggested_target_quote"
    ]
    assert q_high > q_low


def test_four_lines_one_week_has_higher_parallelism_than_one_line_four_weeks() -> None:
    cfg, st = _config(), _settings(n=500)
    economy = _scenario("economy", lines=1, weeks=4.0)
    expedited = _scenario("expedited", lines=4, weeks=1.0)
    summary = summarize_results(
        simulate_many([economy, expedited], cfg, st), cfg, [economy, expedited]
    )
    p_econ = summary.set_index("scenario").loc["economy", "parallelism_multiplier"]
    p_exp = summary.set_index("scenario").loc["expedited", "parallelism_multiplier"]
    assert p_exp > p_econ


def test_downtime_adds_reserved_hours_above_bare_minimum() -> None:
    # reserved_line_hours must be >= production+tooling+debug hours (downtime only adds).
    scn = _scenario()
    df = simulate_scenario(scn, _config(), _settings())
    min_reserved = (
        scn.lines_requested * (df["tooling_weeks"] + df["debug_weeks"] + scn.production_weeks) * 168
    )
    assert (df["reserved_line_hours"] >= min_reserved - 1e-6).all()
