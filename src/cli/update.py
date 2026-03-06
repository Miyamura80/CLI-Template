"""Self-update via PyPI version check + uv."""

import importlib.metadata
import json
import subprocess
import urllib.request

import typer
from packaging.version import Version
from rich.console import Console

from src.cli.state import is_dry_run

console = Console(stderr=True)

_PACKAGE_NAME = "miyamura80-cli-template"
_PYPI_URL = f"https://pypi.org/pypi/{_PACKAGE_NAME}/json"
_TIMEOUT = 5


def update_command() -> None:
    """Check for updates and upgrade if a newer version is available."""
    current = importlib.metadata.version(_PACKAGE_NAME)
    console.print(f"Current version: [bold]{current}[/bold]")

    if is_dry_run():
        console.print(
            f"[yellow][DRY RUN][/yellow] Would GET {_PYPI_URL} to check for updates"
        )
        console.print(
            f"[yellow][DRY RUN][/yellow] Would run: uv pip install --upgrade {_PACKAGE_NAME}"
            " (only if a newer version is found)"
        )
        return
        return

    try:
        req = urllib.request.Request(_PYPI_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        latest_str = data["info"]["version"]
    except Exception:
        console.print("[yellow]Could not check PyPI for updates.[/yellow]")
        raise typer.Exit(code=0) from None

    if Version(latest_str) <= Version(current):
        console.print(f"[green]Already up to date![/green] ({current})")
        raise typer.Exit(code=0)

    console.print(f"New version available: [bold green]{latest_str}[/bold green]")
    try:
        subprocess.run(
            ["uv", "pip", "install", "--upgrade", _PACKAGE_NAME],
            check=True,
        )
        console.print(f"[green]Updated to {latest_str}![/green]")
    except subprocess.CalledProcessError:
        console.print(
            "[red]Update failed.[/red] Try manually: uv pip install --upgrade miyamura80-cli-template"
        )
        raise typer.Exit(code=1) from None
