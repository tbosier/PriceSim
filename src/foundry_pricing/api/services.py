"""Glue between the HTTP layer and the core engine.

Every function here translates a validated request into core calls and shapes the
result for JSON. No pricing or scheduling logic lives here; it all comes from
:mod:`foundry_pricing.simulation` and :mod:`foundry_pricing.scheduling`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..config import load_config, load_scenarios
from ..models import FoundryConfig, JobScenario
from ..scheduling import estimate_schedule_opportunity_cost, schedule_backlog
from ..simulation import simulate_many, summarize_results
from .schemas import (
    BacklogItem,
    ConfigDefaultResponse,
    Histogram,
    OpportunityCost,
    ScenarioDistributions,
    ScenariosSampleResponse,
    ScheduleRequest,
    ScheduleResponse,
    SimulateRequest,
    SimulateResponse,
)

# Number of histogram bins returned per distribution.
DEFAULT_BINS = 40

_DEFAULT_CONFIG_RELPATH = Path("configs/default.yml")
_SAMPLE_SCENARIOS_RELPATH = Path("data/sample/scenarios.yml")


def find_repo_root() -> Path:
    """Locate the repo root so config and data files resolve anywhere.

    Prefers the ``FOUNDRY_DATA_DIR`` environment variable (useful in a container
    where the working dir is ``/app``); otherwise walks up from this file until it
    finds a directory containing ``pyproject.toml``.

    Returns:
        The resolved repo root directory.

    Raises:
        RuntimeError: If no ``pyproject.toml`` is found walking up.
    """
    env_dir = os.environ.get("FOUNDRY_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError(
        "Could not locate the repo root (no pyproject.toml found). "
        "Set FOUNDRY_DATA_DIR to the directory holding configs/ and data/."
    )


def default_config_path() -> Path:
    """Absolute path to ``configs/default.yml``."""
    return find_repo_root() / _DEFAULT_CONFIG_RELPATH


def sample_scenarios_path() -> Path:
    """Absolute path to ``data/sample/scenarios.yml``."""
    return find_repo_root() / _SAMPLE_SCENARIOS_RELPATH


def get_default_config() -> ConfigDefaultResponse:
    """Load the bundled default factory config and Monte Carlo settings."""
    config, settings = load_config(default_config_path())
    return ConfigDefaultResponse(foundry=config, simulation=settings)


def get_sample_scenarios() -> ScenariosSampleResponse:
    """Load the bundled sample scenarios, validated against the default factory."""
    config, _ = load_config(default_config_path())
    scenarios = load_scenarios(sample_scenarios_path(), config)
    return ScenariosSampleResponse(scenarios=scenarios)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to JSON-native records (numpy scalars -> python)."""
    result: list[dict[str, Any]] = json.loads(frame.to_json(orient="records"))
    return result


def _histogram(values: np.ndarray, bins: int = DEFAULT_BINS) -> Histogram:
    """Bin a 1-D array with ``numpy.histogram`` into a wire-ready histogram."""
    counts, bin_edges = np.histogram(values, bins=bins)
    return Histogram(
        bin_edges=[float(edge) for edge in bin_edges],
        counts=[int(count) for count in counts],
    )


def _explain(scenario: JobScenario, config: FoundryConfig, row: dict[str, Any]) -> str:
    """Build a plain-English explanation that names the actual numbers."""
    util_pct = round(config.current_utilization * 100)
    return (
        f"This scenario reserves {scenario.lines_requested} of {config.n_lines} lines, "
        f"so the parallelism multiplier is {row['parallelism_multiplier']:.2f}. "
        f"At {util_pct}% utilization the scarcity multiplier is {row['scarcity_multiplier']:.2f}, "
        f"and {scenario.retooling_complexity} retooling applies a "
        f"{row['retooling_multiplier']:.2f}x tooling multiplier. "
        f"The suggested target quote is ${row['suggested_target_quote']:,.0f}, "
        f"which holds a {row['avg_margin_at_target'] * 100:.0f}% average margin "
        f"and a {row['p10_margin_at_target'] * 100:.0f}% margin in the worst 10% of outcomes."
    )


def _validate_scenarios(scenarios: list[JobScenario], config: FoundryConfig) -> list[JobScenario]:
    """Re-check scenarios against the factory line count.

    FastAPI validates each scenario in isolation; this re-runs validation with the
    ``n_lines`` context so a job that requests more lines than the factory has
    surfaces as a 422 instead of silently over-booking capacity.
    """
    context = {"n_lines": config.n_lines}
    return [JobScenario.model_validate(s.model_dump(), context=context) for s in scenarios]


def run_simulation(request: SimulateRequest) -> SimulateResponse:
    """Run the Monte Carlo simulation and shape the response for the frontend."""
    config = request.foundry
    settings = request.simulation
    scenarios = _validate_scenarios(request.scenarios, config)

    results = simulate_many(scenarios, config, settings)
    summary = summarize_results(results, config, scenarios)
    summary_rows = _records(summary)
    rows_by_name = {row["scenario"]: row for row in summary_rows}

    distributions: dict[str, ScenarioDistributions] = {}
    explanations: dict[str, str] = {}
    for scenario in scenarios:
        group = results[results["scenario"] == scenario.name]
        distributions[scenario.name] = ScenarioDistributions(
            economic_floor=_histogram(group["economic_floor"].to_numpy()),
            margin_at_target=_histogram(group["realized_margin_at_target"].to_numpy()),
        )
        explanations[scenario.name] = _explain(scenario, config, rows_by_name[scenario.name])

    return SimulateResponse(
        summary=summary_rows,
        distributions=distributions,
        explanations=explanations,
    )


def _backlog_frame(backlog: list[BacklogItem]) -> pd.DataFrame:
    """Turn the request backlog into the DataFrame the scheduler expects."""
    return pd.DataFrame([item.model_dump() for item in backlog])


def run_schedule(request: ScheduleRequest) -> ScheduleResponse:
    """Schedule the backlog and, if a scenario is given, price its opportunity cost."""
    config = request.foundry
    backlog = _backlog_frame(request.backlog)

    schedule = schedule_backlog(backlog, config.n_lines, request.planning_horizon_weeks)

    opportunity_cost: OpportunityCost | None = None
    if request.scenario is not None:
        estimate = estimate_schedule_opportunity_cost(
            backlog,
            request.scenario,
            config,
            planning_horizon_weeks=request.planning_horizon_weeks,
        )
        opportunity_cost = OpportunityCost(
            opportunity_cost_from_schedule=estimate["opportunity_cost_from_schedule"],
            total_net_value_without=estimate["total_net_value_without"],
            total_net_value_with=estimate["total_net_value_with"],
            delayed_jobs=estimate["delayed_jobs"],
        )

    return ScheduleResponse(schedule=_records(schedule), opportunity_cost=opportunity_cost)
