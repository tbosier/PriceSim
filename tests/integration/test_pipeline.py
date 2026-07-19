"""End-to-end CLI pipeline test (Task 01).

Runs the ``demo`` command via Typer's CliRunner in a temporary working directory
and asserts the whole pipeline produces the five documented artifacts. Gated on
the CLI module, which lands with Task 01.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

# Gate: skip cleanly until Task 01 (the CLI) merges.
cli = pytest.importorskip("foundry_pricing.cli")

from typer.testing import CliRunner  # noqa: E402

# The five artifacts the demo must produce (per TASK-01).
EXPECTED_ARTIFACTS = (
    "results.parquet",
    "summary.csv",
    "report.md",
    "price_distribution.png",
    "economic_floor_distribution.png",
)


def _find(root: Path, filename: str) -> Path | None:
    """Return the first match for ``filename`` anywhere under ``root``."""
    matches = list(root.rglob(filename))
    return matches[0] if matches else None


def test_demo_pipeline_produces_all_artifacts(
    tmp_path: Path,
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Run in an isolated working dir with its own copy of the sample inputs so
    # the demo can resolve them relative to the cwd and writes land here.
    shutil.copytree(repo_root / "configs", tmp_path / "configs")
    shutil.copytree(repo_root / "data", tmp_path / "data")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["demo"])

    assert result.exit_code == 0, result.output

    for filename in EXPECTED_ARTIFACTS:
        path = _find(tmp_path, filename)
        assert path is not None, f"missing artifact: {filename}\n{result.output}"
        assert path.stat().st_size > 0, f"empty artifact: {filename}"


def test_demo_summary_has_one_row_per_scenario(
    tmp_path: Path,
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(repo_root / "configs", tmp_path / "configs")
    shutil.copytree(repo_root / "data", tmp_path / "data")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["demo"])
    assert result.exit_code == 0, result.output

    summary_path = _find(tmp_path, "summary.csv")
    assert summary_path is not None
    summary = pd.read_csv(summary_path)

    # The sample data defines three scenarios.
    assert len(summary) == 3
    for column in (
        "scenario",
        "suggested_target_quote",
        "suggested_expedited_quote",
        "scarcity_multiplier",
        "parallelism_multiplier",
        "retooling_multiplier",
    ):
        assert column in summary.columns


def test_cli_help_exits_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "demo" in result.output
