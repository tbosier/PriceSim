"""Shared constants: multiplier tables and simulation guardrails.

Keeping these in one place makes the pricing logic auditable at a glance and
easy to tune without hunting through the codebase.
"""

from __future__ import annotations

from typing import Final

# Retooling complexity -> cost multiplier applied to tooling parts cost.
RETOOLING_MULTIPLIERS: Final[dict[str, float]] = {
    "low": 0.85,
    "medium": 1.00,
    "high": 1.35,
    "extreme": 1.80,
}

# Valid retooling complexity levels (order = increasing complexity).
RETOOLING_LEVELS: Final[tuple[str, ...]] = ("low", "medium", "high", "extreme")

# Minimum floor used when drawing truncated-normal tooling weeks. Tooling can
# never realistically take zero time, so we clamp to a small positive number.
MIN_TOOLING_WEEKS: Final[float] = 0.1
