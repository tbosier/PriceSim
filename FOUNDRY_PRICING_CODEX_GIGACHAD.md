# Codex Build Spec: Giga-Chad Foundry Pricing Simulator

You are Codex acting as a senior/principal software engineer. Build a production-quality but readable Python codebase for a Monte Carlo + capacity scheduling pricing simulator for a semiconductor/foundry-style business.

The goal is to impress technically while still being easy for a brand-new engineer to clone, run, read, and modify.

Do **not** over-architect. Favor simple, typed, testable modules with clear names over clever abstractions.

---

## 1. Product Summary

Build a repo called:

```text
foundry-pricing-sim
```

The app answers this business question:

> If a customer wants to reserve scarce foundry/manufacturing line capacity, how should we price different scenarios like `1 line x 4 weeks`, `2 lines x 2 weeks`, or `4 lines x 1 week`, accounting for tooling time, retooling complexity, debug/ramp time, yield uncertainty, downtime, current utilization, backlog opportunity cost, risk buffers, margin targets, and expedite premiums?

The first working version should include:

1. A Monte Carlo quote simulator.
2. A lightweight factory/backlog scheduling simulator.
3. Opportunity-cost pricing.
4. CLI commands.
5. A Streamlit dashboard.
6. Sample YAML/CSV data.
7. Docker and Docker Compose.
8. Makefile commands.
9. Tests, linting, type checking, and CI.
10. A README that makes a new user productive in under 5 minutes.

---

## 2. Core Philosophy

Use “giga-chad” engineering principles, but keep them practical:

- **Readable first:** a smart new engineer should understand the repo without a tour guide.
- **Small modules:** one file, one purpose.
- **Typed boundaries:** Pydantic models for config/input validation; type hints everywhere.
- **Pure-ish business logic:** simulation/pricing/scheduling functions should be deterministic given inputs and random seed.
- **Reproducible:** every simulation run accepts a seed.
- **Config-driven:** users can edit YAML/CSV instead of editing source code.
- **Fast enough:** vectorized NumPy/Pandas for Monte Carlo.
- **Testable:** unit tests for formulas, validation, pricing, and scheduling behavior.
- **No surprise magic:** avoid elaborate frameworks, dependency injection containers, metaclasses, or unnecessary inheritance.
- **Explainable outputs:** output tables should show not just price, but *why* price changed.
- **Safe defaults:** invalid configs fail fast with helpful messages.

---

## 3. Business Model

The pricing model should estimate:

```text
Quote Price =
  NRE / tooling cost
+ engineering labor
+ reserved capacity cost
+ production variable cost
+ expected opportunity cost
+ risk buffer
+ expedite / parallelism premium
+ target margin
```

Important business distinction:

```text
1 line x 4 weeks != 4 lines x 1 week
```

Both consume four production line-weeks, but `4 lines x 1 week` blocks the entire factory at once and should usually carry a capacity concentration / expedite premium.

---

## 4. Repo Structure

Create this structure:

```text
foundry-pricing-sim/
  README.md
  pyproject.toml
  uv.lock                         # generate if using uv
  Makefile
  Dockerfile
  docker-compose.yml
  .dockerignore
  .gitignore
  .env.example
  .pre-commit-config.yaml
  .github/
    workflows/
      ci.yml
  scripts/
    bootstrap.sh
    run_demo.sh
    export_report.sh
  configs/
    default.yml
    high_utilization.yml
    low_utilization.yml
  data/
    sample/
      scenarios.yml
      backlog.csv
      lines.csv
  docs/
    architecture.md
    formulas.md
    examples.md
    decisions.md
  src/
    foundry_pricing/
      __init__.py
      __main__.py
      cli.py
      models.py
      config.py
      distributions.py
      simulation.py
      scheduling.py
      pricing.py
      reporting.py
      plotting.py
      app.py
      logging_config.py
      constants.py
  tests/
    test_models.py
    test_distributions.py
    test_simulation.py
    test_scheduling.py
    test_pricing.py
    test_cli.py
```

