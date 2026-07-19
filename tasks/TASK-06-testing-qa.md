# Task 06: Test suite and QA hardening

You are turning a solid baseline test suite into something that would impress a
sharp engineering team at the receiving company. The core already has 67 passing
tests. Your job is depth: known-output "golden" tests, property-based tests, and
end-to-end integration tests across the CLI and the API. Read
`tasks/ORCHESTRATION.md` first.

## Scope (files you own)

Add new test files only. Do not edit the six existing test files
(`test_models.py`, `test_pricing.py`, `test_distributions.py`,
`test_simulation.py`, `test_scheduling.py`, `test_config.py`) and do not edit any
source module or `pyproject.toml`. `hypothesis`, `httpx`, and `pytest-cov` are
already in the dev dependencies.

```
tests/test_golden_values.py         # hand-verified known outputs
tests/test_properties.py            # hypothesis property-based tests
tests/integration/__init__.py
tests/integration/test_pipeline.py  # CLI demo end to end
tests/integration/test_api_flow.py  # API request/response flow (needs Task 02)
tests/conftest.py                   # shared fixtures (only if not already present)
```

If Task 01 or Task 02 has not merged yet when you start, write those integration
tests anyway and mark them with `pytest.importorskip` or a skip marker so the
suite stays green until the dependency lands. Call out clearly in your PR which
tests are gated.

## What "good tests" means here

### Golden-value tests (`test_golden_values.py`)

Pin down exact, hand-checked numbers so a future refactor cannot silently change
the math. Because the multipliers are deterministic and the RNG is seeded, most
of this is exactly reproducible.

- Deterministic pieces: assert the exact pricing multipliers for the three sample
  scenarios (`parallelism_multiplier` for 1x4, 2x2, 4x1 is 1.00, 1.15, 1.75; the
  scarcity multiplier at 0.88 utilization is 1.25). Assert
  `proposed_job_to_backlog_row` gives 13.0 line-weeks for the 4-line scenario.
- Hand-computed scheduler cases: build small backlogs where you can compute
  completion weeks, lateness, penalties, and net value by hand, and assert the
  exact values (extend beyond the single-job cases already covered).
- Seeded Monte Carlo snapshot: run `simulate_many` on the sample data with
  `random_seed=42, n_sims` fixed, and assert the summary quotes match the values
  you observe, to a tight tolerance (for example `pytest.approx(rel=1e-6)` on the
  reproduced run, and a looser sanity band documented in a comment). Verify the
  ordering invariant holds: expedited target quote > standard > economy.

### Property-based tests (`test_properties.py`)

Use `hypothesis` to assert invariants across wide input ranges:
- `scarcity_multiplier` is monotone non-decreasing in utilization.
- `parallelism_multiplier` is monotone non-decreasing in the requested share.
- `target_quote(floor, margin) >= floor` for all valid margins, and equals floor
  at margin 0.
- For any valid config and scenario, simulated `good_units` is always in
  `[0, expected_units]`, `direct_cost >= 0`, and `effective_yield` is in `[0, 1]`.
- Same seed produces identical results; different seeds generally do not.
- Scheduler: total scheduled line-weeks equals the sum of requested line-weeks
  (capacity is conserved), and adding a job never reduces total late penalty.

Keep hypothesis strategies bounded to realistic ranges so tests stay fast and do
not trip the model validators.

### Integration tests

- `test_pipeline.py`: run the CLI `demo` in a temp directory (Typer `CliRunner`),
  assert exit code 0 and that all five artifacts exist and are non-empty, and that
  `summary.csv` has one row per scenario with the expected columns.
- `test_api_flow.py`: use `TestClient` to walk the real flow: fetch defaults,
  post them to `/api/simulate`, and assert the response shape matches the REST
  contract (summary length, histogram `bin_edges`/`counts` lengths, one
  explanation per scenario). Post the sample backlog to `/api/schedule` and assert
  a schedule row per job and a non-negative opportunity cost.

## Coverage

- Target 90%+ line coverage across `foundry_pricing` once Tasks 01 and 02 have
  merged. Run `pytest --cov=foundry_pricing --cov-report=term-missing` and close
  the obvious gaps. Do not chase coverage with vacuous tests; every test should
  assert real behavior.

## Definition of done

- `uv run pytest --cov=foundry_pricing` passes, with gated integration tests
  skipped only when their dependency is genuinely absent.
- `ruff check .`, `ruff format --check .`, and `mypy src` stay clean (type-annotate
  test helpers where mypy strict requires it, or keep tests out of the mypy path
  as the project already configures).
- Commit on your branch and open a draft PR. Do not merge. In the PR description,
  report the final coverage number and list any gated tests.
