"""Command-line interface for the foundry pricing simulator.

A thin Typer app over the core engine. Each command loads typed inputs, runs the
simulation or scheduler, prints a Rich table, and writes artifacts. The heavy
lifting lives in the core modules; this file only wires them to a terminal and a
set of output files.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from .config import load_backlog, load_config, load_scenarios
from .plotting import save_economic_floor_distribution, save_price_distribution
from .reporting import generate_markdown_report, summarize_from_results, write_outputs
from .scheduling import estimate_schedule_opportunity_cost, schedule_backlog
from .simulation import simulate_many, summarize_results

# Sample inputs ship in the repo. Resolve them relative to the package so the
# demo runs from any working directory.
_PACKAGE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_ROOT.parents[1]
_DEFAULT_CONFIG = _REPO_ROOT / "configs" / "default.yml"
_SAMPLE_SCENARIOS = _REPO_ROOT / "data" / "sample" / "scenarios.yml"
_SAMPLE_BACKLOG = _REPO_ROOT / "data" / "sample" / "backlog.csv"

_DEFAULT_PLANNING_HORIZON = 12

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Monte Carlo pricing and capacity scheduling for a foundry-style business.",
)
console = Console()


def _summary_table(summary: pd.DataFrame) -> Table:
    """Render the scenario summary as a Rich table."""
    table = Table(title="Scenario summary", show_lines=False)
    table.add_column("Scenario", style="bold")
    table.add_column("P80 floor", justify="right")
    table.add_column("Target quote", justify="right")
    table.add_column("Expedited quote", justify="right")
    table.add_column("Avg margin", justify="right")
    table.add_column("Parallelism", justify="right")
    for _, row in summary.iterrows():
        table.add_row(
            str(row["scenario"]),
            f"${float(row['p80_economic_floor']):,.0f}",
            f"${float(row['suggested_target_quote']):,.0f}",
            f"${float(row['suggested_expedited_quote']):,.0f}",
            f"{float(row['avg_margin_at_target']) * 100:.1f}%",
            f"{float(row['parallelism_multiplier']):.2f}x",
        )
    return table


def _schedule_table(schedule: pd.DataFrame) -> Table:
    """Render a backlog schedule as a Rich table."""
    table = Table(title="Backlog schedule", show_lines=False)
    for column in ("job_id", "customer", "completion_week", "lateness_weeks"):
        table.add_column(column)
    table.add_column("late_penalty", justify="right")
    table.add_column("net_value", justify="right")
    for _, row in schedule.iterrows():
        table.add_row(
            str(row["job_id"]),
            str(row["customer"]),
            str(int(row["completion_week"])),
            str(int(row["lateness_weeks"])),
            f"${float(row['late_penalty']):,.0f}",
            f"${float(row['net_value']):,.0f}",
        )
    return table


def _write_report_and_charts(
    results: pd.DataFrame, summary: pd.DataFrame, out_dir: Path, metadata: dict[str, str]
) -> None:
    """Generate the markdown report and both distribution charts."""
    report_path = generate_markdown_report(summary, out_dir, metadata)
    price_path = save_price_distribution(results, out_dir)
    floor_path = save_economic_floor_distribution(results, out_dir)
    console.print(f"[green]Wrote[/green] {report_path}")
    console.print(f"[green]Wrote[/green] {price_path}")
    console.print(f"[green]Wrote[/green] {floor_path}")


@app.command()
def simulate(
    config: Annotated[
        Path, typer.Option(help="Path to the foundry config YAML.")
    ] = _DEFAULT_CONFIG,
    scenarios: Annotated[
        Path, typer.Option(help="Path to the scenarios YAML.")
    ] = _SAMPLE_SCENARIOS,
    out: Annotated[Path, typer.Option(help="Directory for the output artifacts.")] = Path(
        "outputs/demo"
    ),
) -> None:
    """Run the Monte Carlo simulation and write results.parquet + summary.csv."""
    cfg, settings = load_config(config)
    scenario_list = load_scenarios(scenarios, cfg)
    console.print(
        f"Simulating [bold]{len(scenario_list)}[/bold] scenarios "
        f"x [bold]{settings.n_sims:,}[/bold] iterations (seed {settings.random_seed})..."
    )
    results = simulate_many(scenario_list, cfg, settings)
    summary = summarize_results(results, cfg, scenario_list)
    write_outputs(results, summary, out)
    console.print(_summary_table(summary))
    console.print(f"[green]Wrote[/green] {out / 'results.parquet'}")
    console.print(f"[green]Wrote[/green] {out / 'summary.csv'}")


@app.command()
def report(
    results: Annotated[
        Path, typer.Option(help="Path to a results.parquet from `simulate`.")
    ] = Path("outputs/demo/results.parquet"),
    out: Annotated[Path, typer.Option(help="Directory for the report and charts.")] = Path(
        "outputs/demo"
    ),
) -> None:
    """Regenerate the markdown report and charts from a results.parquet."""
    results_df = pd.read_parquet(results)
    summary = summarize_from_results(results_df)
    metadata = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "results": str(results),
        "scenarios": ", ".join(dict.fromkeys(results_df["scenario"].tolist())),
    }
    _write_report_and_charts(results_df, summary, out, metadata)


@app.command()
def schedule(
    config: Annotated[
        Path, typer.Option(help="Path to the foundry config YAML.")
    ] = _DEFAULT_CONFIG,
    backlog: Annotated[Path, typer.Option(help="Path to the backlog CSV.")] = _SAMPLE_BACKLOG,
    out: Annotated[Path, typer.Option(help="Directory for the schedule CSV.")] = Path(
        "outputs/schedule"
    ),
    scenarios: Annotated[
        Path | None,
        typer.Option(help="Optional scenarios YAML; estimates their displacement cost."),
    ] = None,
) -> None:
    """Schedule the backlog and, if a scenario is given, estimate its displacement cost."""
    cfg, _ = load_config(config)
    backlog_df = load_backlog(backlog)
    scheduled = schedule_backlog(backlog_df, cfg.n_lines, _DEFAULT_PLANNING_HORIZON)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scheduled.to_csv(out / "schedule.csv", index=False)
    console.print(_schedule_table(scheduled))
    console.print(f"[green]Wrote[/green] {out / 'schedule.csv'}")

    if scenarios is not None:
        scenario_list = load_scenarios(scenarios, cfg)
        for scenario in scenario_list:
            estimate = estimate_schedule_opportunity_cost(
                backlog_df, scenario, cfg, _DEFAULT_PLANNING_HORIZON
            )
            cost = float(estimate["opportunity_cost_from_schedule"])
            delayed = estimate["delayed_jobs"]
            console.print(
                f"\n[bold]{scenario.name}[/bold]: accepting this job costs the backlog "
                f"[bold]${cost:,.0f}[/bold] in net value; {len(delayed)} job(s) slip later."
            )


@app.command()
def demo(
    out: Annotated[Path, typer.Option(help="Directory for the demo artifacts.")] = Path(
        "outputs/demo"
    ),
    config: Annotated[
        Path, typer.Option(help="Path to the foundry config YAML.")
    ] = _DEFAULT_CONFIG,
    scenarios: Annotated[
        Path, typer.Option(help="Path to the scenarios YAML.")
    ] = _SAMPLE_SCENARIOS,
) -> None:
    """Run the whole pipeline on the sample data: simulate, write artifacts, report."""
    cfg, settings = load_config(config)
    scenario_list = load_scenarios(scenarios, cfg)
    console.print("[bold]Running the foundry pricing demo end to end...[/bold]")
    results = simulate_many(scenario_list, cfg, settings)
    summary = summarize_results(results, cfg, scenario_list)
    write_outputs(results, summary, out)
    console.print(_summary_table(summary))
    console.print(f"[green]Wrote[/green] {out / 'results.parquet'}")
    console.print(f"[green]Wrote[/green] {out / 'summary.csv'}")

    metadata = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "random_seed": str(settings.random_seed),
        "config": str(config),
        "scenarios": str(scenarios),
    }
    _write_report_and_charts(results, summary, out, metadata)
    console.print("\n[bold green]Demo complete.[/bold green]")


if __name__ == "__main__":
    app()
