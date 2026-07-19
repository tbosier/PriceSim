#!/usr/bin/env bash
# Set up a local development environment for foundry-pricing-sim.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Checking for uv"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install it first:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "or see https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

echo "==> Creating the virtual environment (Python 3.12)"
uv venv --python 3.12

echo "==> Installing the package with dev extras"
uv pip install -e ".[dev]"

if [ -f .pre-commit-config.yaml ]; then
  echo "==> Installing pre-commit hooks"
  uv run pre-commit install
else
  echo "==> Skipping pre-commit hooks (no .pre-commit-config.yaml yet)"
fi

echo
echo "Done. Next commands:"
echo "  uv run foundry-pricing demo        # end-to-end demo into outputs/demo"
echo "  uv run pytest                      # run the test suite"
echo "  uv run ruff check .                # lint"
echo "  uv run mypy src                    # type-check"
