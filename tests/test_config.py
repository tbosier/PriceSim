"""Tests for YAML/CSV loading and validation."""

from pathlib import Path

import pytest

from foundry_pricing.config import load_backlog, load_config, load_scenarios

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yml"
SAMPLE_SCENARIOS = REPO_ROOT / "data" / "sample" / "scenarios.yml"
SAMPLE_BACKLOG = REPO_ROOT / "data" / "sample" / "backlog.csv"


def test_load_config_reads_foundry_and_simulation() -> None:
    config, settings = load_config(DEFAULT_CONFIG)
    assert config.n_lines == 4
    assert settings.n_sims == 20000
    assert settings.random_seed == 42


def test_load_config_missing_file_raises_helpful_error() -> None:
    with pytest.raises(FileNotFoundError):
        load_config(REPO_ROOT / "configs" / "does_not_exist.yml")


def test_load_scenarios_returns_three_scenarios() -> None:
    config, _ = load_config(DEFAULT_CONFIG)
    scenarios = load_scenarios(SAMPLE_SCENARIOS, config)
    assert len(scenarios) == 3
    assert scenarios[0].name.startswith("Economy")


def test_load_scenarios_rejects_job_exceeding_lines() -> None:
    # A 2-line factory cannot host the 4-line expedited scenario.
    small_config, _ = load_config(DEFAULT_CONFIG)
    small_config = small_config.model_copy(update={"n_lines": 2})
    with pytest.raises(ValueError):
        load_scenarios(SAMPLE_SCENARIOS, small_config)


def test_load_backlog_has_required_columns() -> None:
    backlog = load_backlog(SAMPLE_BACKLOG)
    assert len(backlog) == 5
    for col in ("job_id", "required_line_weeks", "due_week", "priority"):
        assert col in backlog.columns


def test_load_backlog_missing_column_raises() -> None:
    bad = REPO_ROOT / "tests" / "_tmp_bad_backlog.csv"
    bad.write_text("job_id,customer\nX,Acme\n")
    try:
        with pytest.raises(ValueError):
            load_backlog(bad)
    finally:
        bad.unlink()
