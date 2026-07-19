"""Shared fixtures for the foundry-pricing test suite.

These fixtures give every test a stable handle on the repo root, the sample
config, and the sample scenarios so tests do not each re-derive paths or rebuild
the same objects.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from foundry_pricing.config import load_backlog, load_config, load_scenarios
from foundry_pricing.models import FoundryConfig, JobScenario, SimulationSettings


def _find_repo_root() -> Path:
    """Walk up from this file until we find the directory holding pyproject.toml."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate repo root (no pyproject.toml found).")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return _find_repo_root()


@pytest.fixture(scope="session")
def default_config_path(repo_root: Path) -> Path:
    """Path to the default factory config YAML."""
    return repo_root / "configs" / "default.yml"


@pytest.fixture(scope="session")
def sample_scenarios_path(repo_root: Path) -> Path:
    """Path to the sample scenarios YAML."""
    return repo_root / "data" / "sample" / "scenarios.yml"


@pytest.fixture(scope="session")
def sample_backlog_path(repo_root: Path) -> Path:
    """Path to the sample backlog CSV."""
    return repo_root / "data" / "sample" / "backlog.csv"


@pytest.fixture
def config_and_settings(
    default_config_path: Path,
) -> tuple[FoundryConfig, SimulationSettings]:
    """The default factory config and Monte Carlo settings, loaded from disk."""
    return load_config(default_config_path)


@pytest.fixture
def config(config_and_settings: tuple[FoundryConfig, SimulationSettings]) -> FoundryConfig:
    """Just the default factory config."""
    return config_and_settings[0]


@pytest.fixture
def settings(
    config_and_settings: tuple[FoundryConfig, SimulationSettings],
) -> SimulationSettings:
    """Just the default Monte Carlo settings (seed 42, 20000 sims)."""
    return config_and_settings[1]


@pytest.fixture
def scenarios(sample_scenarios_path: Path, config: FoundryConfig) -> list[JobScenario]:
    """The three sample scenarios validated against the default factory."""
    return load_scenarios(sample_scenarios_path, config)


@pytest.fixture
def backlog(sample_backlog_path: Path) -> pd.DataFrame:
    """The sample backlog CSV as a DataFrame."""
    return load_backlog(sample_backlog_path)
