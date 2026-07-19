"""Request and response models for the REST API.

These wrap the core Pydantic models (:class:`FoundryConfig`, :class:`JobScenario`,
:class:`SimulationSettings`) and add the serialization shapes the frontend expects.
Summary and schedule rows carry mixed string/number columns, so they are typed as
plain dicts rather than a rigid per-column model.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..models import FoundryConfig, JobScenario, SimulationSettings


class HealthResponse(BaseModel):
    """Liveness probe payload."""

    status: str


class ConfigDefaultResponse(BaseModel):
    """The default factory config and Monte Carlo settings."""

    foundry: FoundryConfig
    simulation: SimulationSettings


class ScenariosSampleResponse(BaseModel):
    """The bundled sample scenarios."""

    scenarios: list[JobScenario]


class Histogram(BaseModel):
    """A server-side histogram: ``len(bin_edges) == len(counts) + 1``."""

    bin_edges: list[float]
    counts: list[int]


class ScenarioDistributions(BaseModel):
    """The two distributions charted per scenario."""

    economic_floor: Histogram
    margin_at_target: Histogram


class SimulateRequest(BaseModel):
    """Inputs for a Monte Carlo pricing run."""

    foundry: FoundryConfig
    simulation: SimulationSettings
    scenarios: list[JobScenario] = Field(min_length=1)


class SimulateResponse(BaseModel):
    """Summary rows, per-scenario histograms, and plain-English explanations."""

    summary: list[dict[str, Any]]
    distributions: dict[str, ScenarioDistributions]
    explanations: dict[str, str]


class BacklogItem(BaseModel):
    """One backlog job for the scheduler."""

    model_config = {"extra": "forbid"}

    job_id: str = Field(min_length=1)
    customer: str
    required_line_weeks: float = Field(gt=0)
    margin_value: float
    due_week: int = Field(ge=1)
    late_penalty_per_week: float = Field(ge=0)
    priority: int


class ScheduleRequest(BaseModel):
    """A backlog to schedule, with an optional proposed job to price against it."""

    foundry: FoundryConfig
    backlog: list[BacklogItem] = Field(min_length=1)
    scenario: JobScenario | None = None
    planning_horizon_weeks: int = Field(default=12, ge=1)


class DelayedJob(BaseModel):
    """A backlog job pushed later by inserting the proposed job."""

    job_id: str
    weeks_delayed: int
    completion_without: int
    completion_with: int


class OpportunityCost(BaseModel):
    """What accepting the proposed job costs the existing backlog."""

    opportunity_cost_from_schedule: float
    total_net_value_without: float
    total_net_value_with: float
    delayed_jobs: list[DelayedJob]


class ScheduleResponse(BaseModel):
    """The resolved schedule and, when a scenario was supplied, its opportunity cost."""

    schedule: list[dict[str, Any]]
    opportunity_cost: OpportunityCost | None
