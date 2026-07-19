# Task 03: Next.js frontend

You are building the dashboard that replaces the Streamlit app from the original
spec. It consumes the FastAPI backend (Task 02). Read `tasks/ORCHESTRATION.md`
first, especially the REST contract, which is the source of truth for every API
call. Do not invent endpoints or fields.

## Scope (files you own)

Everything lives under `frontend/`. You own that directory entirely. Do not touch
any Python file, `pyproject.toml`, or `README.md`.

```
frontend/
  package.json
  next.config.js (or .ts)
  tsconfig.json
  .env.local.example        # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
  app/ or src/app/          # Next.js App Router
  components/
  lib/api.ts                # typed fetch wrappers for the REST contract
  ...
```

Use Next.js 14+ with the App Router, TypeScript, and Node 20. Keep dependencies
lean. You may use a lightweight charting library (Recharts or Plotly for React)
and a styling approach of your choice (Tailwind is a good default). No backend
framework, no database.

## What the dashboard shows

Page title: "Foundry Pricing Simulator". The page should explain the problem in
about three sentences, then let the user run the simulation and read the results.

Controls (prefill from `GET /api/config/default` and `GET /api/scenarios/sample`):
- number of simulations
- random seed
- utilization override
- target margin override
- number of lines
- scenario selection

Main content:
- A scenario comparison table (all summary columns that matter: suggested target
  quote, expedited quote, economic floor percentiles, margins, and the three
  multipliers).
- `suggested_target_quote` and `suggested_expedited_quote` shown as large,
  legible metric cards per scenario.
- Charts from the histogram data returned by `/api/simulate`: economic floor
  distribution and margin-at-target distribution. Render the server-provided
  `bin_edges` + `counts` as bar/area charts. Do not expect raw sample arrays.
- An explanation panel for the selected scenario. Use the `explanations` string
  from the API response, which already names the parallelism and scarcity
  multipliers and why the quote lands where it does.
- A collapsible "Formula details" section and a collapsible "How to read this"
  section.

## Design bar

This is the piece the receiving company sees first, so it should look genuinely
good, not like a default template. Aim for a clean, confident, modern analytics
UI: strong typographic hierarchy, generous spacing, a restrained color system,
responsive layout, and dark mode if it is cheap to add. The numbers are large and
the story (why 4x1 costs more than 1x4) is obvious at a glance. Avoid clutter and
avoid stock dashboard chrome.

Copy rules: plain, clear, human. No emojis. No em dashes. Write like a sharp
college senior, direct and unpretentious.

## Data flow

- `lib/api.ts` holds typed wrappers: `getDefaultConfig()`, `getSampleScenarios()`,
  `postSimulate(payload)`, `postSchedule(payload)`. Base URL from
  `process.env.NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000`.
- Handle loading and error states. If the API returns 422, show the `detail`
  message near the controls so the user knows what to fix.

## Definition of done

- `npm install && npm run build` succeeds with Node 20.
- `npm run dev` serves the dashboard on port 3000; with the backend running on
  8000 it loads defaults, runs a simulation, and renders the table, metric cards,
  charts, and explanation for the sample scenarios.
- `npm run lint` is clean.
- Commit on your branch and open a draft PR. Do not merge.
