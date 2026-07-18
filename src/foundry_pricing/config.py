"""Load and validate configuration, scenarios, and backlog from disk.

These loaders are the boundary between untrusted files and the typed core. They
fail fast with messages that tell the user exactly which file and field is
wrong, so a misconfigured YAML never reaches the simulation engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .models import FoundryConfig, JobScenario, SimulationSettings

# Columns every backlog CSV must provide.
REQUIRED_BACKLOG_COLUMNS = (
    "job_id",
    "customer",
    "required_line_weeks",
    "margin_value",
    "due_week",
    "late_penalty_per_week",
    "priority",
)


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file into a dict, with a clear error if it is missing."""
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. Check the path or run from the repo root."
        )
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping at the top of {path}, got {type(data).__name__}.")
    return data


def load_config(path: Path) -> tuple[FoundryConfig, SimulationSettings]:
    """Load factory config and simulation settings from a YAML file.

    Args:
        path: Path to a config file with ``foundry:`` and ``simulation:`` keys.

    Returns:
        A ``(FoundryConfig, SimulationSettings)`` tuple.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required top-level sections are missing.
    """
    path = Path(path)
    data = _read_yaml(path)
    if "foundry" not in data:
        raise ValueError(f"Missing 'foundry:' section in {path}.")
    if "simulation" not in data:
        raise ValueError(f"Missing 'simulation:' section in {path}.")
    config = FoundryConfig.model_validate(data["foundry"])
    settings = SimulationSettings.model_validate(data["simulation"])
    return config, settings


def load_scenarios(path: Path, foundry_config: FoundryConfig) -> list[JobScenario]:
    """Load and validate job scenarios against the active factory config.

    Each scenario is validated with ``n_lines`` context so a scenario cannot
    request more lines than the factory has.

    Args:
        path: Path to a YAML file with a ``scenarios:`` list.
        foundry_config: The factory the scenarios run against.

    Returns:
        A list of validated :class:`JobScenario`.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the ``scenarios:`` list is missing/empty or a scenario
            fails validation.
    """
    path = Path(path)
    data = _read_yaml(path)
    raw = data.get("scenarios")
    if not raw:
        raise ValueError(f"No scenarios found under 'scenarios:' in {path}.")
    context = {"n_lines": foundry_config.n_lines}
    return [JobScenario.model_validate(item, context=context) for item in raw]


def load_backlog(path: Path) -> pd.DataFrame:
    """Load a backlog CSV and check that all required columns are present.

    Args:
        path: Path to a backlog CSV.

    Returns:
        The backlog as a DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If any required column is missing.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Backlog file not found: {path}.")
    backlog = pd.read_csv(path)
    missing = [c for c in REQUIRED_BACKLOG_COLUMNS if c not in backlog.columns]
    if missing:
        raise ValueError(f"Backlog {path} is missing required columns: {', '.join(missing)}.")
    return backlog
