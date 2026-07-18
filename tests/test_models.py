"""Tests for Pydantic input models and their validation rules."""

import pytest
from pydantic import ValidationError

from foundry_pricing.models import FoundryConfig, JobScenario, SimulationSettings


def _valid_config_kwargs() -> dict[str, float | int]:
    return dict(
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


def _valid_scenario_kwargs() -> dict[str, object]:
    return dict(
        name="Standard: 2 lines x 2 weeks",
        lines_requested=2,
        production_weeks=2,
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
        expedite_willingness_to_pay=0.05,
        retooling_complexity="medium",
    )


def test_valid_config_constructs() -> None:
    cfg = FoundryConfig(**_valid_config_kwargs())
    assert cfg.n_lines == 4


def test_valid_scenario_constructs() -> None:
    scn = JobScenario(**_valid_scenario_kwargs())
    assert scn.lines_requested == 2


@pytest.mark.parametrize("bad_util", [-0.1, 1.1])
def test_invalid_utilization_fails(bad_util: float) -> None:
    with pytest.raises(ValidationError):
        FoundryConfig(**{**_valid_config_kwargs(), "current_utilization": bad_util})


def test_n_lines_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        FoundryConfig(**{**_valid_config_kwargs(), "n_lines": 0})


@pytest.mark.parametrize("bad_margin", [-0.01, 0.96])
def test_target_margin_out_of_range_fails(bad_margin: float) -> None:
    with pytest.raises(ValidationError):
        FoundryConfig(**{**_valid_config_kwargs(), "target_margin": bad_margin})


@pytest.mark.parametrize("bad_pct", [0.49, 0.999])
def test_risk_percentile_out_of_range_fails(bad_pct: float) -> None:
    with pytest.raises(ValidationError):
        FoundryConfig(**{**_valid_config_kwargs(), "risk_percentile": bad_pct})


def test_negative_cost_fails() -> None:
    with pytest.raises(ValidationError):
        FoundryConfig(**{**_valid_config_kwargs(), "base_line_hour_cost": -1})


def test_negative_sd_fails() -> None:
    with pytest.raises(ValidationError):
        JobScenario(**{**_valid_scenario_kwargs(), "tooling_weeks_sd": -0.5})


def test_bad_retooling_complexity_fails() -> None:
    with pytest.raises(ValidationError):
        JobScenario(**{**_valid_scenario_kwargs(), "retooling_complexity": "ludicrous"})


@pytest.mark.parametrize("field", ["yield_alpha", "yield_beta"])
def test_beta_params_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        JobScenario(**{**_valid_scenario_kwargs(), field: 0})


def test_lines_requested_cannot_exceed_available_lines() -> None:
    kwargs = {**_valid_scenario_kwargs(), "lines_requested": 8}
    with pytest.raises(ValidationError):
        JobScenario.model_validate(kwargs, context={"n_lines": 4})


def test_lines_requested_within_available_lines_ok() -> None:
    kwargs = {**_valid_scenario_kwargs(), "lines_requested": 4}
    scn = JobScenario.model_validate(kwargs, context={"n_lines": 4})
    assert scn.lines_requested == 4


def test_simulation_settings_requires_positive_sims() -> None:
    with pytest.raises(ValidationError):
        SimulationSettings(n_sims=0, random_seed=42)
