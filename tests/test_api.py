"""Endpoint tests for the FastAPI backend.

These drive the app through ``TestClient`` and assert on the REST contract shapes:
health, default config, sample scenarios, simulate (summary + histograms +
explanations), validation failures, and schedule (with and without a scenario).
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from foundry_pricing.api.app import app

client = TestClient(app)


def _default_payload() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Fetch the default config and sample scenarios from the API itself."""
    config = client.get("/api/config/default").json()
    scenarios = client.get("/api/scenarios/sample").json()["scenarios"]
    return config["foundry"], config["simulation"], scenarios


def _fast_settings(simulation: dict[str, Any]) -> dict[str, Any]:
    """Shrink the run so tests stay quick while exercising the full path."""
    return {**simulation, "n_sims": 2000}


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_default() -> None:
    response = client.get("/api/config/default")
    assert response.status_code == 200
    body = response.json()
    assert body["foundry"]["n_lines"] == 4
    assert body["simulation"]["n_sims"] == 20000


def test_scenarios_sample() -> None:
    response = client.get("/api/scenarios/sample")
    assert response.status_code == 200
    scenarios = response.json()["scenarios"]
    assert len(scenarios) == 3
    assert scenarios[0]["name"] == "Economy: 1 line x 4 weeks"


def test_simulate_shapes() -> None:
    foundry, simulation, scenarios = _default_payload()
    payload = {
        "foundry": foundry,
        "simulation": _fast_settings(simulation),
        "scenarios": scenarios,
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert len(body["summary"]) == len(scenarios)
    assert len(body["explanations"]) == len(scenarios)

    for scenario in scenarios:
        name = scenario["name"]
        assert name in body["distributions"]
        assert name in body["explanations"]
        dist = body["distributions"][name]
        for metric in ("economic_floor", "margin_at_target"):
            hist = dist[metric]
            assert len(hist["bin_edges"]) == len(hist["counts"]) + 1
        assert "multiplier" in body["explanations"][name]


def test_simulate_summary_has_contract_columns() -> None:
    foundry, simulation, scenarios = _default_payload()
    payload = {
        "foundry": foundry,
        "simulation": _fast_settings(simulation),
        "scenarios": scenarios[:1],
    }
    body = client.post("/api/simulate", json=payload).json()
    row = body["summary"][0]
    for column in (
        "scenario",
        "suggested_target_quote",
        "suggested_expedited_quote",
        "p80_economic_floor",
        "scarcity_multiplier",
        "parallelism_multiplier",
    ):
        assert column in row


def test_simulate_invalid_config_returns_422() -> None:
    foundry, simulation, scenarios = _default_payload()
    foundry = {**foundry, "current_utilization": 2.0}
    payload = {
        "foundry": foundry,
        "simulation": _fast_settings(simulation),
        "scenarios": scenarios,
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_simulate_scenario_over_line_count_returns_422() -> None:
    foundry, simulation, scenarios = _default_payload()
    greedy = {**scenarios[0], "name": "Too many lines", "lines_requested": 99}
    payload = {
        "foundry": foundry,
        "simulation": _fast_settings(simulation),
        "scenarios": [greedy],
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def _sample_backlog() -> list[dict[str, Any]]:
    return [
        {
            "job_id": "B001",
            "customer": "NeuroChip Labs",
            "required_line_weeks": 2.0,
            "margin_value": 2_100_000,
            "due_week": 3,
            "late_penalty_per_week": 150_000,
            "priority": 3,
        },
        {
            "job_id": "B002",
            "customer": "Medical Nano Systems",
            "required_line_weeks": 1.5,
            "margin_value": 900_000,
            "due_week": 4,
            "late_penalty_per_week": 75_000,
            "priority": 2,
        },
        {
            "job_id": "B003",
            "customer": "Defense BioCompute",
            "required_line_weeks": 3.0,
            "margin_value": 4_500_000,
            "due_week": 6,
            "late_penalty_per_week": 250_000,
            "priority": 5,
        },
    ]


def test_schedule_without_scenario() -> None:
    foundry, _, _ = _default_payload()
    backlog = _sample_backlog()
    payload = {"foundry": foundry, "backlog": backlog}
    response = client.post("/api/schedule", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["schedule"]) == len(backlog)
    assert set(row["job_id"] for row in body["schedule"]) == {"B001", "B002", "B003"}
    for row in body["schedule"]:
        for column in ("completion_week", "lateness_weeks", "late_penalty", "net_value"):
            assert column in row
    assert body["opportunity_cost"] is None


def test_schedule_with_scenario_reports_opportunity_cost() -> None:
    foundry, _, scenarios = _default_payload()
    payload = {
        "foundry": foundry,
        "backlog": _sample_backlog(),
        "scenario": scenarios[2],
    }
    response = client.post("/api/schedule", json=payload)
    assert response.status_code == 200
    opp = response.json()["opportunity_cost"]
    assert opp is not None
    assert opp["opportunity_cost_from_schedule"] >= 0
    assert opp["total_net_value_without"] >= opp["total_net_value_with"]
