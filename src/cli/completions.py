"""Shell completions install command."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer()
console = Console(stderr=True)


class Shell(StrEnum):
    bash = "bash"
    zsh = "zsh"
    fish = "fish"


_COMPLETION_SCRIPTS = {
    Shell.bash: 'eval "$(_MYCLI_COMPLETE=bash_source mycli)"',
    Shell.zsh: 'eval "$(_MYCLI_COMPLETE=zsh_source mycli)"',
    Shell.fish: "_MYCLI_COMPLETE=fish_source mycli | source",
}

_RC_FILES = {
    Shell.bash: Path.home() / ".bashrc",
    Shell.zsh: Path.home() / ".zshrc",
    Shell.fish: Path.home() / ".config" / "fish" / "config.fish",
}


@app.command()
def install(
    shell: Annotated[Shell, typer.Argument(help="Shell to install completions for.")],
) -> None:
    """Install shell completions for mycli."""
    snippet = _COMPLETION_SCRIPTS[shell]
    rc_file = _RC_FILES[shell]

    if rc_file.exists() and snippet in rc_file.read_text():
        console.print(f"[yellow]Completions already installed in {rc_file}[/yellow]")
        return

    rc_file.parent.mkdir(parents=True, exist_ok=True)
    with open(rc_file, "a") as f:
        f.write(f"\n# mycli completions\n{snippet}\n")

    console.print("[green]Completions installed![/green] Restart your shell or run:")
    console.print(f"  source {rc_file}")


@app.command()
def show(
    shell: Annotated[Shell, typer.Argument(help="Shell to show completions for.")],
) -> None:
    """Print the completion script to stdout."""
    typer.echo(_COMPLETION_SCRIPTS[shell])
