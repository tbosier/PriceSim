"""Enable ``python -m foundry_pricing`` by delegating to the Typer app."""

from __future__ import annotations

from .cli import app

if __name__ == "__main__":
    app()