Use the `src/` layout.

---

## 5. Dependencies

Use Python 3.12.

Prefer `uv` for package management because it is fast and modern. If `uv` is not installed, the README should include a fallback using `pip`.

Runtime dependencies:

```text
numpy
pandas
pydantic>=2
pydantic-settings
PyYAML
typer
rich
streamlit
plotly
matplotlib
scipy
```

Dev dependencies:

```text
pytest
pytest-cov
ruff
mypy
pre-commit
pandas-stubs
types-PyYAML
```

Optional: do **not** add OR-Tools in v1 unless you keep it optional. A simple deterministic greedy scheduler is enough for the MVP. The architecture should make it easy to later add OR-Tools.

---

## 6. Public Interfaces

### 6.1 CLI

Implement with Typer.

Commands:

```bash
foundry-pricing --help
foundry-pricing demo
foundry-pricing simulate --config configs/default.yml --scenarios data/sample/scenarios.yml --out outputs/demo
foundry-pricing schedule --config configs/default.yml --backlog data/sample/backlog.csv --out outputs/schedule
foundry-pricing report --results outputs/demo/results.parquet --out outputs/demo/report.md
```

Also support module execution:

```bash
python -m foundry_pricing demo
```

### 6.2 Streamlit App

Command:

```bash
streamlit run src/foundry_pricing/app.py
```

Dashboard should show:

- Scenario selector.
- Utilization slider.
- Number of lines slider.
- Monte Carlo run count input.
- Seed input.
- Scenario comparison table.
- Price distribution chart.
- Economic floor distribution chart.
- Margin-at-quote distribution chart.
- Capacity explanation panel.

Dashboard should be useful with sample data immediately.

---

## 7. Data Models

Use Pydantic v2 models in `models.py`.

Create at least these models:

```python
class FoundryConfig(BaseModel):
    n_lines: int
    hours_per_line_week: float
    base_line_hour_cost: float
    base_line_hour_value: float
    engineering_hour_cost: float
    current_utilization: float
    target_margin: float
    risk_percentile: float
    downtime_probability: float
    downtime_hours_mean: float
    downtime_hours_sd: float

class JobScenario(BaseModel):
    name: str
    lines_requested: int
    production_weeks: float
    tooling_weeks_mean: float
    tooling_weeks_sd: float
    debug_weeks_mean: float
    debug_weeks_sd: float
    engineering_hours_mean: float
    engineering_hours_sd: float
    tooling_parts_cost_mean: float
    tooling_parts_cost_sd: float
    expected_units: int
    revenue_per_unit: float
    variable_cost_per_unit: float
    yield_alpha: float
    yield_beta: float
    expedite_willingness_to_pay: float
    retooling_complexity: Literal["low", "medium", "high", "extreme"]

class SimulationSettings(BaseModel):
    n_sims: int
    random_seed: int

class SimulationResult(BaseModel):
    scenario: str
    # this may be row-level or summary-level; use a DataFrame internally if easier
```

Validation requirements:

- `n_lines > 0`
- `lines_requested <= n_lines`
- utilization between 0 and 1
- target margin between 0 and 0.95
- risk percentile between 0.5 and 0.99
- standard deviations must be non-negative
- prices/costs must be non-negative
- beta distribution params must be positive

---

## 8. Config Files

### 8.1 `configs/default.yml`

Create realistic but fake demo values:

```yaml
foundry:
  n_lines: 4
  hours_per_line_week: 168
  base_line_hour_cost: 900
  base_line_hour_value: 1600
  engineering_hour_cost: 175
  current_utilization: 0.88
  target_margin: 0.35
  risk_percentile: 0.80
  downtime_probability: 0.12
  downtime_hours_mean: 16
  downtime_hours_sd: 8

simulation:
  n_sims: 20000
  random_seed: 42
```

### 8.2 `data/sample/scenarios.yml`

