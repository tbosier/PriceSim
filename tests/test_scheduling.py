"""Tests for the greedy backlog scheduler and opportunity-cost estimator."""

import pandas as pd

from foundry_pricing.models import FoundryConfig, JobScenario
from foundry_pricing.scheduling import (
    estimate_schedule_opportunity_cost,
    proposed_job_to_backlog_row,
    schedule_backlog,
)


def _backlog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            dict(
                job_id="B001",
                customer="A",
                required_line_weeks=2.0,
                margin_value=2_100_000,
                due_week=3,
                late_penalty_per_week=150_000,
                priority=3,
            ),
            dict(
                job_id="B002",
                customer="B",
                required_line_weeks=1.5,
                margin_value=900_000,
                due_week=4,
                late_penalty_per_week=75_000,
                priority=2,
            ),
            dict(
                job_id="B003",
                customer="C",
                required_line_weeks=3.0,
                margin_value=4_500_000,
                due_week=6,
                late_penalty_per_week=250_000,
                priority=5,
            ),
        ]
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


def _scenario(lines: int = 4) -> JobScenario:
    return JobScenario(
        name="Expedited: 4 lines x 1 week",
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


def test_scheduler_returns_all_jobs() -> None:
    backlog = _backlog()
    result = schedule_backlog(backlog, n_lines=4, planning_horizon_weeks=12)
    assert len(result) == len(backlog)
    assert set(result["job_id"]) == set(backlog["job_id"])


def test_scheduler_adds_expected_columns() -> None:
    result = schedule_backlog(_backlog(), n_lines=4, planning_horizon_weeks=12)
    for col in ("completion_week", "lateness_weeks", "late_penalty", "net_value"):
        assert col in result.columns


def test_high_priority_completes_before_low_priority_when_constrained() -> None:
    # One line: jobs cannot overlap, so priority decides who goes first.
    backlog = pd.DataFrame(
        [
            dict(
                job_id="LOW",
                customer="x",
                required_line_weeks=2.0,
                margin_value=100,
                due_week=99,
                late_penalty_per_week=1,
                priority=1,
            ),
            dict(
                job_id="HIGH",
                customer="y",
                required_line_weeks=2.0,
                margin_value=100,
                due_week=99,
                late_penalty_per_week=1,
                priority=5,
            ),
        ]
    )
    result = schedule_backlog(backlog, n_lines=1, planning_horizon_weeks=12).set_index("job_id")
    assert result.loc["HIGH", "completion_week"] < result.loc["LOW", "completion_week"]


def test_lateness_and_penalty_are_computed_correctly() -> None:
    # Single line, needs 5 line-weeks -> finishes week 5. Due week 3 -> 2 weeks late.
    backlog = pd.DataFrame(
        [
            dict(
                job_id="J",
                customer="x",
                required_line_weeks=5.0,
                margin_value=1_000_000,
                due_week=3,
                late_penalty_per_week=100_000,
                priority=1,
            ),
        ]
    )
    row = schedule_backlog(backlog, n_lines=1, planning_horizon_weeks=12).iloc[0]
    assert row["completion_week"] == 5
    assert row["lateness_weeks"] == 2
    assert row["late_penalty"] == 200_000
    assert row["net_value"] == 800_000


def test_on_time_job_has_zero_penalty() -> None:
    backlog = pd.DataFrame(
        [
            dict(
                job_id="J",
                customer="x",
                required_line_weeks=2.0,
                margin_value=500_000,
                due_week=5,
                late_penalty_per_week=100_000,
                priority=1,
            ),
        ]
    )
    row = schedule_backlog(backlog, n_lines=1, planning_horizon_weeks=12).iloc[0]
    assert row["completion_week"] == 2
    assert row["lateness_weeks"] == 0
    assert row["late_penalty"] == 0
    assert row["net_value"] == 500_000


def test_proposed_job_row_line_weeks_formula() -> None:
    scn = _scenario(lines=4)
    row = proposed_job_to_backlog_row(scn)
    # 4 * (1.5 + 0.75 + 1) = 13.0 line-weeks
    assert row["required_line_weeks"] == 13.0


def test_inserting_large_proposed_job_does_not_reduce_penalty() -> None:
    backlog = _backlog()
    result = estimate_schedule_opportunity_cost(backlog, _scenario(), _config())
    assert result["opportunity_cost_from_schedule"] >= 0
    assert result["total_net_value_without"] >= result["total_net_value_with"]


def test_opportunity_cost_estimate_has_expected_keys() -> None:
    result = estimate_schedule_opportunity_cost(_backlog(), _scenario(), _config())
    for key in (
        "opportunity_cost_from_schedule",
        "total_net_value_without",
        "total_net_value_with",
        "delayed_jobs",
    ):
        assert key in result
