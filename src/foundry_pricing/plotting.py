"""Distribution charts, one overlaid histogram per scenario.

We use the non-interactive Agg backend so these render on a headless server with
no display attached. Each chart overlays every scenario's distribution with a
legend so the reader can see, at a glance, how concentrating capacity shifts the
cost floor and the achievable margin.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# Bins for every histogram. Enough resolution to see the shape, few enough to
# stay readable when several scenarios overlap.
_BINS = 40


def _save_overlay(
    results: pd.DataFrame,
    column: str,
    out_path: Path,
    title: str,
    xlabel: str,
    as_percent: bool,
) -> Path:
    """Overlay one translucent histogram per scenario and save the figure."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for name in dict.fromkeys(results["scenario"].tolist()):
        values = results.loc[results["scenario"] == name, column]
        if as_percent:
            values = values * 100.0
        ax.hist(values, bins=_BINS, alpha=0.5, label=str(name), density=True)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Probability density")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def save_price_distribution(results: pd.DataFrame, out_dir: Path) -> Path:
    """Plot the realized margin at the suggested quote, per scenario.

    The suggested quote itself is a single number per scenario, so what varies
    across the 20k iterations is how good that price turns out to be. This chart
    shows the margin the target quote actually earns once the random cost draws
    land, which is the honest picture of price quality.

    Args:
        results: Per-iteration results with ``realized_margin_at_target``.
        out_dir: Directory to write the PNG into; created if missing.

    Returns:
        The path to ``price_distribution.png``.
    """
    out_dir = Path(out_dir)
    return _save_overlay(
        results,
        column="realized_margin_at_target",
        out_path=out_dir / "price_distribution.png",
        title="Price quality: realized margin at the suggested quote",
        xlabel="Realized margin (%)",
        as_percent=True,
    )


def save_economic_floor_distribution(results: pd.DataFrame, out_dir: Path) -> Path:
    """Plot the distribution of the economic floor, per scenario.

    The economic floor is the all-in cost of a job for a single random outcome:
    direct cost plus the opportunity cost of the capacity it reserves. The quote
    is priced off a risk percentile of this distribution, so its spread is what
    the pricing cushion is protecting against.

    Args:
        results: Per-iteration results with ``economic_floor``.
        out_dir: Directory to write the PNG into; created if missing.

    Returns:
        The path to ``economic_floor_distribution.png``.
    """
    out_dir = Path(out_dir)
    return _save_overlay(
        results,
        column="economic_floor",
        out_path=out_dir / "economic_floor_distribution.png",
        title="Economic floor by scenario",
        xlabel="Economic floor ($)",
        as_percent=False,
    )
