"""Vectorized Monte Carlo simulation engine.

For each scenario we draw ``n_sims`` correlated cost outcomes, roll them up into
an economic floor per iteration, then price a quote off a risk percentile of
that floor distribution. Everything is vectorized with NumPy so tens of
thousands of iterations run in milliseconds, and every draw is seeded so results
are reproducible.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from .distributions import sample_downtime_hours, truncated_normal
from .models import FoundryConfig, JobScenario, SimulationSettings
from .pricing import (
    expedited_quote,
    parallelism_multiplier,
    retooling_multiplier,
    scarcity_multiplier,
    target_quote,
)

# Column order for the per-iteration results DataFrame. Kept explicit so the
# reporting, plotting, and API layers can rely on a stable schema.
RESULT_COLUMNS: Final[tuple[str, ...]] = (
    "scenario",
    "iteration",
    "tooling_weeks",
    "debug_weeks",
    "engineering_hours",
    "tooling_parts_cost",
    "effective_yield",
    "good_units",
    "downtime_hours",
    "reserved_line_hours",
    "production_line_hours",
    "direct_capacity_cost",
    "engineering_cost",
    "variable_production_cost",
    "adjusted_tooling_parts_cost",
    "direct_cost",
    "opportunity_cost",
    "economic_floor",
    "target_quote",
    "expedited_quote",
    "realized_margin_at_target",
    "realized_margin_at_expedited",
    "scarcity_multiplier",
    "parallelism_multiplier",
    "retooling_multiplier",
)


def simulate_scenario(
    scenario: JobScenario,
    config: FoundryConfig,
    settings: SimulationSettings,
) -> pd.DataFrame:
    """Run the Monte Carlo simulation for a single scenario.

    Args:
        scenario: The job being quoted.
        config: Factory configuration.
        settings: Monte Carlo controls (iteration count and seed).

    Returns:
        A DataFrame with one row per iteration and columns ``RESULT_COLUMNS``.
    """
    rng = np.random.default_rng(settings.random_seed)
    n = settings.n_sims

    # --- Random draws -------------------------------------------------------
    tooling_weeks = truncated_normal(
        rng, scenario.tooling_weeks_mean, scenario.tooling_weeks_sd, n, lower=0.1
    )
    debug_weeks = truncated_normal(
        rng, scenario.debug_weeks_mean, scenario.debug_weeks_sd, n, lower=0.0
    )
    engineering_hours = truncated_normal(
        rng, scenario.engineering_hours_mean, scenario.engineering_hours_sd, n, lower=0.0
    )
    tooling_parts_cost = truncated_normal(
        rng, scenario.tooling_parts_cost_mean, scenario.tooling_parts_cost_sd, n, lower=0.0
    )
    effective_yield = rng.beta(scenario.yield_alpha, scenario.yield_beta, size=n)
    downtime_hours = sample_downtime_hours(
        rng,
        probability=config.downtime_probability,
        mean=config.downtime_hours_mean,
        sd=config.downtime_hours_sd,
        size=n,
    )

    # --- Deterministic multipliers -----------------------------------------
    scarcity = scarcity_multiplier(config.current_utilization)
    parallelism = parallelism_multiplier(scenario.lines_requested, config.n_lines)
    retooling = retooling_multiplier(scenario.retooling_complexity)

    # --- Capacity and cost roll-up -----------------------------------------
    good_units = scenario.expected_units * effective_yield
    reserved_line_hours = (
        scenario.lines_requested
        * (tooling_weeks + debug_weeks + scenario.production_weeks)
        * config.hours_per_line_week
        + downtime_hours
    )
    production_line_hours = (
        scenario.lines_requested * scenario.production_weeks * config.hours_per_line_week
    )

    direct_capacity_cost = reserved_line_hours * config.base_line_hour_cost
    engineering_cost = engineering_hours * config.engineering_hour_cost
    variable_production_cost = good_units * scenario.variable_cost_per_unit
    adjusted_tooling_parts_cost = tooling_parts_cost * retooling

    direct_cost = (
        direct_capacity_cost
        + engineering_cost
        + variable_production_cost
        + adjusted_tooling_parts_cost
    )

    opportunity_cost = (
        reserved_line_hours
        * config.base_line_hour_value
        * scarcity
        * parallelism
        * config.current_utilization
    )

    economic_floor = direct_cost + opportunity_cost

    # --- Quote: price off a risk percentile of the floor distribution -------
    risk_floor = float(np.quantile(economic_floor, config.risk_percentile))
    tq = target_quote(risk_floor, config.target_margin)
    eq = expedited_quote(tq, scenario.expedite_willingness_to_pay, parallelism)

    realized_margin_at_target = (tq - direct_cost) / tq
    realized_margin_at_expedited = (eq - direct_cost) / eq

    frame = pd.DataFrame(
        {
            "scenario": scenario.name,
            "iteration": np.arange(n, dtype=np.int64),
            "tooling_weeks": tooling_weeks,
            "debug_weeks": debug_weeks,
            "engineering_hours": engineering_hours,
            "tooling_parts_cost": tooling_parts_cost,
            "effective_yield": effective_yield,
            "good_units": good_units,
            "downtime_hours": downtime_hours,
            "reserved_line_hours": reserved_line_hours,
            "production_line_hours": production_line_hours,
            "direct_capacity_cost": direct_capacity_cost,
            "engineering_cost": engineering_cost,
            "variable_production_cost": variable_production_cost,
            "adjusted_tooling_parts_cost": adjusted_tooling_parts_cost,
            "direct_cost": direct_cost,
            "opportunity_cost": opportunity_cost,
            "economic_floor": economic_floor,
            "target_quote": tq,
            "expedited_quote": eq,
            "realized_margin_at_target": realized_margin_at_target,
            "realized_margin_at_expedited": realized_margin_at_expedited,
            "scarcity_multiplier": scarcity,
            "parallelism_multiplier": parallelism,
            "retooling_multiplier": retooling,
        }
    )
    return frame[list(RESULT_COLUMNS)]


def simulate_many(
    scenarios: list[JobScenario],
    config: FoundryConfig,
    settings: SimulationSettings,
) -> pd.DataFrame:
    """Run the simulation for every scenario and stack the results.

    Each scenario draws from an independent but deterministic random stream
    (base seed offset by scenario index), so results are reproducible and
    scenarios do not share the exact same noise.

    Args:
        scenarios: Scenarios to simulate.
        config: Factory configuration.
        settings: Monte Carlo controls.

    Returns:
        A single DataFrame with ``n_sims * len(scenarios)`` rows.
    """
    frames: list[pd.DataFrame] = []
    for index, scenario in enumerate(scenarios):
        scenario_settings = settings.model_copy(
            update={"random_seed": settings.random_seed + index}
        )
        frames.append(simulate_scenario(scenario, config, scenario_settings))
    return pd.concat(frames, ignore_index=True)


def summarize_results(
    results: pd.DataFrame,
    config: FoundryConfig,
    scenarios: list[JobScenario],
) -> pd.DataFrame:
    """Collapse per-iteration results into one explainable row per scenario.

    Args:
        results: Output of :func:`simulate_many` (or :func:`simulate_scenario`).
        config: Factory configuration (unused today, kept for future fields
            and a stable summarization signature).
        scenarios: Scenarios in the desired output order.

    Returns:
        A summary DataFrame, one row per scenario, ordered like ``scenarios``.
    """
    order = [s.name for s in scenarios]
    rows: list[dict[str, object]] = []
    for name in order:
        g = results[results["scenario"] == name]
        rows.append(
            {
                "scenario": name,
                "avg_tooling_weeks": g["tooling_weeks"].mean(),
                "p80_tooling_weeks": g["tooling_weeks"].quantile(0.80),
                "avg_debug_weeks": g["debug_weeks"].mean(),
                "avg_reserved_line_hours": g["reserved_line_hours"].mean(),
                "avg_direct_cost": g["direct_cost"].mean(),
                "avg_opportunity_cost": g["opportunity_cost"].mean(),
                "p50_economic_floor": g["economic_floor"].quantile(0.50),
                "p80_economic_floor": g["economic_floor"].quantile(0.80),
                "p90_economic_floor": g["economic_floor"].quantile(0.90),
                "suggested_target_quote": g["target_quote"].iloc[0],
                "suggested_expedited_quote": g["expedited_quote"].iloc[0],
                "avg_margin_at_target": g["realized_margin_at_target"].mean(),
                "p10_margin_at_target": g["realized_margin_at_target"].quantile(0.10),
                "scarcity_multiplier": g["scarcity_multiplier"].iloc[0],
                "parallelism_multiplier": g["parallelism_multiplier"].iloc[0],
                "retooling_multiplier": g["retooling_multiplier"].iloc[0],
            }
        )
    return pd.DataFrame(rows)
