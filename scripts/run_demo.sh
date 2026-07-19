#!/usr/bin/env bash
# Run the simulation and report on the sample data, writing to outputs/demo.
set -euo pipefail

cd "$(dirname "$0")/.."

OUT_DIR="${1:-outputs/demo}"

echo "==> Simulating the sample scenarios"
uv run foundry-pricing simulate \
  --config configs/default.yml \
  --scenarios data/sample/scenarios.yml \
  --out "${OUT_DIR}"

echo "==> Generating the report and charts"
uv run foundry-pricing report \
  --results "${OUT_DIR}/results.parquet" \
  --out "${OUT_DIR}"

echo "Done. Artifacts are in ${OUT_DIR}/"
