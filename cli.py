"""Main CLI entry point."""

import importlib.metadata
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
import yaml

from src.cli.state import (
    OutputFormat,
    Verbosity,
    dry_run,
    output_format,
    verbosity,
)
from src.utils.errors import install_error_handler


class FormatChoice(StrEnum):
    table = "table"
    json = "json"
    plain = "plain"


_FORMAT_MAP = {
    FormatChoice.table: OutputFormat.TABLE,
    FormatChoice.json: OutputFormat.JSON,
    FormatChoice.plain: OutputFormat.PLAIN,
}

app = typer.Typer(
    name="mycli",
    help="CLI Template - a batteries-included Python CLI.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _load_cli_branding() -> tuple[str, str]:
    """Read emoji and primary color from global_config.yaml. Returns (emoji, primary_color)."""
    try:
        config_path = Path(__file__).parent / "common" / "global_config.yaml"
        data = yaml.safe_load(config_path.read_text()) or {}
        cli_conf = data.get("cli", {})
        emoji = cli_conf.get("emoji", "") or ""
        primary = cli_conf.get("primary_color", "cyan") or "cyan"
        return emoji, primary
    except Exception:
        return "", "cyan"


def _version_callback(value: bool) -> None:
    if value:
        version = importlib.metadata.version("cli-template")
        emoji, _ = _load_cli_branding()
        prefix = f"{emoji} " if emoji else ""
        typer.echo(f"{prefix}mycli {version}")
        raise typer.Exit()


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Increase output verbosity."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-essential output."),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug mode with full tracebacks."),
    ] = False,
    fmt: Annotated[
        FormatChoice,
        typer.Option("--format", "-f", help="Output format."),
    ] = FormatChoice.table,
    dry: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview actions without executing."),
    ] = False,
    version: Annotated[  # noqa: ARG001
        bool | None,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Process global flags before any subcommand."""
    # Set verbosity
    if debug:
        verbosity.set(Verbosity.DEBUG)
    elif quiet:
        verbosity.set(Verbosity.QUIET)
    elif verbose:
        verbosity.set(Verbosity.VERBOSE)

    # Set output format
    output_format.set(_FORMAT_MAP[fmt])

    # Set dry run
    dry_run.set(dry)

    # Install error handler
    install_error_handler(debug=debug)


_builtins_registered = False
_user_commands_registered = False


def _register_builtin_commands() -> None:
    """Register built-in CLI commands (idempotent)."""
    global _builtins_registered  # noqa: PLW0603
    if _builtins_registered:
        return
    _builtins_registered = True

    from src.cli.completions import app as completions_app
    from src.cli.scaffold import init_command
    from src.cli.telemetry import app as telemetry_app
    from src.cli.update import update_command

    app.add_typer(completions_app, name="completions", help="Manage shell completions.")
    app.add_typer(telemetry_app, name="telemetry", help="Manage anonymous telemetry.")
    app.command(name="update")(update_command)
    app.command(name="init")(init_command)


def _register_user_commands() -> None:
    """Discover and register user commands from commands/ (idempotent)."""
    global _user_commands_registered  # noqa: PLW0603
    if _user_commands_registered:
        return
    _user_commands_registered = True

    from commands import discover_commands

    discover_commands(app)


def main_cli() -> None:
    """Entry point called by the console script."""
    _register_builtin_commands()
    _register_user_commands()

    version = importlib.metadata.version("cli-template")
    emoji, primary = _load_cli_branding()
    prefix = f"{emoji} " if emoji else ""
    app.info.help = (
        f"{prefix}[{primary}]CLI Template[/{primary}] "
        f"[dim]v{version}[/dim] - a batteries-included Python CLI."
    )

    app()