Include these three scenarios:

```yaml
scenarios:
  - name: "Economy: 1 line x 4 weeks"
    lines_requested: 1
    production_weeks: 4
    tooling_weeks_mean: 1.5
    tooling_weeks_sd: 0.5
    debug_weeks_mean: 0.75
    debug_weeks_sd: 0.35
    engineering_hours_mean: 300
    engineering_hours_sd: 100
    tooling_parts_cost_mean: 250000
    tooling_parts_cost_sd: 75000
    expected_units: 250000
    revenue_per_unit: 8.0
    variable_cost_per_unit: 2.75
    yield_alpha: 35
    yield_beta: 8
    expedite_willingness_to_pay: 0.00
    retooling_complexity: "medium"

  - name: "Standard: 2 lines x 2 weeks"
    lines_requested: 2
    production_weeks: 2
    tooling_weeks_mean: 1.5
    tooling_weeks_sd: 0.5
    debug_weeks_mean: 0.75
    debug_weeks_sd: 0.35
    engineering_hours_mean: 300
    engineering_hours_sd: 100
    tooling_parts_cost_mean: 250000
    tooling_parts_cost_sd: 75000
    expected_units: 250000
    revenue_per_unit: 8.0
    variable_cost_per_unit: 2.75
    yield_alpha: 35
    yield_beta: 8
    expedite_willingness_to_pay: 0.05
    retooling_complexity: "medium"

  - name: "Expedited: 4 lines x 1 week"
    lines_requested: 4
    production_weeks: 1
    tooling_weeks_mean: 1.5
    tooling_weeks_sd: 0.5
    debug_weeks_mean: 0.75
    debug_weeks_sd: 0.35
    engineering_hours_mean: 300
    engineering_hours_sd: 100
    tooling_parts_cost_mean: 250000
    tooling_parts_cost_sd: 75000
    expected_units: 250000
    revenue_per_unit: 8.0
    variable_cost_per_unit: 2.75
    yield_alpha: 35
    yield_beta: 8
    expedite_willingness_to_pay: 0.10
    retooling_complexity: "medium"
```

### 8.3 `data/sample/backlog.csv`

Create fake backlog jobs with columns:

```csv
job_id,customer,required_line_weeks,margin_value,due_week,late_penalty_per_week,priority
B001,NeuroChip Labs,2.0,2100000,3,150000,3
B002,Medical Nano Systems,1.5,900000,4,75000,2
B003,Defense BioCompute,3.0,4500000,6,250000,5
B004,University Lab Pilot,0.5,180000,2,25000,1
B005,Strategic Whale Customer,4.0,8000000,8,400000,5
```

### 8.4 `data/sample/lines.csv`

Create fake line capability data:

```csv
line_id,name,capability,max_parallel_jobs
L1,Alpha Line,general,1
L2,Beta Line,general,1
L3,Gamma Line,advanced,1
L4,Delta Line,advanced,1
```

---

## 9. Formula Requirements

Implement in `pricing.py`.

### 9.1 Scarcity multiplier

```python
def scarcity_multiplier(utilization: float) -> float:
    if utilization < 0.60:
        return 0.85
    if utilization < 0.80:
        return 1.00
    if utilization < 0.90:
        return 1.25
    if utilization < 0.97:
        return 1.60
    return 2.25
```

### 9.2 Parallelism multiplier

```python
def parallelism_multiplier(lines_requested: int, total_lines: int) -> float:
    share = lines_requested / total_lines
    if share <= 0.25:
        return 1.00
    if share <= 0.50:
        return 1.15
    if share <= 0.75:
        return 1.35
    return 1.75
```

### 9.3 Retooling multiplier

```python
def retooling_multiplier(complexity: str) -> float:
    mapping = {
        "low": 0.85,
        "medium": 1.00,
        "high": 1.35,
        "extreme": 1.80,
    }
    return mapping[complexity]
```

### 9.4 Quote calculation

