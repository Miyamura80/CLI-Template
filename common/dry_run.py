"""Dry-run flag shared across all layers (CLI, utils, scripts)."""

from contextvars import ContextVar

dry_run: ContextVar[bool] = ContextVar("dry_run", default=False)


def is_dry_run() -> bool:
    return dry_run.get()
