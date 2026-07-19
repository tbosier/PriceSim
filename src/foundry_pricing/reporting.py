"""Write simulation artifacts and render the human-readable markdown report.

This module turns the tidy simulation output into the files a reader actually
opens: the raw ``results.parquet``, a flat ``summary.csv``, and a plain-English
``report.md`` that explains the quote ladder and the capacity-concentration
premium. Charts are handled next door in :mod:`foundry_pricing.plotting`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

# Columns shown in the scenario comparison table, in display order.
_COMPARISON_COLUMNS: tuple[str, ...] = (
    "scenario",
    "p80_economic_floor",
    "suggested_target_quote",
    "suggested_expedited_quote",
    "avg_margin_at_target",
    "p10_margin_at_target",
    "parallelism_multiplier",
    "scarcity_multiplier",
)

_COMPARISON_HEADERS: tuple[str, ...] = (
    "Scenario",
    "P80 floor",
    "Target quote",
    "Expedited quote",
    "Avg margin",
    "P10 margin",
    "Parallelism x",
    "Scarcity x",
)

# Ladder tier names, cheapest first.
_LADDER_TIERS: tuple[str, ...] = ("Economy", "Standard", "Expedited")


def _dollars(value: float) -> str:
    return f"${value:,.0f}"


def _multiplier(value: float) -> str:
    return f"{value:.2f}x"


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_outputs(results: pd.DataFrame, summary: pd.DataFrame, out_dir: Path) -> None:
    """Write the raw per-iteration results and the scenario summary to disk.

    Args:
        results: Per-iteration results from :func:`simulation.simulate_many`.
        summary: One-row-per-scenario summary from ``summarize_results``.
        out_dir: Directory to write into; created if it does not exist.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results.to_parquet(out_dir / "results.parquet", index=False)
    summary.to_csv(out_dir / "summary.csv", index=False)


