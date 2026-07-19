# Orchestration plan: foundry-pricing-sim

This file is the map for the parallel build. The core Python engine is already
built, tested, and on `main`. Six independent tasks fan out from it. Each task
has its own markdown file in this folder and owns a disjoint set of files so the
branches merge cleanly.

Read this whole file before starting any task.

## What already exists on `main` (do not modify)

The core simulation engine is complete: 67 passing tests, ruff clean, mypy
strict clean. These modules are the stable base every task builds on. Import
them; do not edit them.

```
src/foundry_pricing/
  __init__.py
  constants.py          # multiplier tables, guardrails
  models.py             # Pydantic v2: FoundryConfig, JobScenario, SimulationSettings
  distributions.py      # truncated_normal, sample_downtime_hours
  pricing.py            # scarcity/parallelism/retooling multipliers, quote formulas
  simulation.py         # simulate_scenario, simulate_many, summarize_results, RESULT_COLUMNS
  scheduling.py         # schedule_backlog, proposed_job_to_backlog_row, estimate_schedule_opportunity_cost
  config.py             # load_config, load_scenarios, load_backlog
  logging_config.py     # setup_logging
tests/                  # test_models, test_pricing, test_distributions, test_simulation, test_scheduling, test_config
configs/                # default.yml, high_utilization.yml, low_utilization.yml
data/sample/            # scenarios.yml, backlog.csv, lines.csv
pyproject.toml          # ALL Python deps already declared (core + CLI + API). Do not edit.
```

### Stable Python API (the surface you import)

```python
from foundry_pricing.config import load_config, load_scenarios, load_backlog
from foundry_pricing.simulation import simulate_many, summarize_results, RESULT_COLUMNS
from foundry_pricing.scheduling import schedule_backlog, estimate_schedule_opportunity_cost
from foundry_pricing.models import FoundryConfig, JobScenario, SimulationSettings

cfg, settings = load_config(Path("configs/default.yml"))
scenarios = load_scenarios(Path("data/sample/scenarios.yml"), cfg)
results = simulate_many(scenarios, cfg, settings)     # tidy DataFrame, RESULT_COLUMNS
summary = summarize_results(results, cfg, scenarios)  # one row per scenario
```

`summarize_results` returns one row per scenario with these columns:

```
scenario, avg_tooling_weeks, p80_tooling_weeks, avg_debug_weeks,
avg_reserved_line_hours, avg_direct_cost, avg_opportunity_cost,
p50_economic_floor, p80_economic_floor, p90_economic_floor,
suggested_target_quote, suggested_expedited_quote,
avg_margin_at_target, p10_margin_at_target,
scarcity_multiplier, parallelism_multiplier, retooling_multiplier
```

Per-iteration `results` columns are in `simulation.RESULT_COLUMNS`. The two most
useful for charts are `economic_floor` and `realized_margin_at_target`.

## Environment

- Python 3.12 (pinned via `uv`). Node 20 for the frontend.
- Set up the Python env once: `uv venv --python 3.12 && uv pip install -e ".[dev]"`.
- Run tests: `uv run pytest`. Lint: `uv run ruff check .`. Types: `uv run mypy src`.

## The six tasks

| # | Task | Owns (files/dirs) | Depends on |
|---|------|-------------------|------------|
| 01 | CLI + reporting + plotting | `src/foundry_pricing/{cli,__main__,reporting,plotting}.py`, `scripts/` | core |
| 02 | FastAPI backend | `src/foundry_pricing/api/` | core |
| 03 | Next.js frontend | `frontend/` | REST contract (below) |
| 04 | Docker + Compose + Makefile | `Dockerfile*`, `docker-compose.yml`, `.dockerignore`, `Makefile`, `.env.example` | 01, 02, 03 exist |
| 05 | README + docs + CI | `README.md`, `docs/`, `.github/`, `.pre-commit-config.yaml` | all |
| 06 | Test + QA hardening | `tests/` (new files only), `tests/integration/` | 01, 02 for integration |

### Conflict rules (important)

- Nobody edits `pyproject.toml`, `__init__.py`, or any existing core module. All
  Python dependencies you need are already declared.
