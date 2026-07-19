"""CLI smoke tests using Typer's CliRunner.

Broader coverage lives in Task 06; here we only prove the app wires up and the
demo produces every artifact it promises.
"""

from pathlib import Path

from typer.testing import CliRunner

from foundry_pricing.cli import app

runner = CliRunner()

# The five artifacts the demo must always produce.
_EXPECTED_ARTIFACTS = (
    "results.parquet",
    "summary.csv",
    "report.md",
    "price_distribution.png",
    "economic_floor_distribution.png",
)


def test_help_exits_zero() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "simulate" in result.output
    assert "demo" in result.output


def test_demo_creates_all_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "demo"
    result = runner.invoke(app, ["demo", "--out", str(out_dir)])
    assert result.exit_code == 0, result.output
    for artifact in _EXPECTED_ARTIFACTS:
        path = out_dir / artifact
        assert path.exists(), f"missing artifact: {artifact}"
        assert path.stat().st_size > 0, f"empty artifact: {artifact}"


def test_simulate_writes_results(tmp_path: Path) -> None:
    out_dir = tmp_path / "sim"
    result = runner.invoke(app, ["simulate", "--out", str(out_dir)])
    assert result.exit_code == 0, result.output
    assert (out_dir / "results.parquet").exists()
    assert (out_dir / "summary.csv").exists()


def test_report_regenerates_from_results(tmp_path: Path) -> None:
    out_dir = tmp_path / "demo"
    sim = runner.invoke(app, ["simulate", "--out", str(out_dir)])
    assert sim.exit_code == 0, sim.output

    report = runner.invoke(
        app,
        ["report", "--results", str(out_dir / "results.parquet"), "--out", str(out_dir)],
    )
    assert report.exit_code == 0, report.output
    assert (out_dir / "report.md").exists()
    assert (out_dir / "price_distribution.png").exists()
    assert (out_dir / "economic_floor_distribution.png").exists()


def test_schedule_runs_with_scenarios(tmp_path: Path) -> None:
    out_dir = tmp_path / "schedule"
    result = runner.invoke(app, ["schedule", "--out", str(out_dir)])
    assert result.exit_code == 0, result.output
    assert (out_dir / "schedule.csv").exists()