For each Monte Carlo draw:

```text
tooling_weeks ~ truncated normal(mean, sd, min=0.1)
debug_weeks ~ truncated normal(mean, sd, min=0.0)
engineering_hours ~ truncated normal(mean, sd, min=0.0)
tooling_parts_cost ~ truncated normal(mean, sd, min=0.0)
yield ~ beta(alpha, beta)
downtime_hours ~ Bernoulli(p) * truncated normal(mean, sd, min=0)
```

Then:

```text
good_units = expected_units * yield
reserved_line_hours = lines_requested * (tooling_weeks + debug_weeks + production_weeks) * hours_per_line_week + downtime_hours
production_line_hours = lines_requested * production_weeks * hours_per_line_week

direct_capacity_cost = reserved_line_hours * base_line_hour_cost
engineering_cost = engineering_hours * engineering_hour_cost
variable_production_cost = good_units * variable_cost_per_unit
adjusted_tooling_parts_cost = tooling_parts_cost * retooling_multiplier

direct_cost = direct_capacity_cost + engineering_cost + variable_production_cost + adjusted_tooling_parts_cost

opportunity_cost = reserved_line_hours * base_line_hour_value * scarcity_multiplier * parallelism_multiplier * current_utilization

economic_floor = direct_cost + opportunity_cost
risk_floor = quantile(economic_floor, risk_percentile)
target_quote = risk_floor / (1 - target_margin)
expedited_quote = target_quote * (1 + expedite_willingness_to_pay * parallelism_multiplier)
realized_margin = (target_quote - direct_cost) / target_quote
```

The summary table should include:

```text
scenario
avg_tooling_weeks
p80_tooling_weeks
avg_debug_weeks
avg_reserved_line_hours
avg_direct_cost
avg_opportunity_cost
p50_economic_floor
p80_economic_floor
p90_economic_floor
suggested_target_quote
suggested_expedited_quote
avg_margin_at_target
p10_margin_at_target
scarcity_multiplier
parallelism_multiplier
retooling_multiplier
```

---

## 10. Scheduling Simulator

Build a lightweight scheduler in `scheduling.py`.

Do not overcomplicate it. The first implementation can be greedy and deterministic.

Purpose:

- Estimate opportunity cost from inserting a proposed job into a backlog.
- Show which backlog jobs get delayed.
- Compute late penalties.
- Compare factory plan with and without proposed job.

Inputs:

```text
n_lines
planning_horizon_weeks
backlog jobs
optional proposed job
```

Scheduling rule v1:

1. Sort jobs by:
   - priority descending
   - due_week ascending
   - margin_value descending
2. Assign each job to earliest available line-week slots.
3. Track completion week.
4. Compute lateness:

```text
lateness_weeks = max(0, completion_week - due_week)
late_penalty = lateness_weeks * late_penalty_per_week
net_value = margin_value - late_penalty
```

For the proposed job, model it as capacity consumption equal to:

```text
required_line_weeks = lines_requested * (tooling_weeks_mean + debug_weeks_mean + production_weeks)
```

Then compute:

```text
opportunity_cost_from_schedule = total_net_value_without_proposed_job - total_net_value_with_proposed_job
```

Return:

```text
schedule table
summary metrics
delayed jobs
opportunity cost estimate
```

The Monte Carlo pricing model can use formula-based opportunity cost in v1, while the CLI/dashboard should also expose backlog-based opportunity cost as an extra diagnostic.

---

## 11. Reporting

Implement in `reporting.py`.

The report command should generate:

```text
outputs/demo/results.parquet
outputs/demo/summary.csv
outputs/demo/report.md
outputs/demo/price_distribution.png
outputs/demo/economic_floor_distribution.png
```

The Markdown report should include:

1. Title.
2. Run metadata: timestamp, seed, config path, scenario path.
3. Scenario comparison table.
4. Plain-English interpretation:
   - Which scenario is cheapest.
   - Which has highest capacity concentration premium.
   - Why all-lines-at-once is not equivalent to one-line-over-time.
