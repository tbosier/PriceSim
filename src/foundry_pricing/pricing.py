"""Pure pricing-formula functions.

Every function here is deterministic and side-effect free so it can be unit
tested in isolation and reused by the Monte Carlo engine, the CLI, and the API.
The multipliers encode the core business intuition: scarce capacity, whole-
factory concentration, and complex retooling all push the quote up.
"""

from __future__ import annotations

from .constants import RETOOLING_MULTIPLIERS


def scarcity_multiplier(utilization: float) -> float:
    """Return the price multiplier driven by how busy the factory already is.

    A near-full factory has little slack, so reserving capacity costs more.

    Args:
        utilization: Current factory utilization in ``[0, 1]``.

    Returns:
        A multiplier applied to opportunity cost.
    """
    if utilization < 0.60:
        return 0.85
    if utilization < 0.80:
        return 1.00
    if utilization < 0.90:
        return 1.25
    if utilization < 0.97:
        return 1.60
    return 2.25


def parallelism_multiplier(lines_requested: int, total_lines: int) -> float:
    """Return the premium for concentrating capacity across many lines at once.

    Reserving the whole factory for one week is far more disruptive than
    reserving one line for four weeks, even though both consume the same
    number of line-weeks. This multiplier prices that concentration.

    Args:
        lines_requested: Number of lines the job wants simultaneously.
        total_lines: Total number of lines in the factory.

    Returns:
        A multiplier applied to opportunity cost (and expedite premium).
    """
    share = lines_requested / total_lines
    if share <= 0.25:
        return 1.00
    if share <= 0.50:
        return 1.15
    if share <= 0.75:
        return 1.35
    return 1.75


def retooling_multiplier(complexity: str) -> float:
    """Return the tooling-cost multiplier for a retooling complexity level.

    Args:
        complexity: One of ``low``, ``medium``, ``high``, ``extreme``.

    Returns:
        The multiplier applied to tooling parts cost.

    Raises:
        KeyError: If ``complexity`` is not a recognized level.
    """
    return RETOOLING_MULTIPLIERS[complexity]


def target_quote(risk_floor: float, target_margin: float) -> float:
    """Mark up the risk-adjusted economic floor to hit a target margin.

    Args:
        risk_floor: The economic floor at the chosen risk percentile.
        target_margin: Desired margin as a fraction in ``[0, 0.95)``.

    Returns:
        The suggested quote price before any expedite premium.
    """
    return risk_floor / (1.0 - target_margin)


def expedited_quote(target_quote: float, expedite_wtp: float, parallelism_mult: float) -> float:
    """Apply an expedite premium scaled by how much the factory is monopolized.

    Args:
        target_quote: The base suggested quote.
        expedite_wtp: Customer's expedite willingness-to-pay fraction.
        parallelism_mult: The parallelism multiplier for this job.

    Returns:
        The suggested expedited quote (``>= target_quote`` for non-negative WTP).
    """
    return target_quote * (1.0 + expedite_wtp * parallelism_mult)
