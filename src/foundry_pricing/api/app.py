"""FastAPI application exposing the foundry pricing engine over HTTP.

Run locally with::

    uvicorn foundry_pricing.api.app:app --host 0.0.0.0 --port 8000

The app is intentionally thin: each route delegates to :mod:`services`, which
calls the core engine and shapes the response. CORS is fully permissive because
this is a local analytics tool meant to be driven by the Next.js dev server, not
a public service.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import services
from .schemas import (
    ConfigDefaultResponse,
    HealthResponse,
    ScenariosSampleResponse,
    ScheduleRequest,
    ScheduleResponse,
    SimulateRequest,
    SimulateResponse,
)

app = FastAPI(
    title="Foundry Pricing API",
    version="0.1.0",
    summary="Monte Carlo pricing and capacity scheduling for a foundry-style business.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_errors(errors: Sequence[Any]) -> str:
    """Collapse pydantic error records into one readable sentence."""
    parts: list[str] = []
    for err in errors:
        location = err.get("loc", ())
        # Drop the leading "body" element for a cleaner field path.
        fields = [str(p) for p in location if p != "body"]
        where = ".".join(fields) if fields else "request"
        parts.append(f"{where}: {err.get('msg', 'invalid value')}")
    return "; ".join(parts) if parts else "Invalid request."


@app.exception_handler(RequestValidationError)
async def _handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a single readable 422 detail instead of the raw error list."""
    return JSONResponse(status_code=422, content={"detail": _format_errors(exc.errors())})


@app.exception_handler(ValidationError)
async def _handle_validation(_: Request, exc: ValidationError) -> JSONResponse:
    """Surface model validation raised inside services as a 422."""
    return JSONResponse(status_code=422, content={"detail": _format_errors(exc.errors())})


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(status="ok")


@app.get("/api/config/default", response_model=ConfigDefaultResponse)
def config_default() -> ConfigDefaultResponse:
    """Return the bundled default factory config and Monte Carlo settings."""
    return services.get_default_config()


@app.get("/api/scenarios/sample", response_model=ScenariosSampleResponse)
def scenarios_sample() -> ScenariosSampleResponse:
    """Return the bundled sample scenarios."""
    return services.get_sample_scenarios()


@app.post("/api/simulate", response_model=SimulateResponse)
def simulate(request: SimulateRequest) -> SimulateResponse:
    """Run the Monte Carlo simulation and return summary, histograms, explanations."""
    return services.run_simulation(request)


@app.post("/api/schedule", response_model=ScheduleResponse)
def schedule(request: ScheduleRequest) -> ScheduleResponse:
    """Schedule the backlog and, if a scenario is supplied, price its opportunity cost."""
    return services.run_schedule(request)