5. Recommended quote ladder:
   - Economy
   - Standard
   - Expedited
6. Caveats.
7. Next steps.

Use `matplotlib` for static PNG report charts. Do not require a display server.

---

## 12. Streamlit Dashboard UX

Implement `src/foundry_pricing/app.py`.

Requirements:

- Page title: `Foundry Pricing Simulator`
- Sidebar controls:
  - config file path
  - scenario file path
  - number of simulations
  - random seed
  - utilization override slider
  - target margin slider
- Main page:
  - Explain problem in 3 sentences.
  - Show scenario comparison table.
  - Show `target_quote` and `expedited_quote` in big metric cards.
  - Show Plotly histograms for economic floor and margin distribution.
  - Show an explanation panel for the selected scenario:

```text
This scenario reserves X lines out of Y total lines, so the parallelism multiplier is Z. At current utilization U, the scarcity multiplier is S. This is why this quote is priced above/below the other scenarios.
```

- Include an expandable “Formula details” section.
- Include an expandable “Raw simulation results sample” section.

---

## 13. Docker Requirements

### 13.1 Dockerfile

Multi-stage is nice but do not make it too complex.

Requirements:

- Python 3.12 slim base.
- Install uv.
- Copy `pyproject.toml` and lockfile first for layer caching.
- Install dependencies.
- Copy source.
- Default command runs Streamlit.

### 13.2 docker-compose.yml

Include service:

```yaml
services:
  app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./configs:/app/configs
      - ./data:/app/data
      - ./outputs:/app/outputs
    command: streamlit run src/foundry_pricing/app.py --server.address=0.0.0.0 --server.port=8501
```

---

## 14. Makefile Commands

Implement:

```makefile
.PHONY: help setup demo run-app simulate report test lint format typecheck check docker-build docker-up clean

help:
	@echo "Available commands:"
	@echo "  make setup        Install dependencies"
	@echo "  make demo         Run end-to-end demo"
	@echo "  make run-app      Start Streamlit app"
	@echo "  make simulate     Run simulation CLI"
	@echo "  make report       Generate markdown report"
	@echo "  make test         Run tests"
	@echo "  make lint         Run ruff lint"
	@echo "  make format       Format code"
	@echo "  make typecheck    Run mypy"
	@echo "  make check        Run lint + typecheck + tests"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-up    Run app with Docker Compose"
	@echo "  make clean        Remove caches and outputs"
```

Use `uv run` in the commands if uv is available.

---

## 15. Shell Scripts

### 15.1 `scripts/bootstrap.sh`

- Check Python version.
- Check/install uv guidance.
- Run dependency install.
- Run pre-commit install.
- Print next commands.

### 15.2 `scripts/run_demo.sh`

Run the full demo:

```bash
foundry-pricing simulate --config configs/default.yml --scenarios data/sample/scenarios.yml --out outputs/demo
foundry-pricing report --results outputs/demo/results.parquet --out outputs/demo
```

### 15.3 `scripts/export_report.sh`

Generate a fresh report and print the output path.

All scripts should use:

```bash
set -euo pipefail
```

---

## 16. Testing Requirements

Use pytest.

At minimum test:

### 16.1 `test_pricing.py`

- scarcity multiplier thresholds.
- parallelism multiplier thresholds.
- retooling multiplier values.
- target quote is greater than economic floor when margin > 0.
- expedited quote is greater than or equal to target quote.

### 16.2 `test_models.py`

- invalid utilization fails.
- lines requested cannot exceed available lines.
- negative costs fail.
- bad retooling complexity fails.

### 16.3 `test_simulation.py`

- same seed returns identical summary.
- output row count equals `n_sims * n_scenarios`.
- no negative direct costs.
- good units are non-negative and less than or equal to expected units.

### 16.4 `test_scheduling.py`

