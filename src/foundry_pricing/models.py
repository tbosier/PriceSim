"""Typed, self-validating input models.

These Pydantic v2 models are the single source of truth for what a valid
foundry configuration and job scenario look like. Invalid inputs fail fast at
the boundary with a clear message, so the simulation engine can assume clean
data and stay free of defensive checks.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, model_validator

RetoolingComplexity = Literal["low", "medium", "high", "extreme"]


class FoundryConfig(BaseModel):
    """Physical and commercial parameters of the factory."""

    model_config = {"extra": "forbid"}

    n_lines: int = Field(gt=0, description="Number of production lines.")
    hours_per_line_week: float = Field(gt=0)
    base_line_hour_cost: float = Field(ge=0, description="Cash cost per reserved line-hour.")
    base_line_hour_value: float = Field(ge=0, description="Opportunity value per line-hour.")
    engineering_hour_cost: float = Field(ge=0)
    current_utilization: float = Field(ge=0.0, le=1.0)
    target_margin: float = Field(ge=0.0, le=0.95)
    risk_percentile: float = Field(ge=0.5, le=0.99)
    downtime_probability: float = Field(ge=0.0, le=1.0)
    downtime_hours_mean: float = Field(ge=0.0)
    downtime_hours_sd: float = Field(ge=0.0)


class JobScenario(BaseModel):
    """A single quoting scenario (e.g. ``2 lines x 2 weeks``).

    When validated with ``context={"n_lines": N}`` the model additionally
    enforces that ``lines_requested <= N``. ``config.load_scenarios`` supplies
    that context so scenarios are checked against the active factory.
    """

    model_config = {"extra": "forbid"}

    name: str = Field(min_length=1)
    lines_requested: int = Field(ge=1)
    production_weeks: float = Field(gt=0)
    tooling_weeks_mean: float = Field(ge=0)
    tooling_weeks_sd: float = Field(ge=0)
    debug_weeks_mean: float = Field(ge=0)
    debug_weeks_sd: float = Field(ge=0)
    engineering_hours_mean: float = Field(ge=0)
    engineering_hours_sd: float = Field(ge=0)
    tooling_parts_cost_mean: float = Field(ge=0)
    tooling_parts_cost_sd: float = Field(ge=0)
    expected_units: int = Field(ge=0)
    revenue_per_unit: float = Field(ge=0)
    variable_cost_per_unit: float = Field(ge=0)
    yield_alpha: float = Field(gt=0)
    yield_beta: float = Field(gt=0)
    expedite_willingness_to_pay: float = Field(ge=0)
    retooling_complexity: RetoolingComplexity

    @model_validator(mode="after")
    def _check_lines_against_factory(self, info: ValidationInfo) -> JobScenario:
        """Ensure the job does not request more lines than the factory has."""
        context: dict[str, Any] | None = info.context if isinstance(info.context, dict) else None
        if context is not None and "n_lines" in context:
            n_lines = int(context["n_lines"])
            if self.lines_requested > n_lines:
                raise ValueError(
                    f"Scenario {self.name!r} requests {self.lines_requested} lines "
                    f"but the factory only has {n_lines}."
                )
        return self


class SimulationSettings(BaseModel):
    """Monte Carlo run controls."""

    model_config = {"extra": "forbid"}

    n_sims: int = Field(gt=0, description="Number of Monte Carlo iterations.")
    random_seed: int = Field(ge=0)
