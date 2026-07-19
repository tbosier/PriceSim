"""Golden-value tests: hand-verified known outputs.

These pin exact numbers so a future refactor cannot silently change the math.
The pricing multipliers are deterministic step functions and the Monte Carlo
draws are seeded, so everything here is exactly reproducible.
"""

from __future__ import annotations

import pandas as pd
import pytest

from foundry_pricing.models import FoundryConfig, JobScenario, SimulationSettings
from foundry_pricing.pricing import (
    expedited_quote,
    parallelism_multiplier,
    retooling_multiplier,
    scarcity_multiplier,
    target_quote,
)
from foundry_pricing.scheduling import proposed_job_to_backlog_row, schedule_backlog
from foundry_pricing.simulation import simulate_many, summarize_results

# --- Deterministic pricing multipliers -------------------------------------


def test_scarcity_multiplier_at_default_utilization() -> None:
    # 0.88 falls in the [0.80, 0.90) band -> 1.25.
    assert scarcity_multiplier(0.88) == 1.25


@pytest.mark.parametrize(
    ("utilization", "expected"),
    [
        (0.00, 0.85),
        (0.59, 0.85),
        (0.60, 1.00),
        (0.79, 1.00),
        (0.80, 1.25),
        (0.89, 1.25),
        (0.90, 1.60),
        (0.96, 1.60),
        (0.97, 2.25),
        (1.00, 2.25),
    ],
)
def test_scarcity_multiplier_bands(utilization: float, expected: float) -> None:
    assert scarcity_multiplier(utilization) == expected


@pytest.mark.parametrize(
    ("lines_requested", "expected"),
    [(1, 1.00), (2, 1.15), (3, 1.35), (4, 1.75)],
)
def test_parallelism_multiplier_for_four_line_factory(
    lines_requested: int, expected: float
) -> None:
    # The three sample scenarios (1x4, 2x2, 4x1) map to 1.00, 1.15, 1.75.
    assert parallelism_multiplier(lines_requested, total_lines=4) == expected


@pytest.mark.parametrize(
    ("complexity", "expected"),
    [("low", 0.85), ("medium", 1.00), ("high", 1.35), ("extreme", 1.80)],
)
def test_retooling_multiplier_table(complexity: str, expected: float) -> None:
    assert retooling_multiplier(complexity) == expected


def test_target_quote_marks_up_floor_to_hit_margin() -> None:
    # A 35% margin turns a 1,300,000 floor into 1,300,000 / 0.65 = 2,000,000.
    assert target_quote(1_300_000.0, 0.35) == pytest.approx(2_000_000.0)


def test_target_quote_equals_floor_at_zero_margin() -> None:
    assert target_quote(1_234_567.0, 0.0) == 1_234_567.0


def test_expedited_quote_applies_parallelism_scaled_premium() -> None:
    # base 1,000,000 * (1 + 0.10 * 1.75) = 1,175,000
    assert expedited_quote(1_000_000.0, 0.10, 1.75) == pytest.approx(1_175_000.0)


# --- Deterministic scheduler line-week formula ------------------------------


def _scenario(lines: int) -> JobScenario:
    return JobScenario(
        name=f"{lines} lines",
        lines_requested=lines,
        production_weeks=1,
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
        expedite_willingness_to_pay=0.10,
        retooling_complexity="medium",
    )


def test_proposed_job_line_weeks_for_four_line_scenario() -> None:
    # 4 * (1.5 tooling + 0.75 debug + 1 production) = 13.0 line-weeks.
    row = proposed_job_to_backlog_row(_scenario(lines=4))
    assert row["required_line_weeks"] == 13.0


# --- Hand-computed multi-job scheduler cases --------------------------------


def test_single_line_three_job_schedule_is_hand_verifiable() -> None:
    # One line, so jobs run strictly in priority order and cannot overlap.
    # HIGH(p5, 2lw), MED(p3, 1lw), LOW(p1, 3lw) run in that order:
    #   HIGH: weeks 1-2 -> completes week 2, due 1 -> 1 late  -> penalty 100k
    #   MED : week 3    -> completes week 3, due 5 -> on time -> penalty 0
    #   LOW : weeks 4-6 -> completes week 6, due 2 -> 4 late  -> penalty 100k
    backlog = pd.DataFrame(
        [
            dict(
                job_id="HIGH",
                customer="x",
                required_line_weeks=2.0,
                margin_value=1_000_000,
                due_week=1,
                late_penalty_per_week=100_000,
                priority=5,
            ),
            dict(
                job_id="MED",
                customer="y",
                required_line_weeks=1.0,
                margin_value=500_000,
                due_week=5,
                late_penalty_per_week=50_000,
                priority=3,
            ),
            dict(
                job_id="LOW",
                customer="z",
                required_line_weeks=3.0,
                margin_value=300_000,
                due_week=2,
                late_penalty_per_week=25_000,
                priority=1,
            ),
        ]
    )
    result = schedule_backlog(backlog, n_lines=1, planning_horizon_weeks=12).set_index("job_id")

    assert result.loc["HIGH", "completion_week"] == 2
    assert result.loc["HIGH", "lateness_weeks"] == 1
    assert result.loc["HIGH", "late_penalty"] == 100_000
    assert result.loc["HIGH", "net_value"] == 900_000

    assert result.loc["MED", "completion_week"] == 3
    assert result.loc["MED", "lateness_weeks"] == 0
    assert result.loc["MED", "late_penalty"] == 0
    assert result.loc["MED", "net_value"] == 500_000

    assert result.loc["LOW", "completion_week"] == 6
    assert result.loc["LOW", "lateness_weeks"] == 4
    assert result.loc["LOW", "late_penalty"] == 100_000
    assert result.loc["LOW", "net_value"] == 200_000