- Task 02 works only inside `src/foundry_pricing/api/`. Task 01 works only on the
  four named files plus `scripts/`. They share the `src/foundry_pricing/` folder
  but never the same file.
- Task 06 adds new test files only. Do not edit the six existing test files.
- `README.md` currently holds a placeholder. Task 05 owns and replaces it. No one
  else touches it.

### Merge order (I, the lead, handle merges)

1. 01 and 02 merge first (pure Python, no cross-deps).
2. 03 merges after 02 (frontend was built against the contract, verified against
   the running backend).
3. 04 merges after 01-03 (needs all services to containerize).
4. 06 merges after 01-02 (integration tests need the CLI and API).
5. 05 merges last (docs describe the finished system).

## REST contract (source of truth for tasks 02 and 03)

The backend runs on `http://localhost:8000`. The frontend calls it at a base URL
from the `NEXT_PUBLIC_API_BASE_URL` env var (default `http://localhost:8000`).
All bodies are JSON. Field names match the Pydantic models exactly.

### `GET /api/health`
```json
{ "status": "ok" }
```

### `GET /api/config/default`
Loads `configs/default.yml`. Response:
```json
{
  "foundry": { "n_lines": 4, "hours_per_line_week": 168, "...": "all FoundryConfig fields" },
  "simulation": { "n_sims": 20000, "random_seed": 42 }
}
```

### `GET /api/scenarios/sample`
Loads `data/sample/scenarios.yml`. Response:
```json
{ "scenarios": [ { "name": "Economy: 1 line x 4 weeks", "...": "all JobScenario fields" } ] }
```

### `POST /api/simulate`
Request:
```json
{
  "foundry": { "...": "FoundryConfig fields" },
  "simulation": { "n_sims": 20000, "random_seed": 42 },
  "scenarios": [ { "...": "JobScenario fields" } ]
}
```
Response:
```json
{
  "summary": [ { "scenario": "...", "suggested_target_quote": 6005117.0, "...": "all summary columns" } ],
  "distributions": {
    "Economy: 1 line x 4 weeks": {
      "economic_floor": { "bin_edges": [/* n+1 floats */], "counts": [/* n ints */] },
      "margin_at_target": { "bin_edges": [], "counts": [] }
    }
  },
  "explanations": {
    "Economy: 1 line x 4 weeks": "This scenario reserves 1 of 4 lines, so the parallelism multiplier is 1.00. At 88% utilization the scarcity multiplier is 1.25. ..."
  }
}
```
Notes: the backend computes histograms server-side (default 40 bins) so the
frontend never receives 20k raw points. Validation errors return HTTP 422 with
`{ "detail": "message that tells the user what to fix" }`.

### `POST /api/schedule`
Request:
```json
{
  "foundry": { "...": "FoundryConfig fields" },
  "backlog": [ { "job_id": "B001", "customer": "...", "required_line_weeks": 2.0,
                 "margin_value": 2100000, "due_week": 3, "late_penalty_per_week": 150000,
                 "priority": 3 } ],
  "scenario": { "...": "optional JobScenario; if present, estimate its opportunity cost" }
}
```
Response:
```json
{
  "schedule": [ { "job_id": "...", "completion_week": 2, "lateness_weeks": 0,
                  "late_penalty": 0, "net_value": 2100000, "...": "input columns too" } ],
  "opportunity_cost": {
    "opportunity_cost_from_schedule": 0.0,
    "total_net_value_without": 0.0,
    "total_net_value_with": 0.0,
    "delayed_jobs": [ { "job_id": "...", "weeks_delayed": 1 } ]
  }
}
```
`opportunity_cost` is `null` when no `scenario` is supplied.

## Global constraints (every task)

- Keep it readable. Small typed functions, clear names, no clever abstractions.
- Type hints on public functions. `pathlib.Path`, not string paths. No secrets,
  no network calls in the core paths.
- The receiving company should clone, read the README, and run `docker compose up
  --build`. Everything must serve that goal.
- Documentation and UI copy: plain, clear, human. No emojis. No em dashes. Write
  the way a sharp college senior writes: direct and unpretentious, not academic
  and not markety.
