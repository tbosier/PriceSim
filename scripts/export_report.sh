#!/usr/bin/env bash
# Regenerate a fresh report and charts from an existing results.parquet, then
# print where the report landed.
set -euo pipefail

cd "$(dirname "$0")/.."

OUT_DIR="${1:-outputs/demo}"
RESULTS="${OUT_DIR}/results.parquet"

if [ ! -f "${RESULTS}" ]; then
  echo "No results found at ${RESULTS}."
  echo "Run 'uv run foundry-pricing simulate --out ${OUT_DIR}' first (or scripts/run_demo.sh)."
  exit 1
fi

uv run foundry-pricing report --results "${RESULTS}" --out "${OUT_DIR}"

echo "Report written to ${OUT_DIR}/report.md"