- scheduler returns all jobs.
- high-priority jobs schedule before lower-priority jobs when constrained.
- inserting a large proposed job increases or maintains total penalty.
- opportunity cost is non-negative or clearly documented if it can be negative.

### 16.5 `test_cli.py`

Use Typer CliRunner:

- `--help` works.
- `demo` exits 0.

---

## 17. CI Requirements

Create `.github/workflows/ci.yml`.

Run on:

```yaml
on:
  push:
  pull_request:
```

Steps:

1. Checkout.
2. Set up Python 3.12.
3. Install uv.
4. Install dependencies.
5. Run:

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=foundry_pricing --cov-report=term-missing
```

---

## 18. README Requirements

The README should be excellent. Include:

1. One-paragraph explanation.
2. Screenshot placeholder or text block saying “dashboard screenshot goes here.”
3. Quickstart local:

```bash
git clone <repo-url>
cd foundry-pricing-sim
make setup
make demo
make run-app
```

4. Quickstart Docker:

```bash
docker compose up --build
```

5. CLI examples.
6. Config explanation.
7. Formula summary.
8. Project structure.
9. How to add a new scenario.
10. How to interpret results.
11. Engineering notes.
12. Caveats.
13. Roadmap.

Tone: clear, confident, helpful, not academic.

---

## 19. Documentation Requirements

### 19.1 `docs/architecture.md`

Explain:

```text
YAML/CSV inputs -> Pydantic validation -> simulation engine -> pricing summaries -> reports/dashboard
```

Include module responsibilities.

### 19.2 `docs/formulas.md`

Explain all formulas in plain English with math blocks where useful.

### 19.3 `docs/examples.md`

Show example outputs and how to change scenarios.

### 19.4 `docs/decisions.md`

Record design decisions:

- Why Monte Carlo first.
- Why greedy scheduler in v1.
- Why Pydantic.
- Why uv.
- Why Streamlit.
- Why not a database in v1.

---

## 20. Code Quality Standards

Use these standards:

- Type hints on all public functions.
- Google-style or NumPy-style docstrings for non-trivial functions.
- No giant functions. Split at roughly 50-80 lines unless there is a good reason.
- No global mutable state.
- Avoid class-heavy design unless state or validation makes it worthwhile.
- Prefer small pure functions.
- Use `pathlib.Path`, not raw string paths.
- Use `logging`, not random `print`, except CLI output through Rich.
- Error messages should tell users what to fix.
- All random draws must use `numpy.random.default_rng(seed)`.
- Avoid network calls.
- Do not add secrets.
- Do not hard-code absolute paths.

---

## 21. Implementation Details

### 21.1 `config.py`

Functions:

```python
def load_config(path: Path) -> tuple[FoundryConfig, SimulationSettings]: ...
def load_scenarios(path: Path, foundry_config: FoundryConfig) -> list[JobScenario]: ...
def load_backlog(path: Path) -> pd.DataFrame: ...
```

Validate input files exist. Fail with useful messages.

### 21.2 `distributions.py`

Functions:

```python
def truncated_normal(
    rng: np.random.Generator,
    mean: float,
    sd: float,
    size: int,
    lower: float = 0.0,
) -> np.ndarray: ...

def bernoulli_lognormal_or_normal_downtime(...): ...
```

Keep it simple. Truncated normal can be implemented by drawing normal and clipping to lower bound for v1. Mention approximation in docs.

### 21.3 `simulation.py`

Functions:

```python
def simulate_scenario(
    scenario: JobScenario,
    config: FoundryConfig,
    settings: SimulationSettings,
) -> pd.DataFrame: ...

def simulate_many(
    scenarios: list[JobScenario],
    config: FoundryConfig,
    settings: SimulationSettings,
) -> pd.DataFrame: ...

