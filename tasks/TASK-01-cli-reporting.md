# Task 01: CLI, reporting, and plotting

You are implementing the command-line interface and the report/artifact
generation for `foundry-pricing-sim`. Read `tasks/ORCHESTRATION.md` first for the
stable core API you build on and the global rules.

## Scope (files you own)

Create only these files. Do not edit any existing core module, `pyproject.toml`,
`__init__.py`, or `README.md`.

```
src/foundry_pricing/cli.py
src/foundry_pricing/__main__.py
src/foundry_pricing/reporting.py
src/foundry_pricing/plotting.py
scripts/bootstrap.sh
scripts/run_demo.sh
scripts/export_report.sh
tests/test_cli.py            # CLI-specific tests only (Task 06 owns broader coverage)
```

## What to build

### `cli.py` (Typer + Rich)

A Typer app exposing these commands. Use Rich for tables and status output. Every
command creates its output directory automatically with `pathlib`.

```
foundry-pricing --help
foundry-pricing demo
foundry-pricing simulate --config configs/default.yml --scenarios data/sample/scenarios.yml --out outputs/demo
foundry-pricing schedule --config configs/default.yml --backlog data/sample/backlog.csv --out outputs/schedule
foundry-pricing report --results outputs/demo/results.parquet --out outputs/demo
```

- `demo` runs the whole pipeline end to end on the sample data: simulate, write
  artifacts, generate the report. It must exit 0 with no arguments.
- `simulate` loads config + scenarios, runs `simulate_many` + `summarize_results`,
  writes artifacts via `reporting.write_outputs`, and prints the summary as a Rich
  table.
- `schedule` loads config + backlog, runs `schedule_backlog`, prints the schedule,
  and if scenarios are provided also prints `estimate_schedule_opportunity_cost`.
- `report` reads a results parquet and regenerates the markdown report + charts.

The console script entry point `foundry-pricing = "foundry_pricing.cli:app"` is
already declared in `pyproject.toml`. Your Typer app object must be named `app`.

### `__main__.py`

Enables `python -m foundry_pricing ...`. Just delegate to `cli.app()`.

### `reporting.py`

```python
def write_outputs(results: pd.DataFrame, summary: pd.DataFrame, out_dir: Path) -> None: ...
def generate_markdown_report(summary: pd.DataFrame, out_dir: Path, metadata: dict[str, str]) -> Path: ...
```

`write_outputs` writes `results.parquet` and `summary.csv`. The demo must produce:

```
outputs/demo/results.parquet
outputs/demo/summary.csv
outputs/demo/report.md
outputs/demo/price_distribution.png
outputs/demo/economic_floor_distribution.png
```

The markdown report includes: title; run metadata (timestamp, seed, config path,
scenario path); the scenario comparison table; a plain-English interpretation
(cheapest scenario, highest capacity-concentration premium, why all-lines-at-once
is not the same as one-line-over-time); a recommended quote ladder (Economy /
Standard / Expedited); caveats; next steps. Use markdown tables.

### `plotting.py`

```python
def save_price_distribution(results: pd.DataFrame, out_dir: Path) -> Path: ...
def save_economic_floor_distribution(results: pd.DataFrame, out_dir: Path) -> Path: ...
```

Use matplotlib with the Agg backend (`matplotlib.use("Agg")`) so no display
server is needed. Overlay one distribution per scenario with a legend.

### `scripts/`

All scripts start with `set -euo pipefail`.
- `bootstrap.sh`: check Python version, give uv install guidance, install deps,
  install pre-commit, print next commands.
- `run_demo.sh`: run `simulate` then `report` on the sample data.
- `export_report.sh`: generate a fresh report and print the output path.

## Tests (`tests/test_cli.py`)

Use Typer's `CliRunner`:
- `--help` exits 0.
- `demo` exits 0 and creates the five expected output files in a temp dir.

## Definition of done

- `uv run pytest tests/test_cli.py` passes.
- `uv run foundry-pricing demo` exits 0 and generates all five artifacts.
- `ruff check .`, `ruff format --check .`, and `mypy src` are clean.
- Commit on your branch and open a draft PR. Do not merge.
