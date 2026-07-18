"""Random-draw helpers for the Monte Carlo engine.

All randomness flows through an explicit ``numpy.random.Generator`` so runs are
reproducible given a seed. The truncated normal is intentionally the simple
"draw-then-clip" approximation; see ``docs/formulas.md`` for the caveat.
"""

from __future__ import annotations

import numpy as np


def truncated_normal(
    rng: np.random.Generator,
    mean: float,
    sd: float,
    size: int,
    lower: float = 0.0,
) -> np.ndarray:
    """Draw from a normal distribution, clipping values below ``lower``.

    This is a fast, good-enough approximation of a truncated normal: we draw
    ``normal(mean, sd)`` and clamp the lower tail. For the small standard
    deviations used here the distortion is minor and keeps the code readable.

    Args:
        rng: Seeded NumPy generator.
        mean: Distribution mean.
        sd: Standard deviation (``0`` yields a constant array of ``mean``).
        size: Number of draws.
        lower: Inclusive lower bound.

    Returns:
        A 1-D array of shape ``(size,)`` with no values below ``lower``.
    """
    draws = rng.normal(loc=mean, scale=sd, size=size)
    return np.clip(draws, a_min=lower, a_max=None)


def sample_downtime_hours(
    rng: np.random.Generator,
    probability: float,
    mean: float,
    sd: float,
    size: int,
) -> np.ndarray:
    """Draw downtime hours as ``Bernoulli(p) * truncated_normal(mean, sd)``.

    Each iteration either has a downtime event (with ``probability``) or none.
    When it does, the number of lost hours is a non-negative truncated normal.

    Args:
        rng: Seeded NumPy generator.
        probability: Probability of a downtime event per iteration, in ``[0, 1]``.
        mean: Mean downtime hours given an event.
        sd: Standard deviation of downtime hours given an event.
        size: Number of draws.

    Returns:
        A 1-D array of shape ``(size,)`` of non-negative downtime hours.
    """
    occurred = rng.random(size=size) < probability
    hours = truncated_normal(rng, mean=mean, sd=sd, size=size, lower=0.0)
    return np.where(occurred, hours, 0.0)