def summarize_from_results(results: pd.DataFrame) -> pd.DataFrame:
    """Rebuild the scenario summary from a per-iteration results frame alone.

    ``simulation.summarize_results`` needs the original scenario objects for
    ordering. The ``report`` command only has a ``results.parquet`` on disk, so
    this reconstructs the same summary columns directly from the frame,
    preserving each scenario's first-appearance order.

    Args:
        results: Per-iteration results with the ``simulation.RESULT_COLUMNS``.

    Returns:
        A summary DataFrame, one row per scenario.
    """
    order = list(dict.fromkeys(results["scenario"].tolist()))
    rows: list[dict[str, object]] = []
    for name in order:
        g = results[results["scenario"] == name]
        rows.append(
            {
                "scenario": name,
                "avg_tooling_weeks": float(g["tooling_weeks"].mean()),
                "p80_tooling_weeks": float(g["tooling_weeks"].quantile(0.80)),
                "avg_debug_weeks": float(g["debug_weeks"].mean()),
                "avg_reserved_line_hours": float(g["reserved_line_hours"].mean()),
                "avg_direct_cost": float(g["direct_cost"].mean()),
                "avg_opportunity_cost": float(g["opportunity_cost"].mean()),
                "p50_economic_floor": float(g["economic_floor"].quantile(0.50)),
                "p80_economic_floor": float(g["economic_floor"].quantile(0.80)),
                "p90_economic_floor": float(g["economic_floor"].quantile(0.90)),
                "suggested_target_quote": float(g["target_quote"].iloc[0]),
                "suggested_expedited_quote": float(g["expedited_quote"].iloc[0]),
                "avg_margin_at_target": float(g["realized_margin_at_target"].mean()),
                "p10_margin_at_target": float(g["realized_margin_at_target"].quantile(0.10)),
                "scarcity_multiplier": float(g["scarcity_multiplier"].iloc[0]),
                "parallelism_multiplier": float(g["parallelism_multiplier"].iloc[0]),
                "retooling_multiplier": float(g["retooling_multiplier"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a simple GitHub-flavored markdown table."""
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(cells) + " |" for cells in rows)
    return "\n".join([head, sep, body])


def _metadata_table(metadata: dict[str, str]) -> str:
    rows = [[key, value] for key, value in metadata.items()]
    return _markdown_table(["Field", "Value"], rows)


def _comparison_table(summary: pd.DataFrame) -> str:
    formatters: dict[str, Callable[[float], str]] = {
        "p80_economic_floor": _dollars,
        "suggested_target_quote": _dollars,
        "suggested_expedited_quote": _dollars,
        "avg_margin_at_target": _percent,
        "p10_margin_at_target": _percent,
        "parallelism_multiplier": _multiplier,
        "scarcity_multiplier": _multiplier,
    }
    rows: list[list[str]] = []
    for _, row in summary.iterrows():
        cells: list[str] = []
        for col in _COMPARISON_COLUMNS:
            if col == "scenario":
                cells.append(str(row[col]))
            else:
                cells.append(formatters[col](float(row[col])))
        rows.append(cells)
    return _markdown_table(list(_COMPARISON_HEADERS), rows)


def _ladder(summary: pd.DataFrame) -> pd.DataFrame:
    """Order scenarios cheapest-to-most-expensive and label them as tiers."""
    ordered = summary.sort_values("suggested_target_quote").reset_index(drop=True)
    tiers = [
        _LADDER_TIERS[i] if i < len(_LADDER_TIERS) else f"Tier {i + 1}" for i in range(len(ordered))
    ]
    ordered = ordered.copy()
    ordered["tier"] = tiers
    return ordered


def _ladder_table(ladder: pd.DataFrame) -> str:
    rows: list[list[str]] = []
    for _, row in ladder.iterrows():
        rows.append(
            [
                str(row["tier"]),
                str(row["scenario"]),
                _dollars(float(row["suggested_target_quote"])),
                _dollars(float(row["suggested_expedited_quote"])),
                _percent(float(row["avg_margin_at_target"])),
            ]
        )
    return _markdown_table(
        ["Tier", "Scenario", "Target quote", "Expedited quote", "Avg margin"], rows
    )


def _interpretation(summary: pd.DataFrame) -> str:
    """Write the plain-English reading of the comparison table."""
    names = summary["scenario"].tolist()
    quotes = summary["suggested_target_quote"].tolist()
    parallelism = summary["parallelism_multiplier"].tolist()

    cheapest_i = min(range(len(quotes)), key=lambda i: quotes[i])
    dearest_i = max(range(len(quotes)), key=lambda i: quotes[i])
    concentrated_i = max(range(len(parallelism)), key=lambda i: parallelism[i])

    cheapest_name = str(names[cheapest_i])
    cheapest_quote = float(quotes[cheapest_i])
    dearest_name = str(names[dearest_i])
    dearest_quote = float(quotes[dearest_i])
    concentrated_name = str(names[concentrated_i])
    premium = float(parallelism[concentrated_i])
    quote_gap = dearest_quote - cheapest_quote

    lines = [
        f"- Cheapest option: **{cheapest_name}** at a target quote of "
        f"{_dollars(cheapest_quote)}. It spreads the same work over "
        "more weeks on fewer lines, so it ties up the least scarce capacity at any one moment.",
        f"- Most expensive option: **{dearest_name}** at "
        f"{_dollars(dearest_quote)}, "
        f"about {_dollars(quote_gap)} more than the cheapest.",
        f"- Highest capacity-concentration premium: **{concentrated_name}** carries a "
        f"parallelism multiplier of {_multiplier(premium)}. Reserving several lines at once "
        "monopolizes the factory, so the opportunity cost, and therefore the quote, climbs.",
        "- One line for four weeks is not the same as four lines for one week. Both consume the "
        "same number of line-weeks, but running the whole factory at once blocks every other job "
        "for that window. The parallelism multiplier prices that disruption, which is why the "
        "concentrated scenario quotes higher even though the raw line-weeks match.",
    ]
    return "\n".join(lines)


def generate_markdown_report(
    summary: pd.DataFrame, out_dir: Path, metadata: dict[str, str]
) -> Path:
    """Render the full markdown report and write it to ``report.md``.

    Args:
        summary: One-row-per-scenario summary.
        out_dir: Directory to write ``report.md`` into; created if missing.
        metadata: Run metadata (timestamp, seed, config path, scenario path).

    Returns:
        The path to the written ``report.md``.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ladder = _ladder(summary)
    sections = [
        "# Foundry pricing report",
        "",
        "A Monte Carlo read on what to charge for a job, and why the same work costs "
        "more when it is crammed onto the whole factory at once.",
        "",
        "## Run metadata",
        "",
        _metadata_table(metadata),
        "",
        "## Scenario comparison",
        "",
        _comparison_table(summary),
        "",
        "## What the numbers say",
        "",
        _interpretation(summary),
        "",
        "## Recommended quote ladder",
        "",
        "Present these as tiers. Economy is the patient customer who lets us schedule "
        "around them. Expedited is the customer who wants the whole factory now and pays "
        "for the disruption.",
        "",
        _ladder_table(ladder),
        "",
        "## Caveats",
        "",
        "- These figures come from a simulation of fictional demo inputs, not a booked deal.",
        "- Quotes are priced off a risk percentile of the cost floor, so they already carry a "
        "cushion against bad-luck cost outcomes. Do not stack another arbitrary margin on top.",
        "- The scheduler that estimates displacement cost is a simple greedy fill, not an "
        "optimal solver. Treat opportunity-cost figures as directional.",
        "- Multipliers are business judgment encoded as step functions. Retune them in "
        "`constants.py` as real quoting data arrives.",
        "",
        "## Next steps",
        "",
        "- Replace the sample config and scenarios with the real factory parameters and the "
        "live job being quoted.",
        "- Feed the current backlog into `foundry-pricing schedule` to see which committed jobs "
        "a rush order would push late.",
        "- Compare the suggested quote ladder against recent won and lost bids to calibrate the "
        "target margin and the multiplier tables.",
        "",
    ]
    report_path = out_dir / "report.md"
    report_path.write_text("\n".join(sections), encoding="utf-8")
    return report_path
