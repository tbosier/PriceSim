"""Central logging setup.

A single ``setup_logging`` call keeps log formatting consistent across the CLI,
the API, and any scripts. Business output goes through Rich in the CLI; this is
for diagnostic logging, not user-facing tables.
"""

from __future__ import annotations

import logging

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root logging once and return the package logger.

    Args:
        level: Logging level (e.g. ``logging.INFO``).

    Returns:
        The ``foundry_pricing`` logger.
    """
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        _CONFIGURED = True
    logger = logging.getLogger("foundry_pricing")
    logger.setLevel(level)
    return logger
