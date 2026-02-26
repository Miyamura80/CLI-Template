"""Security ratings from Snyk and Socket.dev for package trust verification."""

import importlib.metadata
import json
import urllib.request
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_PACKAGE_NAME = "miyamura80-cli-template"
_TIMEOUT = 5

_CONFIG_DIR = Path.home() / ".config" / _PACKAGE_NAME
_STATE_FILE = _CONFIG_DIR / "state.json"

# Public assessment page URLs
_SNYK_ADVISOR_URL = "https://snyk.io/advisor/python/{package}"
_SNYK_SECURITY_URL = "https://security.snyk.io/package/pip/{package}"
_SOCKET_URL = "https://socket.dev/pypi/package/{package}"

console = Console(stderr=True)


def _load_state() -> dict[str, Any]:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())
    return {}


def _save_state(state: dict[str, Any]) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def get_snyk_advisor_url(package: str | None = None) -> str:
    """Build Snyk Advisor URL for the package."""
    return _SNYK_ADVISOR_URL.format(package=package or _PACKAGE_NAME)


def get_snyk_security_url(package: str | None = None) -> str:
    """Build Snyk Security DB URL for the package."""
    return _SNYK_SECURITY_URL.format(package=package or _PACKAGE_NAME)


def get_socket_url(package: str | None = None) -> str:
    """Build Socket.dev URL for the package."""
    return _SOCKET_URL.format(package=package or _PACKAGE_NAME)


def _fetch_snyk_score(package: str) -> float | None:
    """Try to fetch the Snyk Advisor health score (0.0–1.0)."""
    try:
        url = f"https://snyk.io/advisor/python/{package}/badge.svg"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            svg = resp.read().decode()
        # Badge SVG contains text like "health 85/100"
        for token in svg.split(">"):
            if "/100" in token:
                raw = token.split("/100")[0].strip().split(">")[-1]
                digits = "".join(c for c in raw if c.isdigit())
                if digits:
                    return int(digits) / 100
    except Exception:
        pass
    return None


def _score_bar(score: float) -> str:
    """Render a score as a coloured bar: ████████░░ 80%."""
    filled = round(score * 10)
    empty = 10 - filled
    pct = round(score * 100)
    if pct >= 70:
        colour = "green"
    elif pct >= 40:
        colour = "yellow"
    else:
        colour = "red"
    bar = "█" * filled + "░" * empty
    return f"[{colour}]{bar}[/{colour}] {pct}%"


def _score_label(score: float) -> str:
    """Human-readable label for a health score."""
    pct = round(score * 100)
    if pct >= 85:
        return "[bold green]Healthy[/bold green]"
    if pct >= 70:
        return "[green]Good[/green]"
    if pct >= 40:
        return "[yellow]Fair[/yellow]"
    return "[red]Needs attention[/red]"


def display_security_panel(package: str | None = None) -> None:
    """Display a rich panel with security ratings and links."""
    pkg = package or _PACKAGE_NAME
    version = importlib.metadata.version(pkg)

    snyk_advisor = get_snyk_advisor_url(pkg)
    snyk_security = get_snyk_security_url(pkg)
    socket_url = get_socket_url(pkg)

    # Attempt to fetch Snyk health score
    snyk_score = _fetch_snyk_score(pkg)

    # Build table
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Provider", style="bold cyan", min_width=18)
    table.add_column("Assessment", min_width=28)
    table.add_column("Link", style="dim")

    # Snyk Advisor row
    snyk_detail = "Package health analysis"
    if snyk_score is not None:
        snyk_detail = f"Health: {_score_bar(snyk_score)}  {_score_label(snyk_score)}"
    table.add_row("🛡️  Snyk Advisor", snyk_detail, snyk_advisor)

    # Snyk Security DB row
    table.add_row(
        "🛡️  Snyk Security",
        "Known vulnerability database",
        snyk_security,
    )

    # Socket.dev row
    table.add_row(
        "🔒 Socket.dev",
        "Supply-chain & dependency risk",
        socket_url,
    )

    panel = Panel(
        table,
        title=f"[bold]Security Ratings — {pkg} v{version}[/bold]",
        subtitle="[dim]Verify this package on independent security platforms[/dim]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def show_first_install_notice() -> None:
    """Print a one-time security notice on first run after install."""
    state = _load_state()
    if state.get("security_notice_shown"):
        return

    pkg = _PACKAGE_NAME
    console.print(
        f"[bold green]🔒 Security verification available for {pkg}[/bold green]\n"
        f"   Snyk:   {get_snyk_advisor_url(pkg)}\n"
        f"   Socket: {get_socket_url(pkg)}\n"
        f"   [dim]Run 'mycli security' for full details.[/dim]"
    )

    state["security_notice_shown"] = True
    _save_state(state)


def security_command() -> None:
    """Show security ratings and links to Snyk & Socket.dev assessments."""
    display_security_panel()