def test_two_line_job_consumes_capacity_within_a_week() -> None:
    # A single 3.0 line-week job on a 2-line factory fills week 1 (2 line-weeks)
    # and 1 line-week of week 2, completing in week 2.
    backlog = pd.DataFrame(
        [
            dict(
                job_id="J",
                customer="x",
                required_line_weeks=3.0,
                margin_value=600_000,
                due_week=1,
                late_penalty_per_week=100_000,
                priority=1,
            )
        ]
    )
    row = schedule_backlog(backlog, n_lines=2, planning_horizon_weeks=12).iloc[0]
    assert row["completion_week"] == 2
    assert row["lateness_weeks"] == 1
    assert row["late_penalty"] == 100_000
    assert row["net_value"] == 500_000


def test_two_line_two_job_concurrent_schedule() -> None:
    # Two lines let both jobs start in week 1.
    #   A(p5, 3lw): week1 takes 2, week2 takes 1 -> completes week 2
    #   B(p3, 2lw): week1 has 0 left, week2 takes 1, week3 takes 1 -> completes week 3
    backlog = pd.DataFrame(
        [
            dict(
                job_id="A",
                customer="x",
                required_line_weeks=3.0,
                margin_value=1_000_000,
                due_week=1,
                late_penalty_per_week=100_000,
                priority=5,
            ),
            dict(
                job_id="B",
                customer="y",
                required_line_weeks=2.0,
                margin_value=500_000,
                due_week=2,
                late_penalty_per_week=50_000,
                priority=3,
            ),
        ]
    )
    result = schedule_backlog(backlog, n_lines=2, planning_horizon_weeks=12).set_index("job_id")
    assert result.loc["A", "completion_week"] == 2
    assert result.loc["A", "late_penalty"] == 100_000
    assert result.loc["B", "completion_week"] == 3
    assert result.loc["B", "lateness_weeks"] == 1
    assert result.loc["B", "late_penalty"] == 50_000


# --- Seeded Monte Carlo snapshot -------------------------------------------

# Snapshot of suggested quotes for the three sample scenarios at seed 42 with
# n_sims=20000. These were reproduced from a clean run of the sealed core and
# are exact under the same NumPy/pandas versions. Sanity band (documented): each
# target quote sits in single-digit millions to low tens of millions, and the
# quotes strictly increase from economy to expedited (see the ordering test).
GOLDEN_TARGET_QUOTES = {
    "Economy: 1 line x 4 weeks": 6_005_116.834671878,
    "Standard: 2 lines x 2 weeks": 8_531_837.318394935,
    "Expedited: 4 lines x 1 week": 16_846_772.20753684,
}
GOLDEN_EXPEDITED_QUOTES = {
    "Economy: 1 line x 4 weeks": 6_005_116.834671878,
    "Standard: 2 lines x 2 weeks": 9_022_417.964202644,
    "Expedited: 4 lines x 1 week": 19_794_957.343855787,
}


def test_seeded_monte_carlo_snapshot_matches_golden_quotes(
    scenarios: list[JobScenario],
    config: FoundryConfig,
    settings: SimulationSettings,
) -> None:
    assert settings.random_seed == 42
    assert settings.n_sims == 20000

    results = simulate_many(scenarios, config, settings)
    summary = summarize_results(results, config, scenarios)

    for _, row in summary.iterrows():
        name = row["scenario"]
        assert row["suggested_target_quote"] == pytest.approx(GOLDEN_TARGET_QUOTES[name], rel=1e-6)
        assert row["suggested_expedited_quote"] == pytest.approx(
            GOLDEN_EXPEDITED_QUOTES[name], rel=1e-6
        )
        # Documented sanity band: quotes are realistic multi-million-dollar
        # figures, never negative or absurdly large.
        assert 1_000_000 < row["suggested_target_quote"] < 100_000_000


def test_snapshot_multipliers_match_sample_scenarios(
    scenarios: list[JobScenario],
    config: FoundryConfig,
    settings: SimulationSettings,
) -> None:
    results = simulate_many(scenarios, config, settings)
    summary = summarize_results(results, config, scenarios).set_index("scenario")

    # Every scenario runs at 0.88 utilization -> scarcity 1.25, medium retool 1.00.
    for name in GOLDEN_TARGET_QUOTES:
        assert summary.loc[name, "scarcity_multiplier"] == 1.25
        assert summary.loc[name, "retooling_multiplier"] == 1.00

    assert summary.loc["Economy: 1 line x 4 weeks", "parallelism_multiplier"] == 1.00
    assert summary.loc["Standard: 2 lines x 2 weeks", "parallelism_multiplier"] == 1.15
    assert summary.loc["Expedited: 4 lines x 1 week", "parallelism_multiplier"] == 1.75


def test_target_quote_ordering_economy_standard_expedited(
    scenarios: list[JobScenario],
    config: FoundryConfig,
    settings: SimulationSettings,
) -> None:
    results = simulate_many(scenarios, config, settings)
    summary = summarize_results(results, config, scenarios).set_index("scenario")

    economy = summary.loc["Economy: 1 line x 4 weeks", "suggested_target_quote"]
    standard = summary.loc["Standard: 2 lines x 2 weeks", "suggested_target_quote"]
    expedited = summary.loc["Expedited: 4 lines x 1 week", "suggested_target_quote"]

    # Concentrating the same line-weeks into fewer weeks costs more.
    assert economy < standard < expedited

    # The expedited *expedited* quote also dominates the standard expedited quote.
    exp_economy = summary.loc["Economy: 1 line x 4 weeks", "suggested_expedited_quote"]
    exp_expedited = summary.loc["Expedited: 4 lines x 1 week", "suggested_expedited_quote"]
    assert exp_expedited > exp_economy
