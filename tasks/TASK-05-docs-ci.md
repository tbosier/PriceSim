# Task 05: README, docs, and CI

You are writing the documentation that lets a competent startup clone this repo,
understand it, and run it in a few minutes, plus the CI that keeps it honest. Read
`tasks/ORCHESTRATION.md` first. This task merges last, so you can describe the
finished system accurately.

## Scope (files you own)

```
README.md               # replace the placeholder
docs/architecture.md
docs/formulas.md
docs/examples.md
docs/decisions.md
.github/workflows/ci.yml
.pre-commit-config.yaml
```

Do not edit Python source, the frontend, `pyproject.toml`, or the Docker files.
Read the code and the other task files to describe what was actually built.

## Writing style (strict)

This is the most important constraint for this task. The README and docs must read
like a real engineer wrote them by hand.

- No emojis. Anywhere.
- No em dashes. Use a period, a comma, or restructure the sentence.
- Plain, clear English at the level of a sharp college senior. Direct and
  unpretentious. Not academic, not markety, not breathless.
- Short paragraphs. Concrete verbs. Say what the thing does and how to run it.
- No filler like "In today's fast-paced world" or "leverage synergies". No
  exclamation marks stacked for hype.

## `README.md`

Cover, in this order:
1. One paragraph on what this is and the business question it answers (how to
   price scarce foundry capacity, and why `1 line x 4 weeks` is not the same as
   `4 lines x 1 week`).
2. A short "dashboard screenshot goes here" placeholder block.
3. Quickstart with Docker (the primary path): `docker compose up --build`, then
   open `http://localhost:3000` for the dashboard and `http://localhost:8000/api/health`
   for the API.
4. Quickstart local without Docker: `uv venv --python 3.12`, install, `make demo`,
   `make run-api`, `make run-app`.
5. CLI examples (from Task 01).
6. Config explanation (the `configs/*.yml` fields).
7. Formula summary (link to `docs/formulas.md`).
8. Project structure.
9. How to add a new scenario (edit `data/sample/scenarios.yml`, no code changes).
10. How to interpret results.
11. Engineering notes.
12. Caveats.
13. Roadmap.

Confirm every command in the README actually works before you finish.

## `docs/`

- `architecture.md`: the data flow `YAML/CSV inputs -> Pydantic validation ->
  simulation engine -> pricing summaries -> API/CLI -> dashboard/reports`, plus a
  short responsibility note per module.
- `formulas.md`: every formula in plain English with math where it helps
  (scarcity, parallelism, retooling multipliers; reserved line hours; direct cost;
  opportunity cost; economic floor; risk floor; target and expedited quotes).
  Note the truncated-normal draw-then-clip approximation.
- `examples.md`: example outputs and how to change scenarios and configs.
- `decisions.md`: why Monte Carlo first, why a greedy scheduler in v1, why
  Pydantic, why uv, why a Next.js + FastAPI split instead of Streamlit, why no
  database in v1.

## CI (`.github/workflows/ci.yml`)

Run on `push` and `pull_request`. Steps: checkout, set up Python 3.12, install uv,
install deps, then run:

```
ruff check .
ruff format --check .
mypy src
pytest --cov=foundry_pricing --cov-report=term-missing
```

Optionally add a second job that builds the frontend (`npm ci && npm run build`)
if it is quick to wire up.

## `.pre-commit-config.yaml`

Hooks for `ruff` (lint + format) and `mypy` on `src/`.

## Definition of done

- Every command in the README works on a clean checkout.
- The docs match the code that shipped, not this task file.
- `ruff format --check` passes on any code snippets you add as files.
- Commit on your branch and open a draft PR. Do not merge.
