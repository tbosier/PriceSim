# Task 04: Docker, Compose, and Makefile

You are making the whole system start with one command. The target experience:
the receiving company clones the repo, reads the README, runs
`docker compose up --build`, and gets a working backend and frontend. Read
`tasks/ORCHESTRATION.md` first.

## Scope (files you own)

```
Dockerfile.backend
Dockerfile.frontend
docker-compose.yml
.dockerignore
Makefile
.env.example
```

Do not edit Python source, the frontend source, `pyproject.toml`, or `README.md`.
You may assume the Task 01, 02, and 03 code exists (CLI, `foundry_pricing.api.app`,
and `frontend/`). Coordinate only through files, not by editing others' code.

## Backend image (`Dockerfile.backend`)

- Base: `python:3.12-slim`.
- Install `uv`.
- Copy `pyproject.toml` first (and lockfile if present) for layer caching, install
  dependencies, then copy `src/`, `configs/`, and `data/`.
- Default command runs the API:
  `uvicorn foundry_pricing.api.app:app --host 0.0.0.0 --port 8000`.
- Working directory `/app`. No display server needed.

## Frontend image (`Dockerfile.frontend`)

- Base: `node:20-slim` (or `node:20-alpine`).
- Multi-stage: install deps and `npm run build`, then run `npm run start` (or a
  minimal runtime stage). Serve on port 3000.
- Pass `NEXT_PUBLIC_API_BASE_URL` as a build/runtime arg. In compose, the browser
  reaches the backend at `http://localhost:8000` (host port), so set it to that.

## `docker-compose.yml`

Two services that come up together:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    volumes:
      - ./configs:/app/configs
      - ./data:/app/data
      - ./outputs:/app/outputs
  frontend:
    build:
      context: ./frontend
      dockerfile: ../Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
    depends_on:
      - backend
```

Adjust paths/contexts to whatever actually builds cleanly. Add a healthcheck on
the backend hitting `/api/health` if it helps `depends_on`.

## `Makefile`

Implement these targets (use `uv run ...` when uv is available):

```
help setup demo run-app run-api simulate report test lint format typecheck check docker-build docker-up clean
```

- `check` runs lint + typecheck + tests.
- `run-api` starts uvicorn; `run-app` starts the frontend dev server.
- `docker-up` runs `docker compose up --build`.
- `clean` removes caches and `outputs/`.
- `help` prints a one-line description of each target.

## `.env.example`

Document the few env vars that exist (at least `NEXT_PUBLIC_API_BASE_URL` and any
optional `FOUNDRY_DATA_DIR`). No secrets.

## Definition of done

- `docker compose up --build` brings up both services. `curl localhost:8000/api/health`
  returns ok, and `http://localhost:3000` loads the dashboard and can run a
  simulation against the backend.
- `make check` and `make demo` work in a local (non-Docker) environment.
- Commit on your branch and open a draft PR. Do not merge.
