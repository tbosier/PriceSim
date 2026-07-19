# Task 02: FastAPI backend

You are implementing the REST API that wraps the core engine. Read
`tasks/ORCHESTRATION.md` first, especially the REST contract section, which is the
source of truth. The frontend (Task 03) is built against that exact contract, so
match it precisely.

## Scope (files you own)

Work only inside `src/foundry_pricing/api/`. Do not edit any existing core module,
`pyproject.toml`, `__init__.py`, or `README.md`. `fastapi` and `uvicorn[standard]`
are already declared as dependencies.

```
src/foundry_pricing/api/__init__.py
src/foundry_pricing/api/app.py            # FastAPI() app instance named `app`
src/foundry_pricing/api/schemas.py        # Pydantic request/response models
src/foundry_pricing/api/services.py       # thin glue: request -> core calls -> response
tests/test_api.py                         # endpoint tests via httpx/TestClient
```

Run the server with: `uvicorn foundry_pricing.api.app:app --host 0.0.0.0 --port 8000`.

## Endpoints

Implement exactly what the REST contract specifies:

- `GET /api/health` -> `{ "status": "ok" }`
- `GET /api/config/default` -> loads `configs/default.yml` via `load_config`
- `GET /api/scenarios/sample` -> loads `data/sample/scenarios.yml` via `load_scenarios`
- `POST /api/simulate` -> runs `simulate_many` + `summarize_results`, returns the
  summary rows, server-side histograms (default 40 bins) for `economic_floor` and
  `realized_margin_at_target` per scenario, and a plain-English explanation string
  per scenario.
- `POST /api/schedule` -> runs `schedule_backlog`; if a `scenario` is included,
  also runs `estimate_schedule_opportunity_cost`.

## Implementation notes

- Reuse the core functions; do not reimplement any pricing or scheduling logic.
  The API layer is glue plus serialization only.
- Build request/response models in `schemas.py`. Reuse `FoundryConfig`,
  `JobScenario`, and `SimulationSettings` from `foundry_pricing.models` directly
  where possible.
- Compute histograms with `numpy.histogram`. Return `bin_edges` (length n+1) and
  `counts` (length n). Do not return raw per-iteration arrays.
- The explanation string must name the actual numbers, e.g. "reserves 1 of 4
  lines, so the parallelism multiplier is 1.00. At 88% utilization the scarcity
  multiplier is 1.25." Pull the multipliers straight from the summary row.
- Enable permissive CORS for local development (`allow_origins=["*"]`) so the
  Next.js dev server can call the API. This is a local analytics tool, not a
  public service.
- Validation failures from the Pydantic models should surface as HTTP 422 with a
  `detail` message that tells the user what to fix. FastAPI does most of this for
  free; add a clear handler if needed.
- Config and data file paths: resolve them relative to the repo root so the API
  works both locally and inside the container (where the working dir is `/app`).
  A small helper that finds the repo root (walk up for `pyproject.toml`, or read a
  `FOUNDRY_DATA_DIR` env var) is fine.

## Tests (`tests/test_api.py`)

Use `fastapi.testclient.TestClient` (or httpx):
- `/api/health` returns 200 and `{"status": "ok"}`.
- `/api/config/default` returns the expected `n_lines` and `n_sims`.
- `/api/simulate` with the sample payload returns a summary of the right length,
  histograms with `len(bin_edges) == len(counts) + 1`, and one explanation per
  scenario.
- `/api/simulate` with an invalid config (e.g. utilization 2.0) returns 422.
- `/api/schedule` with the sample backlog returns a schedule for every job, and
  with a `scenario` returns a non-negative `opportunity_cost_from_schedule`.

## Definition of done

- `uv run pytest tests/test_api.py` passes.
- `uvicorn foundry_pricing.api.app:app` starts and `curl localhost:8000/api/health`
  returns ok. Verify `/api/simulate` end to end with a real curl call.
- `ruff check .`, `ruff format --check .`, and `mypy src` are clean.
- Commit on your branch and open a draft PR. Do not merge.
