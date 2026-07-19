"""Property-based tests with hypothesis.

These assert invariants that must hold across wide input ranges, catching whole
classes of regressions that a handful of example tests would miss. Strategies
are bounded to realistic ranges so the tests stay fast and never trip the model
validators.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from foundry_pricing.models import FoundryConfig, JobScenario, SimulationSettings
from foundry_pricing.pricing import (
    parallelism_multiplier,
    scarcity_multiplier,
    target_quote,
)
from foundry_pricing.scheduling import schedule_backlog
from foundry_pricing.simulation import simulate_scenario

# --- Pricing multiplier monotonicity ---------------------------------------


@given(
    a=st.floats(min_value=0.0, max_value=1.0),
    b=st.floats(min_value=0.0, max_value=1.0),
)
def test_scarcity_multiplier_is_monotone_in_utilization(a: float, b: float) -> None:
    lo, hi = sorted((a, b))
    assert scarcity_multiplier(lo) <= scarcity_multiplier(hi)


@given(
    total_lines=st.integers(min_value=1, max_value=20),
    a=st.integers(min_value=1, max_value=20),
    b=st.integers(min_value=1, max_value=20),
)
def test_parallelism_multiplier_is_monotone_in_share(total_lines: int, a: int, b: int) -> None:
    lo, hi = sorted((a, b))
    assert parallelism_multiplier(lo, total_lines) <= parallelism_multiplier(hi, total_lines)


# --- target_quote invariants ------------------------------------------------


@given(
    floor=st.floats(min_value=0.0, max_value=1e9),
    margin=st.floats(min_value=0.0, max_value=0.949),
)
def test_target_quote_never_below_floor(floor: float, margin: float) -> None:
    assert target_quote(floor, margin) >= floor - 1e-6


@given(floor=st.floats(min_value=0.0, max_value=1e9))
def test_target_quote_equals_floor_at_zero_margin(floor: float) -> None:
    assert target_quote(floor, 0.0) == pytest.approx(floor)


# --- Simulation output invariants ------------------------------------------

_config_strategy = st.builds(
    FoundryConfig,
    n_lines=st.integers(min_value=1, max_value=8),
    hours_per_line_week=st.floats(min_value=40, max_value=168),
    # Strictly positive so the economic floor (and thus the quote) is never
    # exactly zero, which would make the core's realized-margin division ill-defined.
    base_line_hour_cost=st.floats(min_value=1, max_value=2000),
    base_line_hour_value=st.floats(min_value=0, max_value=3000),
    engineering_hour_cost=st.floats(min_value=0, max_value=500),
    current_utilization=st.floats(min_value=0.0, max_value=1.0),
    target_margin=st.floats(min_value=0.0, max_value=0.9),
    risk_percentile=st.floats(min_value=0.5, max_value=0.99),
    downtime_probability=st.floats(min_value=0.0, max_value=1.0),
    downtime_hours_mean=st.floats(min_value=0.0, max_value=48),
    downtime_hours_sd=st.floats(min_value=0.0, max_value=24),
)


def _scenario_strategy(max_lines: int) -> st.SearchStrategy[JobScenario]:
    return st.builds(
        JobScenario,
        name=st.just("prop-scenario"),
        lines_requested=st.integers(min_value=1, max_value=max_lines),
        production_weeks=st.floats(min_value=0.5, max_value=6),
        tooling_weeks_mean=st.floats(min_value=0.0, max_value=4),
        tooling_weeks_sd=st.floats(min_value=0.0, max_value=1.5),
        debug_weeks_mean=st.floats(min_value=0.0, max_value=3),
        debug_weeks_sd=st.floats(min_value=0.0, max_value=1.0),
        engineering_hours_mean=st.floats(min_value=0.0, max_value=1000),
        engineering_hours_sd=st.floats(min_value=0.0, max_value=300),
        tooling_parts_cost_mean=st.floats(min_value=0.0, max_value=500000),
        tooling_parts_cost_sd=st.floats(min_value=0.0, max_value=150000),
        expected_units=st.integers(min_value=0, max_value=1_000_000),
        revenue_per_unit=st.floats(min_value=0.0, max_value=100),
        variable_cost_per_unit=st.floats(min_value=0.0, max_value=50),
        yield_alpha=st.floats(min_value=1, max_value=60),
        yield_beta=st.floats(min_value=1, max_value=60),
        expedite_willingness_to_pay=st.floats(min_value=0.0, max_value=0.5),
        retooling_complexity=st.sampled_from(["low", "medium", "high", "extreme"]),
    )


@st.composite
def _config_and_scenario(
    draw: st.DrawFn,
) -> tuple[FoundryConfig, JobScenario]:
    config = draw(_config_strategy)
    scenario = draw(_scenario_strategy(config.n_lines))
    return config, scenario


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(data=_config_and_scenario(), seed=st.integers(min_value=0, max_value=10_000))
def test_simulated_outputs_stay_in_valid_ranges(
    data: tuple[FoundryConfig, JobScenario], seed: int
) -> None:
    config, scenario = data
    sim_settings = SimulationSettings(n_sims=256, random_seed=seed)
    frame = simulate_scenario(scenario, config, sim_settings)

    yields = frame["effective_yield"].to_numpy()
    assert np.all(yields >= 0.0)
    assert np.all(yields <= 1.0)

    good_units = frame["good_units"].to_numpy()
    assert np.all(good_units >= 0.0)
    assert np.all(good_units <= scenario.expected_units + 1e-6)

    assert np.all(frame["direct_cost"].to_numpy() >= 0.0)
    assert np.all(frame["opportunity_cost"].to_numpy() >= 0.0)
    assert np.all(frame["reserved_line_hours"].to_numpy() >= 0.0)


# --- Determinism ------------------------------------------------------------


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(data=_config_and_scenario(), seed=st.integers(min_value=0, max_value=10_000))
def test_same_seed_produces_identical_results(
    data: tuple[FoundryConfig, JobScenario], seed: int
) -> None:
    config, scenario = data
    sim_settings = SimulationSettings(n_sims=128, random_seed=seed)
    first = simulate_scenario(scenario, config, sim_settings)
    second = simulate_scenario(scenario, config, sim_settings)
    pd.testing.assert_frame_equal(first, second)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(data=_config_and_scenario(), seed=st.integers(min_value=0, max_value=5_000))
def test_different_seeds_generally_differ(
    data: tuple[FoundryConfig, JobScenario], seed: int
) -> None:
    config, scenario = data
    # With any real spread in the draws, two different seeds should not produce
    # the exact same economic-floor column. Skip degenerate all-constant configs
    # (zero costs and zero variance) where identical output is legitimate.
    has_spread = (
        scenario.tooling_weeks_sd > 0
        or scenario.debug_weeks_sd > 0
        or scenario.engineering_hours_sd > 0
        or scenario.tooling_parts_cost_sd > 0
    )
    if not has_spread:
        return
    a = simulate_scenario(scenario, config, SimulationSettings(n_sims=256, random_seed=seed))
    b = simulate_scenario(scenario, config, SimulationSettings(n_sims=256, random_seed=seed + 1))
    assert not np.array_equal(a["economic_floor"].to_numpy(), b["economic_floor"].to_numpy())


# --- Scheduler invariants ---------------------------------------------------

_line_weeks = st.floats(min_value=0.1, max_value=10.0)
_jobs = st.lists(
    st.tuples(
        _line_weeks,
        st.integers(min_value=1, max_value=12),  # due_week
        st.floats(min_value=0.0, max_value=500_000),  # penalty per week
        st.integers(min_value=1, max_value=5),  # priority
    ),
    min_size=1,
    max_size=8,
)


def _make_backlog(
    jobs: list[tuple[float, int, float, int]],
) -> pd.DataFrame:
    rows = [
        dict(
            job_id=f"J{i}",
            customer=f"C{i}",
            required_line_weeks=lw,
            margin_value=1_000_000.0,
            due_week=due,
            late_penalty_per_week=pen,
            priority=prio,
        )
        for i, (lw, due, pen, prio) in enumerate(jobs)
    ]
    return pd.DataFrame(rows)


@settings(max_examples=80, deadline=None)
@given(jobs=_jobs, n_lines=st.integers(min_value=1, max_value=4))
def test_capacity_is_conserved_no_work_dropped(
    jobs: list[tuple[float, int, float, int]], n_lines: int
) -> None:
    backlog = _make_backlog(jobs)
    result = schedule_backlog(backlog, n_lines=n_lines, planning_horizon_weeks=12)

    # Every job is scheduled exactly once.
    assert len(result) == len(backlog)
    assert set(result["job_id"]) == set(backlog["job_id"])

    # Work is conserved: the makespan cannot be shorter than the total required
    # line-weeks divided by the per-week capacity. If any work were dropped the
    # schedule could finish sooner than this lower bound.
    total_line_weeks = float(backlog["required_line_weeks"].sum())
    min_makespan = math.ceil(total_line_weeks / n_lines - 1e-9)
    assert int(result["completion_week"].max()) >= min_makespan


@settings(max_examples=60, deadline=None)
@given(jobs=_jobs, n_lines=st.integers(min_value=1, max_value=4))
def test_adding_a_job_never_reduces_total_late_penalty(
    jobs: list[tuple[float, int, float, int]], n_lines: int
) -> None:
    backlog = _make_backlog(jobs)
    before = schedule_backlog(backlog, n_lines=n_lines, planning_horizon_weeks=12)
    total_before = float(before["late_penalty"].sum())

    extra = pd.DataFrame(
        [
            dict(
                job_id="EXTRA",
                customer="extra",
                required_line_weeks=3.0,
                margin_value=1_000_000.0,
                due_week=1,
                late_penalty_per_week=100_000.0,
                priority=3,
            )
        ]
    )
    augmented = pd.concat([backlog, extra], ignore_index=True)
    after = schedule_backlog(augmented, n_lines=n_lines, planning_horizon_weeks=12)
    total_after = float(after["late_penalty"].sum())

    assert total_after >= total_before - 1e-6
