"""Error handling with Rich panels in normal mode, tracebacks in debug."""

import sys
from types import TracebackType

from rich.console import Console
from rich.panel import Panel

console = Console(stderr=True)

_original_excepthook = sys.excepthook


def _friendly_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    _exc_tb: TracebackType | None,
) -> None:
    if exc_type is KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        return
    console.print(
        Panel(
            f"[bold red]{exc_type.__name__}[/bold red]: {exc_value}",
            title="Error",
            subtitle="Use --debug for full traceback",
            border_style="red",
        )
    )


def _debug_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    _exc_tb: TracebackType | None,
) -> None:
    if exc_type is KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        return
    console.print_exception(show_locals=True)


def install_error_handler(debug: bool = False) -> None:
    """Install a Rich error handler as sys.excepthook."""
    sys.excepthook = _debug_handler if debug else _friendly_handler
