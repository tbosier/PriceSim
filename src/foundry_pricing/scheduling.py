"""Lightweight, deterministic backlog scheduler.

The scheduler answers a diagnostic question: if we accept a proposed job, which
backlog jobs slip, and what does that slippage cost us? It uses a simple greedy
fill over weekly capacity buckets. This is intentionally not an optimal solver;
the architecture leaves room to drop in OR-Tools later without touching callers.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .models import FoundryConfig, JobScenario

# Sort key: highest priority first, then earliest due, then most valuable.
_SORT_COLUMNS = ["priority", "due_week", "margin_value"]
_SORT_ASCENDING = [False, True, False]

# Tolerance for fractional line-week bookkeeping.
_EPS = 1e-9


def schedule_backlog(
    backlog: pd.DataFrame,
    n_lines: int,
    planning_horizon_weeks: int,
) -> pd.DataFrame:
    """Greedily assign jobs to the earliest available line-week capacity.

    Each week offers ``n_lines`` line-weeks of capacity. Jobs are placed in
    priority order and consume capacity from the earliest weeks first. A job's
    completion week is the last week it consumes any capacity. Weeks beyond the
    nominal horizon still exist (with full capacity) so every job schedules and
    lateness can accrue past the horizon rather than silently dropping a job.

    Args:
        backlog: Rows with at least ``job_id, required_line_weeks, margin_value,
            due_week, late_penalty_per_week, priority``.
        n_lines: Line-weeks of capacity available per week.
        planning_horizon_weeks: Nominal planning window (used to size the grid).

    Returns:
        The backlog with ``completion_week, lateness_weeks, late_penalty,
        net_value`` columns appended, in scheduled order.
    """
    ordered = backlog.sort_values(
        _SORT_COLUMNS, ascending=_SORT_ASCENDING, kind="stable"
    ).reset_index(drop=True)

    # Capacity remaining per week; grows on demand beyond the horizon.
    capacity: dict[int, float] = {w: float(n_lines) for w in range(1, planning_horizon_weeks + 1)}

    completion_weeks: list[int] = []
    for _, job in ordered.iterrows():
        remaining = float(job["required_line_weeks"])
        week = 1
        completion = 1
        while remaining > _EPS:
            available = capacity.setdefault(week, float(n_lines))
            take = min(available, remaining)
            if take > _EPS:
                capacity[week] = available - take
                remaining -= take
                completion = week
            week += 1
        completion_weeks.append(completion)

    ordered["completion_week"] = completion_weeks
    ordered["lateness_weeks"] = (ordered["completion_week"] - ordered["due_week"]).clip(lower=0)
    ordered["late_penalty"] = ordered["lateness_weeks"] * ordered["late_penalty_per_week"]
    ordered["net_value"] = ordered["margin_value"] - ordered["late_penalty"]
    return ordered


def proposed_job_to_backlog_row(scenario: JobScenario) -> dict[str, Any]:
    """Translate a quoting scenario into an equivalent backlog capacity request.

    The proposed job is modeled purely as capacity consumption:

        required_line_weeks = lines_requested *
            (tooling_weeks_mean + debug_weeks_mean + production_weeks)

    Args:
        scenario: The job being quoted.

    Returns:
        A backlog-shaped row dict for the proposed job.
    """
    required_line_weeks = scenario.lines_requested * (
        scenario.tooling_weeks_mean + scenario.debug_weeks_mean + scenario.production_weeks
    )
    return {
        "job_id": "PROPOSED",
        "customer": scenario.name,
        "required_line_weeks": float(required_line_weeks),
        "margin_value": 0.0,  # excluded from backlog value totals below
        "due_week": 1,
        "late_penalty_per_week": 0.0,
        "priority": 99,  # jump the queue so it displaces existing backlog jobs
    }


def estimate_schedule_opportunity_cost(
    backlog: pd.DataFrame,
    scenario: JobScenario,
    config: FoundryConfig,
    planning_horizon_weeks: int = 12,
) -> dict[str, Any]:
    """Estimate opportunity cost of accepting a job by comparing schedules.

    We schedule the backlog with and without the proposed job (which jumps the
    queue) and measure how much net value the existing backlog loses to the
    extra delay:

        opportunity_cost = net_value_without_proposed - net_value_with_proposed

    Args:
        backlog: The existing backlog.
        scenario: The proposed job.
        config: Factory configuration (supplies ``n_lines``).
        planning_horizon_weeks: Planning window passed to the scheduler.

    Returns:
        A dict with the opportunity cost, both net-value totals, the delayed
        jobs, and both schedule tables for inspection.
    """
    without = schedule_backlog(backlog, config.n_lines, planning_horizon_weeks)
    total_without = float(without["net_value"].sum())

    augmented = pd.concat(
        [backlog, pd.DataFrame([proposed_job_to_backlog_row(scenario)])], ignore_index=True
    )
    with_proposed = schedule_backlog(augmented, config.n_lines, planning_horizon_weeks)

    # Compare only the original backlog jobs; the proposed job's own value is not
    # part of the backlog we might displace.
    original_ids = set(backlog["job_id"])
    with_backlog_only = with_proposed[with_proposed["job_id"].isin(original_ids)]
    total_with = float(with_backlog_only["net_value"].sum())

    # Jobs whose completion week moved later once the proposed job was inserted.
    before = without.set_index("job_id")["completion_week"]
    after = with_backlog_only.set_index("job_id")["completion_week"]
    delayed_jobs = [
        {
            "job_id": job_id,
            "completion_without": int(before[job_id]),
            "completion_with": int(after[job_id]),
            "weeks_delayed": int(after[job_id] - before[job_id]),
        }
        for job_id in original_ids
        if after[job_id] > before[job_id]
    ]

    return {
        "opportunity_cost_from_schedule": total_without - total_with,
        "total_net_value_without": total_without,
        "total_net_value_with": total_with,
        "delayed_jobs": delayed_jobs,
        "schedule_without": without,
        "schedule_with": with_proposed,
    }