def summarize_results(results: pd.DataFrame, config: FoundryConfig, scenarios: list[JobScenario]) -> pd.DataFrame: ...
```

Results DataFrame columns:

```text
scenario
iteration
tooling_weeks
debug_weeks
engineering_hours
tooling_parts_cost
effective_yield
good_units
downtime_hours
reserved_line_hours
production_line_hours
direct_capacity_cost
engineering_cost
variable_production_cost
adjusted_tooling_parts_cost
direct_cost
opportunity_cost
economic_floor
target_quote
expedited_quote
realized_margin_at_target
realized_margin_at_expedited
scarcity_multiplier
parallelism_multiplier
retooling_multiplier
```

### 21.4 `pricing.py`

Pure formula functions. Keep easy to test.

### 21.5 `scheduling.py`

Functions:

```python
def schedule_backlog(backlog: pd.DataFrame, n_lines: int, planning_horizon_weeks: int) -> pd.DataFrame: ...
def proposed_job_to_backlog_row(scenario: JobScenario) -> dict[str, object]: ...
def estimate_schedule_opportunity_cost(backlog: pd.DataFrame, scenario: JobScenario, config: FoundryConfig) -> dict[str, object]: ...
```

Scheduler can discretize weeks into capacity buckets:

```text
week 1: n_lines available
week 2: n_lines available
...
```

If a job needs 2.5 line-weeks, consume available capacity greedily from earliest weeks.

### 21.6 `reporting.py`

Functions:

```python
def write_outputs(results: pd.DataFrame, summary: pd.DataFrame, out_dir: Path) -> None: ...
def generate_markdown_report(summary: pd.DataFrame, out_dir: Path, metadata: dict[str, str]) -> Path: ...
```

Use markdown tables.

### 21.7 `plotting.py`

Functions:

```python
def save_price_distribution(results: pd.DataFrame, out_dir: Path) -> Path: ...
def save_economic_floor_distribution(results: pd.DataFrame, out_dir: Path) -> Path: ...
```

Use matplotlib for report images. Use Plotly in Streamlit.

### 21.8 `cli.py`

Use Rich for tables and status output.

Commands should create output dirs automatically.

The `demo` command should run end-to-end using sample data.

---

## 22. Acceptance Criteria

The repo is complete when all of this works:

```bash
make setup
make check
make demo
make run-app
```

And Docker works:

```bash
docker compose up --build
```

And these files are generated by the demo:

```text
outputs/demo/results.parquet
outputs/demo/summary.csv
outputs/demo/report.md
outputs/demo/price_distribution.png
outputs/demo/economic_floor_distribution.png
```

The demo summary should show that:

- `Expedited: 4 lines x 1 week` has a higher parallelism multiplier than `Economy: 1 line x 4 weeks`.
- Higher utilization increases quote prices.
- Higher retooling complexity increases tooling-related costs.
- Suggested quote prices are greater than the economic floor after margin/risk adjustment.

---

## 23. Nice-to-Have Polish

Add these if time permits, but do not block the core build:

1. `outputs/demo/report.html` using Pandas Styler or a simple template.
2. Scenario sensitivity analysis:
   - utilization sweep from 50% to 98%.
   - margin target sweep.
3. `make sensitivity` command.
4. Export dashboard-selected scenario to Markdown.
5. Add `examples/notebooks/quick_analysis.ipynb` only if it does not complicate setup.
6. Add optional OR-Tools scheduler behind an extra dependency group.

---

## 24. Do Not Do These Things

Do not:

- Build a database.
- Build auth.
- Build a web backend unless absolutely necessary.
- Add Kubernetes.
- Add Celery/Redis.
- Add cloud deployment.
- Add secrets.
- Add complex plugin systems.
- Hide formulas in unreadable abstractions.
- Make users edit source code to run a new scenario.

This is a simulation/analytics product, not a SaaS platform.

---

## 25. Final Deliverable

Produce the full repository implementation.

After generating the codebase, run:

```bash
make check
make demo
```

Fix any failures.

Then provide a concise final summary with:

1. What was built.
2. How to run locally.
3. How to run with Docker.
4. Where to look first in the code.
5. Any known limitations.

