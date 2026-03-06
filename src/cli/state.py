"""Global CLI state via contextvars."""

from contextvars import ContextVar
from enum import StrEnum
from functools import wraps
from typing import Any

from rich.console import Console

from common.dry_run import dry_run as dry_run
from common.dry_run import is_dry_run as is_dry_run

console = Console(stderr=True)


class Verbosity(StrEnum):
    NORMAL = "normal"
    VERBOSE = "verbose"
    QUIET = "quiet"
    DEBUG = "debug"


class OutputFormat(StrEnum):
    TABLE = "table"
    JSON = "json"
    PLAIN = "plain"


verbosity: ContextVar[Verbosity] = ContextVar("verbosity", default=Verbosity.NORMAL)
output_format: ContextVar[OutputFormat] = ContextVar(
    "output_format", default=OutputFormat.TABLE
)


def is_verbose() -> bool:
    return verbosity.get() in (Verbosity.VERBOSE, Verbosity.DEBUG)


def is_quiet() -> bool:
    return verbosity.get() == Verbosity.QUIET


def is_debug() -> bool:
    return verbosity.get() == Verbosity.DEBUG


def dry_run_guard(description: str):
    """Decorator that short-circuits a command when --dry-run is active."""

    def decorator(func: Any):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            if is_dry_run():
                console.print(f"[yellow][DRY RUN][/yellow] Would {description}")
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator
