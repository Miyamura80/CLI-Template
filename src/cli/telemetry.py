"""Anonymous telemetry - local JSON, opt-out, first-run notice."""

import hashlib
import importlib.metadata
import json
import os
import platform
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

app = typer.Typer()
console = Console(stderr=True)

_CONFIG_DIR = Path.home() / ".config" / "cli-template"
_TELEMETRY_FILE = _CONFIG_DIR / "telemetry.json"
_STATE_FILE = _CONFIG_DIR / "state.json"
_MAX_EVENTS = 1000


def _machine_id() -> str:
    """Anonymous machine ID: truncated SHA-256 hash of hostname."""
    raw = socket.gethostname()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_state() -> dict[str, Any]:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())
    return {}


def _save_state(state: dict[str, Any]) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def is_enabled() -> bool:
    """Check if telemetry is enabled."""
    if os.environ.get("CLI_TELEMETRY_DISABLED", "").strip() in ("1", "true", "yes"):
        return False
    state = _load_state()
    return state.get("telemetry_enabled", True)


def show_first_run_notice() -> None:
    """Print a one-time telemetry notice."""
    state = _load_state()
    if state.get("telemetry_notice_shown"):
        return
    console.print(
        "[dim]Anonymous usage telemetry is enabled. "
        "Run 'mycli telemetry disable' or set CLI_TELEMETRY_DISABLED=1 to opt out.[/dim]"
    )
    state["telemetry_notice_shown"] = True
    _save_state(state)


def record_event(command: str, duration: float, success: bool) -> None:
    """Record a telemetry event to the local JSON file."""
    if not is_enabled():
        return

    event = {
        "command": command,
        "duration_s": round(duration, 3),
        "success": success,
        "cli_version": importlib.metadata.version("cli-template"),
        "python_version": platform.python_version(),
        "os": platform.system(),
        "machine_id": _machine_id(),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    events: list[dict] = []
    if _TELEMETRY_FILE.exists():
        try:
            events = json.loads(_TELEMETRY_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            events = []

    events.append(event)
    # Cap at _MAX_EVENTS
    if len(events) > _MAX_EVENTS:
        events = events[-_MAX_EVENTS:]

    _TELEMETRY_FILE.write_text(json.dumps(events, indent=2))


@app.command()
def status() -> None:
    """Show telemetry status."""
    enabled = is_enabled()
    state = "enabled" if enabled else "disabled"
    console.print(f"Telemetry is [bold]{state}[/bold]")
    if _TELEMETRY_FILE.exists():
        try:
            events = json.loads(_TELEMETRY_FILE.read_text())
            console.print(f"Local events recorded: {len(events)}")
        except (json.JSONDecodeError, OSError):
            pass


@app.command()
def enable() -> None:
    """Enable anonymous telemetry."""
    state = _load_state()
    state["telemetry_enabled"] = True
    _save_state(state)
    console.print("[green]Telemetry enabled.[/green]")


@app.command()
def disable() -> None:
    """Disable anonymous telemetry."""
    state = _load_state()
    state["telemetry_enabled"] = False
    _save_state(state)
    console.print("[yellow]Telemetry disabled.[/yellow]")
