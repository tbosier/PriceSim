"""End-to-end REST API flow test (Task 02).

Walks the real request/response flow with FastAPI's TestClient and asserts the
response shapes match the REST contract in tasks/ORCHESTRATION.md. Gated on the
API module, which lands with Task 02.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

# Gate: skip cleanly until Task 02 (the API) merges.
api_app = pytest.importorskip("foundry_pricing.api.app")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(api_app.app)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_default_exposes_expected_values(client: TestClient) -> None:
    response = client.get("/api/config/default")
    assert response.status_code == 200
    body = response.json()
    assert body["foundry"]["n_lines"] == 4
    assert body["simulation"]["n_sims"] == 20000


def test_scenarios_sample_returns_three(client: TestClient) -> None:
    response = client.get("/api/scenarios/sample")
    assert response.status_code == 200
    scenarios = response.json()["scenarios"]
    assert len(scenarios) == 3


def test_simulate_flow_matches_contract(client: TestClient) -> None:
    # Fetch the documented defaults and post them straight back to /api/simulate.
    config = client.get("/api/config/default").json()
    scenarios = client.get("/api/scenarios/sample").json()["scenarios"]

    payload = {
        "foundry": config["foundry"],
        "simulation": config["simulation"],
        "scenarios": scenarios,
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()

    # One summary row per scenario.
    assert len(body["summary"]) == len(scenarios)

    scenario_names = [s["name"] for s in scenarios]

    # One explanation per scenario, keyed by name.
    assert set(body["explanations"].keys()) == set(scenario_names)
    for text in body["explanations"].values():
        assert isinstance(text, str) and text.strip()

    # Histograms: bin_edges is exactly one longer than counts, for both metrics.
    for name in scenario_names:
        dists = body["distributions"][name]
        for metric in ("economic_floor", "margin_at_target"):
            hist = dists[metric]
            assert len(hist["bin_edges"]) == len(hist["counts"]) + 1
            assert len(hist["counts"]) > 0


def test_simulate_rejects_invalid_config(client: TestClient) -> None:
    config = client.get("/api/config/default").json()
    scenarios = client.get("/api/scenarios/sample").json()["scenarios"]

    bad = dict(config["foundry"])
    bad["current_utilization"] = 2.0  # out of [0, 1]

    payload = {
        "foundry": bad,
        "simulation": config["simulation"],
        "scenarios": scenarios,
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 422


def test_schedule_flow_returns_row_per_job(
    client: TestClient,
    backlog: pd.DataFrame,
) -> None:
    config = client.get("/api/config/default").json()
    scenario = client.get("/api/scenarios/sample").json()["scenarios"][0]

    backlog_rows: list[dict[str, Any]] = backlog.to_dict(orient="records")

    payload = {
        "foundry": config["foundry"],
        "backlog": backlog_rows,
        "scenario": scenario,
    }
    response = client.post("/api/schedule", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()

    # A schedule row for every backlog job.
    assert len(body["schedule"]) == len(backlog_rows)

    # With a scenario supplied, opportunity cost is present and non-negative.
    opp = body["opportunity_cost"]
    assert opp is not None
    assert opp["opportunity_cost_from_schedule"] >= 0


def test_schedule_without_scenario_has_null_opportunity_cost(
    client: TestClient,
    backlog: pd.DataFrame,
) -> None:
    config = client.get("/api/config/default").json()
    backlog_rows: list[dict[str, Any]] = backlog.to_dict(orient="records")

    payload = {
        "foundry": config["foundry"],
        "backlog": backlog_rows,
    }
    response = client.post("/api/schedule", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["opportunity_cost"] is None
