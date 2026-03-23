"""Interactive onboarding CLI for project setup."""

import asyncio
import os
import random
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import questionary
import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).parent

# Branding configuration -------------------------------------------------------

#: (name, primary_color, secondary_color, description)
COLOR_PALETTES: list[tuple[str, str, str, str]] = [
    ("Ocean", "bright_cyan", "blue", "Cool blues and teals"),
    ("Forest", "bright_green", "green", "Natural greens"),
    ("Sunset", "yellow", "bright_red", "Warm and fiery"),
    ("Aurora", "bright_magenta", "bright_cyan", "Vibrant purples and teals"),
    ("Rose", "bright_red", "magenta", "Warm pinks and reds"),
    ("Gold", "bright_yellow", "yellow", "Rich golden tones"),
    ("Slate", "bright_white", "cyan", "Clean whites with cyan"),
    ("Midnight", "bright_blue", "blue", "Deep ocean blues"),
]

PRESET_EMOJIS: list[str] = [
    "🚀", "⚡", "🔥", "🛠️", "🎯", "✨", "🌟", "💎",
    "🦊", "🐉", "🌊", "🌿", "🔮", "🧪", "🎨", "🤖",
]

# ------------------------------------------------------------------------------

app = typer.Typer(
    name="onboard",
    help="Interactive onboarding CLI for project setup.",
    invoke_without_command=True,
)


def _read_pyproject_name() -> str:
    """Read the current project name from pyproject.toml."""
    text = (PROJECT_ROOT / "pyproject.toml").read_text()
    match = re.search(r'^name\s*=\s*"([^"]*)"', text, re.MULTILINE)
    return match.group(1) if match else ""


def _validate_kebab_case(value: str) -> bool | str:
    """Validate that the value is kebab-case (lowercase, hyphens, no spaces)."""
    if not value:
        return "Project name cannot be empty."
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", value):
        return "Must be kebab-case (e.g. my-cool-project). Lowercase letters, digits, hyphens only."
    return True


def _validate_cli_name(value: str) -> bool | str:
    """Validate that the value is a valid CLI command name."""
    if not value:
        return "CLI name cannot be empty."
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", value):
        return "Must be lowercase with optional hyphens (e.g. my-tool). No spaces or underscores."
    return True


def _read_cli_name() -> str:
    """Read the current CLI entry-point name from pyproject.toml [project.scripts]."""
    text = (PROJECT_ROOT / "pyproject.toml").read_text()
    match = re.search(r"^\[project\.scripts\]\s*\n(\S+)\s*=", text, re.MULTILINE)
    return match.group(1) if match else "mycli"


STEPS: list[tuple[str, str]] = [
    ("Branding", "branding"),
    ("Rename", "rename"),
    ("CLI Name", "cli_name"),
    ("Dependencies", "deps"),
    ("Environment Variables", "env"),
    ("Pre-commit Hooks", "hooks"),
    ("Media Generation", "media"),
    ("Jules Workflows", "jules"),
]

STEP_FUNCTIONS: dict[str, object] = {}


def _run_orchestrator() -> None:
    """Run the full onboarding flow, executing all steps in sequence."""
    project_name = _read_pyproject_name()
    rprint(
        Panel(
            f"[bold]{project_name}[/bold]\n\n"
            "This wizard will guide you through:\n"
            "  1. Branding - Pick emoji and colour scheme for the CLI\n"
            "  2. Rename - Set project name and description\n"
            "  3. CLI Name - Choose the CLI command name\n"
            "  4. Dependencies - Install project dependencies\n"
            "  5. Environment - Configure API keys and secrets\n"
            "  6. Hooks - Activate pre-commit hooks\n"
            "  7. Media - Generate banner and logo assets\n"
            "  8. Jules - Enable/disable automated maintenance workflows",
            title="Welcome to Project Onboarding",
            border_style="blue",
        )
    )

    total = len(STEPS)
    results: dict[str, str] = {}  # label -> "completed" | "skipped" | "skipped (failed)"

    idx = 0
    while idx < total:
        label, cmd_name = STEPS[idx]
        rprint(f"\n[bold cyan]--- Step {idx + 1}/{total}: {label} ---[/bold cyan]")

        choices = ["Yes", "Skip"]
        if idx > 0:
            choices.append("← Go back")

        answer = questionary.select(
            "Run this step?",
            choices=choices,
            default="Yes",
        ).ask()
        if answer is None:
            raise typer.Abort()

        if answer == "← Go back":
            idx -= 1
            continue

        if answer == "Skip":
            results[label] = "skipped"
            rprint(f"[yellow]- {label} skipped[/yellow]")
            idx += 1
            continue

        try:
            step_fn = STEP_FUNCTIONS[cmd_name]
            step_fn()  # type: ignore[operator]
            results[label] = "completed"
        except (typer.Exit, SystemExit) as exc:
            code = getattr(exc, "code", getattr(exc, "exit_code", 1))
            if code != 0:
                rprint(f"[red]✗ {label} failed.[/red]")
                cont = questionary.confirm(
                    "Continue with remaining steps?", default=True
                ).ask()
                if cont is None or not cont:
                    raise typer.Abort() from None
                results[label] = "skipped (failed)"
            else:
                results[label] = "completed"

        idx += 1

    completed = [name for name, status in results.items() if status == "completed"]
    skipped = [
        f"{name} (failed)" if status == "skipped (failed)" else name
        for name, status in results.items()
        if status != "completed"
    ]
    _print_summary(completed, skipped)


def _print_summary(completed: list[str], skipped: list[str]) -> None:
    """Print the final onboarding summary."""
    lines: list[str] = []
    for name in completed:
        lines.append(f"[green]✓[/green] {name}")
    for name in skipped:
        lines.append(f"[yellow]-[/yellow] {name}")
    lines.append("")
    lines.append("[bold]Suggested next commands:[/bold]")
    lines.append("  make test    - Run tests")
    lines.append("  make ci      - Run CI checks")
    lines.append("  make all     - Run main application")

    rprint(Panel("\n".join(lines), title="Onboarding Summary", border_style="green"))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run the full onboarding flow, or use a subcommand for a specific step."""
    if ctx.invoked_subcommand is None:
        _run_orchestrator()


def _save_cli_branding(emoji: str, primary_color: str, secondary_color: str) -> None:
    """Persist emoji and colour settings into common/global_config.yaml."""
    config_path = PROJECT_ROOT / "common" / "global_config.yaml"
    text = config_path.read_text()
    text = re.sub(r'^  emoji:.*$', f'  emoji: "{emoji}"', text, flags=re.MULTILINE)
    text = re.sub(
        r'^  primary_color:.*$',
        f'  primary_color: "{primary_color}"',
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r'^  secondary_color:.*$',
        f'  secondary_color: "{secondary_color}"',
        text,
        flags=re.MULTILINE,
    )
    config_path.write_text(text)


def _pick_emoji() -> str:
    """Prompt the user to pick or enter an emoji. Returns the chosen emoji."""
    rprint("\n[bold]Pick an emoji for your CLI:[/bold]")
    grid = "  ".join(PRESET_EMOJIS[:8]) + "\n  " + "  ".join(PRESET_EMOJIS[8:])
    rprint(f"  {grid}\n")

    emoji_choices = list(PRESET_EMOJIS) + ["✏️  Enter custom emoji"]
    selected = questionary.select("Select an emoji:", choices=emoji_choices).ask()
    if selected is None:
        raise typer.Abort()
    if selected == "✏️  Enter custom emoji":
        selected = questionary.text("Enter your emoji:").ask()
        if selected is None:
            raise typer.Abort()
    return selected


def _pick_color_scheme() -> tuple[str, str]:
    """Prompt the user to pick a colour scheme. Returns (primary_color, secondary_color)."""
    rprint("\n[bold]Pick a colour scheme:[/bold]")
    for name, primary, secondary, desc in COLOR_PALETTES:
        rprint(
            f"  [{primary}]■■■[/{primary}][{secondary}]■■■[/{secondary}]  "
            f"[bold]{name}[/bold] – {desc}"
        )
    rprint()

    palette_choices = [
        f"{name} – {desc}" for name, primary, secondary, desc in COLOR_PALETTES
    ]
    palette_choices += ["🎲 Auto-generate (random)", "✏️  Enter custom colours"]

    while True:
        selection = questionary.select(
            "Select a colour scheme:", choices=palette_choices
        ).ask()
        if selection is None:
            raise typer.Abort()

        if selection == "🎲 Auto-generate (random)":
            result = _try_random_scheme()
            if result is not None:
                return result
            continue  # Reroll or back to manual

        if selection == "✏️  Enter custom colours":
            return _enter_custom_colours()

        # Named palette selected
        for name, primary, secondary, desc in COLOR_PALETTES:
            if selection == f"{name} – {desc}":
                return primary, secondary

    return "cyan", "green"  # unreachable – satisfies type checker


def _try_random_scheme() -> tuple[str, str] | None:
    """Show a randomly generated scheme and return colours, or None to loop again."""
    name, primary, secondary, desc = random.choice(COLOR_PALETTES)
    rprint(
        f"\n  Generated: [bold]{name}[/bold] – {desc}\n"
        f"  [{primary}]■■■ {primary}[/{primary}]  "
        f"[{secondary}]■■■ {secondary}[/{secondary}]\n"
    )
    action = questionary.select(
        "What would you like to do?",
        choices=["✓ Use this scheme", "🎲 Reroll", "← Pick manually"],
        default="✓ Use this scheme",
    ).ask()
    if action is None:
        raise typer.Abort()
    if action == "✓ Use this scheme":
        return primary, secondary
    return None  # Reroll or pick manually → caller loops


def _enter_custom_colours() -> tuple[str, str]:
    """Prompt for custom Rich colour names and return (primary, secondary)."""
    rprint(
        "[dim]  Enter Rich colour names (e.g. cyan, bright_green) "
        "or hex (#ff0000)[/dim]"
    )
    primary = questionary.text("Primary colour:", default="cyan").ask() or "cyan"
    secondary = questionary.text("Secondary colour:", default="green").ask() or "green"
    return primary, secondary


@app.command()
def branding() -> None:
    """Step 1: Choose CLI emoji and colour scheme."""
    selected_emoji = _pick_emoji()
    primary_color, secondary_color = _pick_color_scheme()

    _save_cli_branding(selected_emoji, primary_color, secondary_color)

    rprint(
        Panel(
            f"Emoji:           {selected_emoji}\n"
            f"Primary colour:  [{primary_color}]{primary_color}[/{primary_color}]\n"
            f"Secondary colour:[{secondary_color}]{secondary_color}[/{secondary_color}]",
            title="✅ Branding Complete",
            border_style="green",
        )
    )


_RENAME_EXTENSIONS = {
    ".py", ".toml", ".md", ".mdx", ".yml", ".yaml",
    ".json", ".tsx", ".ts", ".sh", ".txt",
}
_RENAME_SKIP_DIRS = {".venv", ".venv-test", ".git", "node_modules", "__pycache__", ".uv_cache"}
_RENAME_SKIP_FILES = {"uv.lock", "onboard.py"}


def _should_process(path: Path) -> bool:
    """Check if a file should be included in bulk replacement."""
    if not path.is_file() or path.suffix not in _RENAME_EXTENSIONS:
        return False
    if path.name in _RENAME_SKIP_FILES:
        return False
    return not any(part in _RENAME_SKIP_DIRS for part in path.parts)


def _apply_replacements(text: str, replacements: list[tuple[str, str]]) -> str:
    """Apply all replacement pairs to a string."""
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _replace_in_files(replacements: list[tuple[str, str]]) -> list[str]:
    """Replace old->new pairs across all matching files in the project.

    Skips .venv, .git, node_modules, __pycache__, and uv.lock.
    Returns a list of relative paths that were modified.
    """
    changed: list[str] = []
    for path in sorted(PROJECT_ROOT.rglob("*")):
        if not _should_process(path):
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, PermissionError):
            continue
        new_text = _apply_replacements(text, replacements)
        if new_text != text:
            path.write_text(new_text)
            changed.append(str(path.relative_to(PROJECT_ROOT)))
    return changed


#: Template values that get replaced during onboarding rename
_TEMPLATE_PACKAGE_NAME = "miyamura80-cli-template"
_TEMPLATE_OWNER = "Miyamura80"
_TEMPLATE_REPO_NAME = "CLI-Template"


def _read_github_owner_repo() -> tuple[str, str]:
    """Extract owner and repo from the git remote URL. Falls back to placeholders."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=5,
        )
        url = result.stdout.strip()
        match = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$", url)
        if match:
            return match.group(1), match.group(2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "OWNER", "REPO"


def _build_rename_replacements(
    name: str,
    description: str,
    github_owner: str,
    github_repo: str,
    current_name: str = "",
    current_desc: str = "",
    current_owner: str = "",
    current_repo: str = "",
) -> list[tuple[str, str]]:
    """Build replacement pairs for the rename step (order matters, most specific first)."""
    pairs: list[tuple[str, str]] = []

    # Package name (PyPI) - use live current name, fall back to template constant
    from_name = current_name if current_name else _TEMPLATE_PACKAGE_NAME
    pairs.append((from_name, name))
    if "python-template" not in name and from_name != "python-template":
        pairs.append(("python-template", name))

    # GitHub owner/repo URLs
    from_owner = current_owner if current_owner not in ("", "OWNER") else _TEMPLATE_OWNER
    from_repo = current_repo if current_repo not in ("", "REPO") else _TEMPLATE_REPO_NAME
    pairs.append((f"{from_owner}/{from_repo}", f"{github_owner}/{github_repo}"))
    # URL-encoded form (used in badge URLs)
    pairs.append((
        f"{from_owner}%2F{from_repo}",
        f"{github_owner}%2F{github_repo}",
    ))

    # Standalone repo directory name (e.g. in `cd CLI-Template`)
    # Skip if from_repo is a substring of github_repo to avoid double-substitution
    if from_repo not in github_repo:
        pairs.append((from_repo, github_repo))

    # Standalone owner references (CODEOWNERS, author)
    pairs.append((f"@{from_owner}", f"@{github_owner}"))
    pairs.append((f'name = "{from_owner}"', f'name = "{github_owner}"'))

    if description:
        old_desc = current_desc if current_desc else "Add your description here"
        pairs.append((old_desc, description))

    return pairs


def _prompt_github_info(
    force_prompt: bool = False,
) -> tuple[str, str, str, str]:
    """Prompt for GitHub owner and repo, auto-detecting from git remote.

    On first rename, only prompts when sentinels or template values are detected.
    When force_prompt is True (re-rename), always prompts with current values as defaults.

    Returns (new_owner, new_repo, raw_owner, raw_repo) where raw values are the
    pre-prompt values read from git remote (used as "from" values in replacements).
    """
    raw_owner, raw_repo = _read_github_owner_repo()
    github_owner, github_repo = raw_owner, raw_repo

    def _nonempty(v: str) -> bool | str:
        return True if v.strip() else "Cannot be empty."

    if force_prompt or github_owner in ("OWNER", _TEMPLATE_OWNER):
        entered = questionary.text(
            "GitHub owner/org (e.g. my-github-username):",
            default=github_owner if github_owner not in ("OWNER", _TEMPLATE_OWNER) else "",
            validate=_nonempty,
        ).ask()
        if entered is None:
            raise typer.Abort()
        github_owner = entered.strip()

    if force_prompt or github_repo in ("REPO", _TEMPLATE_REPO_NAME):
        entered = questionary.text(
            "GitHub repository name:",
            default=github_repo if github_repo not in ("REPO", _TEMPLATE_REPO_NAME) else "",
            validate=_nonempty,
        ).ask()
        if entered is None:
            raise typer.Abort()
        github_repo = entered.strip()

    return github_owner, github_repo, raw_owner, raw_repo


def _read_pyproject_description() -> str:
    """Read the current project description from pyproject.toml."""
    text = (PROJECT_ROOT / "pyproject.toml").read_text()
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return ""
    project = data.get("project", {})
    description = project.get("description", "")
    return description if isinstance(description, str) else ""


def _update_readme_heading_and_tagline(
    name: str, description: str, changed_files: list[str]
) -> None:
    """Update README heading and tagline via regex (these differ from pyproject.toml values)."""
    readme_path = PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        return
    readme_text = readme_path.read_text()
    new_readme = re.sub(
        r"^#\s+.*$", f"# {name}", readme_text, count=1, flags=re.MULTILINE
    )
    if description:
        new_readme = re.sub(
            r"<b>.*?</b>",
            lambda _: f"<b>{description}</b>",
            new_readme,
            count=1,
        )
    if new_readme != readme_text:
        readme_path.write_text(new_readme)
        rel = str(readme_path.relative_to(PROJECT_ROOT))
        if rel not in changed_files:
            changed_files.append(rel)


def _update_pyproject_description(description: str, changed_files: list[str]) -> None:
    """Ensure pyproject.toml stores the description with TOML-safe escaping."""
    if not description:
        return

    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    text = pyproject_path.read_text()
    safe_description = description.replace('"', '\\"')
    new_text = re.sub(
        r'^description\s*=\s*".*"$',
        lambda _: f'description = "{safe_description}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text != text:
        pyproject_path.write_text(new_text)
        rel = str(pyproject_path.relative_to(PROJECT_ROOT))
        if rel not in changed_files:
            changed_files.append(rel)


@app.command()
def rename() -> None:
    """Step 2: Rename the project and update metadata."""
    current_name = _read_pyproject_name()
    is_re_rename = current_name not in ("python-template", _TEMPLATE_PACKAGE_NAME)
    if is_re_rename:
        rprint(f"[blue]ℹ Project currently named '{current_name}'.[/blue]")
        re_rename = questionary.confirm("Re-rename the project?", default=False).ask()
        if re_rename is None:
            raise typer.Abort()
        if not re_rename:
            return

    name = questionary.text(
        "Project name (kebab-case):",
        default=current_name if is_re_rename else "",
        validate=_validate_kebab_case,
    ).ask()
    if name is None:
        raise typer.Abort()

    current_desc = _read_pyproject_description()
    description = questionary.text(
        "Project description:",
        default=current_desc,
    ).ask()
    if description is None:
        raise typer.Abort()

    github_owner, github_repo, raw_owner, raw_repo = _prompt_github_info(force_prompt=is_re_rename)
    replacements = _build_rename_replacements(
        name, description, github_owner, github_repo,
        current_name, current_desc, raw_owner, raw_repo,
    )
    changed_files = _replace_in_files(replacements)
    _update_pyproject_description(description, changed_files)
    _update_readme_heading_and_tagline(name, description, changed_files)

    summary_lines = [
        f"Package name: [green]{name}[/green]",
        f"GitHub:       [green]{github_owner}/{github_repo}[/green]",
    ]
    if description:
        summary_lines.append(f"Description:  [green]{description}[/green]")
    summary_lines.append("")
    summary_lines.append(f"Updated [bold]{len(changed_files)}[/bold] file(s):")
    summary_lines.extend(f"  [green]{f}[/green]" for f in changed_files)

    rprint(Panel("\n".join(summary_lines), title="✅ Rename Complete", border_style="green"))


def _replace_cli_name(old_name: str, new_name: str) -> list[str]:
    """Replace all occurrences of the old CLI name with the new one across the codebase.

    Returns a list of human-readable change descriptions.
    """
    old_upper = old_name.upper().replace("-", "_")
    new_upper = new_name.upper().replace("-", "_")

    # Map of (file_path, [(old, new), ...])
    replacements: list[tuple[Path, list[tuple[str, str]]]] = [
        (
            PROJECT_ROOT / "pyproject.toml",
            [(f'{old_name} = "cli:main_cli"', f'{new_name} = "cli:main_cli"')],
        ),
        (
            PROJECT_ROOT / "cli.py",
            [
                (f'name="{old_name}"', f'name="{new_name}"'),
                (f"{old_name} {{version}}", f"{new_name} {{version}}"),
            ],
        ),
        (
            PROJECT_ROOT / "src" / "cli" / "completions.py",
            [
                (f'"_{old_upper}_COMPLETE"', f'"_{new_upper}_COMPLETE"'),
                (f'which("{old_name}")', f'which("{new_name}")'),
                (f"completions for {old_name}.", f"completions for {new_name}."),
                (
                    f"[bold]{old_name} --install-completion[/bold]",
                    f"[bold]{new_name} --install-completion[/bold]",
                ),
                (
                    f"[bold]{old_name} --show-completion[/bold]",
                    f"[bold]{new_name} --show-completion[/bold]",
                ),
                (f"# {old_name} completions", f"# {new_name} completions"),
            ],
        ),
        (
            PROJECT_ROOT / "src" / "cli" / "telemetry.py",
            [(f"'{old_name} telemetry disable'", f"'{new_name} telemetry disable'")],
        ),
        (
            PROJECT_ROOT / "src" / "cli" / "scaffold.py",
            [(f"[bold]{old_name} ", f"[bold]{new_name} ")],
        ),
        (
            PROJECT_ROOT / "tests" / "cli" / "test_cli.py",
            [(f'"{old_name}"', f'"{new_name}"')],
        ),
    ]

    # Files where we use regex word-boundary replacement instead of literal
    regex_replacements: list[tuple[Path, str, str]] = [
        (PROJECT_ROOT / "README.md", rf"\b{re.escape(old_name)}\b", new_name),
        (PROJECT_ROOT / "release.md", rf"\b{re.escape(old_name)}\b", new_name),
        (PROJECT_ROOT / ".claude" / "skills" / "usage" / "SKILL.md", rf"\b{re.escape(old_name)}\b", new_name),
    ]

    changes: list[str] = []
    for file_path, pairs in replacements:
        if not file_path.exists():
            continue
        text = file_path.read_text()
        file_changed = False
        for old, new in pairs:
            if old in text:
                text = text.replace(old, new)
                file_changed = True
        if file_changed:
            file_path.write_text(text)
            rel = file_path.relative_to(PROJECT_ROOT)
            changes.append(f"[green]{rel}[/green]")

    for file_path, pattern, repl in regex_replacements:
        if not file_path.exists():
            continue
        text = file_path.read_text()
        new_text = re.sub(pattern, repl, text)
        if new_text != text:
            file_path.write_text(new_text)
            rel = file_path.relative_to(PROJECT_ROOT)
            if f"[green]{rel}[/green]" not in changes:
                changes.append(f"[green]{rel}[/green]")

    return changes


@app.command()
def cli_name() -> None:
    """Step 3: Choose the CLI command name (renames all 'mycli' references)."""
    current = _read_cli_name()
    if current != "mycli":
        rprint(f"[blue]ℹ CLI currently named '{current}'.[/blue]")
        re_rename = questionary.confirm("Re-rename the CLI?", default=False).ask()
        if re_rename is None:
            raise typer.Abort()
        if not re_rename:
            return

    name = questionary.text(
        "CLI command name (e.g. my-tool):",
        default=current,
        validate=_validate_cli_name,
    ).ask()
    if name is None:
        raise typer.Abort()

    if name == current:
        rprint(f"[yellow]Keeping current name '{current}'.[/yellow]")
        return

    changed_files = _replace_cli_name(current, name)

    if not changed_files:
        rprint("[yellow]No files needed updating.[/yellow]")
        return

    rprint(
        Panel(
            f"Renamed CLI from [red]{current}[/red] → [green]{name}[/green]\n\n"
            "Updated files:\n" + "\n".join(f"  {f}" for f in changed_files),
            title="✅ CLI Name Complete",
            border_style="green",
        )
    )


@app.command()
def deps() -> None:
    """Step 4: Install project dependencies."""
    if not shutil.which("uv"):
        rprint(
            "[red]✗ uv is not installed.[/red]\n"
            "  Install it from: [link=https://docs.astral.sh/uv]https://docs.astral.sh/uv[/link]"
        )
        raise typer.Exit(code=1)

    venv_path = PROJECT_ROOT / ".venv"
    if not venv_path.is_dir():
        with console.status("[yellow]Creating virtual environment...[/yellow]"):
            result = subprocess.run(
                ["uv", "venv"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                rprint(f"[red]✗ Failed to create venv:[/red]\n{result.stderr}")
                raise typer.Exit(code=1)
        rprint("[green]✓[/green] Virtual environment created.")

    with console.status("[yellow]Installing dependencies (uv sync)...[/yellow]"):
        result = subprocess.run(
            ["uv", "sync"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        rprint(f"[red]✗ uv sync failed:[/red]\n{result.stderr}")
        raise typer.Exit(code=1)

    rprint("[green]✓ Dependencies installed successfully.[/green]")


def _is_secret_key(name: str) -> bool:
    """Check if an env var name suggests a secret value."""
    return any(word in name.upper() for word in ("SECRET", "KEY", "TOKEN", "PASSWORD"))


def _parse_env_example() -> list[dict[str, str]]:
    """Parse .env.example into a list of entries with group, key, and default value.

    Returns a list of dicts with keys: 'group', 'key', 'default'.
    Comment-only lines set the current group. Blank lines are skipped.
    """
    env_example_path = PROJECT_ROOT / ".env.example"
    if not env_example_path.exists():
        return []

    entries: list[dict[str, str]] = []
    current_group = "General"

    for line in env_example_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_group = line.lstrip("# ").strip()
            continue
        if "=" in line:
            key, _, default = line.partition("=")
            entries.append(
                {"group": current_group, "key": key.strip(), "default": default.strip()}
            )

    return entries


def _load_existing_env() -> dict[str, str]:
    """Load existing .env file into a dict."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return {}

    result: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _has_real_value(value: str) -> bool:
    """Check if an env var value is a real (non-placeholder) value."""
    if not value:
        return False
    placeholders = {
        "sk-...",
        "sk-ant-...",
        "xai-...",
        "gsk_...",
        "pplx-...",
        "AIza...",
        "csk-...",
        "sk-lf-...",
        "pk-lf-...",
        "sk_test_...",
        "ghp_...",
        "postgresql://user:pass@host:port/db",
        "https://your-project.supabase.co",
    }
    return value not in placeholders


def _build_env_choices(
    entries: list[dict[str, str]], existing: dict[str, str]
) -> list[questionary.Choice]:
    """Build questionary checkbox choices from env entries."""
    choices = []
    for entry in entries:
        key = entry["key"]
        has_value = _has_real_value(existing.get(key, ""))
        label = f"[{entry['group']}] {key}"
        if has_value:
            label += " (configured)"
        choices.append(questionary.Choice(title=label, value=key, checked=has_value))
    return choices


def _prompt_env_value(key: str, default: str, current_value: str) -> str:
    """Prompt the user for a single env var value, handling existing values."""
    if _has_real_value(current_value):
        keep = questionary.confirm(
            f"{key} already has a value. Keep existing value?",
            default=True,
        ).ask()
        if keep is None:
            raise typer.Abort()
        if keep:
            return current_value

    prompt_fn = questionary.password if _is_secret_key(key) else questionary.text
    default_hint = default if not _is_secret_key(key) else ""
    new_value = prompt_fn(f"{key}:", default=default_hint).ask()
    if new_value is None:
        raise typer.Abort()
    return new_value


def _write_env_file(entries: list[dict[str, str]], values: dict[str, str]) -> int:
    """Write .env file preserving group structure and custom vars. Returns count of skipped keys."""
    # Load existing env and identify custom variables not in .env.example
    existing = _load_existing_env()
    tracked_keys = {entry["key"] for entry in entries}
    custom_vars = {k: v for k, v in existing.items() if k not in tracked_keys}

    lines: list[str] = []
    current_group = ""
    skipped = 0

    for entry in entries:
        if entry["group"] != current_group:
            if lines:
                lines.append("")
            lines.append(f"# {entry['group']}")
            current_group = entry["group"]

        key = entry["key"]
        if key in values:
            lines.append(f"{key}={values[key]}")
        else:
            lines.append(f"# {key}={entry['default']}")
            skipped += 1

    # Preserve custom variables not in .env.example
    if custom_vars:
        lines.append("")
        lines.append("# Custom variables")
        for key, value in custom_vars.items():
            lines.append(f"{key}={value}")

    (PROJECT_ROOT / ".env").write_text("\n".join(lines) + "\n")
    return skipped


@app.command()
def env() -> None:
    """Step 5: Configure environment variables."""
    entries = _parse_env_example()
    if not entries:
        rprint("[red]✗ No .env.example found.[/red]")
        raise typer.Exit(code=1)

    existing = _load_existing_env()
    choices = _build_env_choices(entries, existing)

    selected_keys = questionary.checkbox(
        "Select environment variables to configure:",
        choices=choices,
    ).ask()
    if selected_keys is None:
        raise typer.Abort()

    selected_set = set(selected_keys)
    values: dict[str, str] = {}
    for entry in entries:
        key = entry["key"]
        if key not in selected_set:
            continue
        values[key] = _prompt_env_value(key, entry["default"], existing.get(key, ""))

    skipped = _write_env_file(entries, values)
    configured = len(values)

    rprint(
        f"\n[green]✓ {configured} key(s) configured, {skipped} key(s) skipped.[/green]"
    )


def _ensure_prek() -> None:
    """Prompt to install prek if not found on PATH."""
    if shutil.which("prek"):
        return
    rprint("[yellow]⚠ prek is not installed.[/yellow]")
    install = questionary.confirm(
        "Install prek via 'uv tool install prek'?",
        default=True,
    ).ask()
    if install is None:
        raise typer.Abort()
    if not install:
        rprint("[red]✗ prek is required for pre-commit hooks.[/red]")
        raise typer.Exit(code=1)
    result = subprocess.run(
        ["uv", "tool", "install", "prek"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        rprint(f"[red]✗ Failed to install prek:[/red]\n{result.stderr}")
        raise typer.Exit(code=1)
    rprint("[green]✓ prek installed.[/green]")


@app.command()
def hooks() -> None:
    """Step 6: Activate pre-commit hooks."""
    config_path = PROJECT_ROOT / "prek.toml"
    if not config_path.exists():
        rprint("[red]✗ prek.toml not found.[/red]")
        raise typer.Exit(code=1)

    _ensure_prek()

    config = tomllib.loads(config_path.read_text())

    table = Table(title="Configured Pre-commit Hooks (prek)")
    table.add_column("Hook ID", style="cyan")
    table.add_column("Description", style="white")

    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            hook_id = hook.get("id", "unknown")
            hook_name = hook.get("name", hook_id)
            table.add_row(hook_id, hook_name)

    console.print(table)
    rprint("")

    activate = questionary.confirm(
        "Activate pre-commit hooks? (Recommended)",
        default=True,
    ).ask()
    if activate is None:
        raise typer.Abort()

    if activate:
        result = subprocess.run(
            ["prek", "install"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            rprint(f"[red]✗ Failed to activate hooks:[/red]\n{result.stderr}")
            raise typer.Exit(code=1)
        rprint("[green]✓ Pre-commit hooks activated (prek).[/green]")
    else:
        rprint(
            "[yellow]Skipped.[/yellow] You can activate later with: "
            "[bold]prek install[/bold]"
        )


def _check_gemini_key() -> bool:
    """Check if GEMINI_API_KEY is available in .env or environment."""
    if os.environ.get("GEMINI_API_KEY"):
        return True
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                value = line.split("=", 1)[1].strip()
                return _has_real_value(value)
    return False


def _run_media_generation(choice: str, project_name: str, theme: str) -> list[str]:
    """Run the selected media generation and return list of generated file paths."""
    # Import here to avoid requiring GEMINI_API_KEY for non-media commands
    from init.generate_banner import generate_banner as gen_banner
    from init.generate_logo import generate_logo as gen_logo

    generated_files: list[str] = []

    if choice in ("Banner only", "Both"):
        with console.status("[yellow]Generating banner...[/yellow]"):
            asyncio.run(gen_banner(title=project_name, theme=theme))
        banner_path = PROJECT_ROOT / "media" / "banner.png"
        generated_files.append(str(banner_path))
        rprint(f"[green]✓[/green] Banner saved to {banner_path}")

    if choice in ("Logo only", "Both"):
        with console.status("[yellow]Generating logo...[/yellow]"):
            asyncio.run(gen_logo(project_name=project_name, theme=theme))
        logo_dir = PROJECT_ROOT / "docs" / "public"
        for name in (
            "logo-light.png",
            "logo-dark.png",
            "icon-light.png",
            "icon-dark.png",
            "favicon.ico",
        ):
            generated_files.append(str(logo_dir / name))
        rprint(f"[green]✓[/green] Logo assets saved to {logo_dir}")

    return generated_files


@app.command()
def media() -> None:
    """Step 7: Generate banner and logo assets."""
    if not _check_gemini_key():
        rprint("[yellow]⚠ GEMINI_API_KEY is not configured.[/yellow]")
        skip = questionary.confirm("Skip media generation?", default=True).ask()
        if skip is None:
            raise typer.Abort()
        if skip:
            rprint("[yellow]Media generation skipped.[/yellow]")
            return

    project_name = _read_pyproject_name()

    rprint()
    theme = questionary.text(
        "Describe the visual theme/style for your project assets:",
        default="modern, clean, minimalist tech aesthetic",
    ).ask()
    if theme is None:
        raise typer.Abort()

    choice = questionary.select(
        "What would you like to generate?",
        choices=["Both", "Banner only", "Logo only", "Skip"],
        default="Both",
    ).ask()
    if choice is None:
        raise typer.Abort()

    if choice == "Skip":
        rprint("[yellow]Media generation skipped.[/yellow]")
        return

    generated_files = _run_media_generation(choice, project_name, theme)
    rprint("\n[green]Generated files:[/green]")
    for f in generated_files:
        rprint(f"  {f}")


_JULES_WORKFLOWS: list[tuple[str, str]] = [
    (
        "jules-prune-unnecessary-code.yml",
        "Dead code cleanup (Wednesdays 2pm UTC)",
    ),
    (
        "jules-find-outdated-docs.yml",
        "Documentation drift check (Wednesdays 4pm UTC)",
    ),
]

_WORKFLOWS_DIR = PROJECT_ROOT / ".github" / "workflows"


def _workflow_enabled(filename: str) -> bool:
    """Check if a Jules workflow file is enabled (not disabled)."""
    return (_WORKFLOWS_DIR / filename).exists() and not (
        _WORKFLOWS_DIR / f"{filename}.disabled"
    ).exists()


def _enable_workflow(filename: str) -> None:
    """Enable a workflow by renaming .disabled back to .yml."""
    disabled = _WORKFLOWS_DIR / f"{filename}.disabled"
    enabled = _WORKFLOWS_DIR / filename
    if disabled.exists() and not enabled.exists():
        disabled.rename(enabled)


def _disable_workflow(filename: str) -> None:
    """Disable a workflow by renaming .yml to .yml.disabled."""
    enabled = _WORKFLOWS_DIR / filename
    if enabled.exists():
        enabled.rename(_WORKFLOWS_DIR / f"{filename}.disabled")


@app.command()
def jules() -> None:
    """Step 8: Enable or disable automated Jules maintenance workflows."""
    if not _WORKFLOWS_DIR.is_dir():
        rprint("[red]✗ .github/workflows/ directory not found.[/red]")
        raise typer.Exit(code=1)

    table = Table(title="Jules Maintenance Workflows")
    table.add_column("Workflow", style="cyan")
    table.add_column("Schedule", style="white")
    table.add_column("Status", style="white")

    for filename, description in _JULES_WORKFLOWS:
        enabled = _workflow_enabled(filename)
        status = "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]"
        table.add_row(filename, description, status)

    console.print(table)
    rprint("")

    choices = []
    for filename, description in _JULES_WORKFLOWS:
        enabled = _workflow_enabled(filename)
        label = f"{description}"
        if enabled:
            label += " (enabled)"
        choices.append(questionary.Choice(title=label, value=filename, checked=enabled))

    selected = questionary.checkbox(
        "Select which Jules workflows to enable:",
        choices=choices,
    ).ask()
    if selected is None:
        raise typer.Abort()

    selected_set = set(selected)
    changes: list[str] = []

    for filename, description in _JULES_WORKFLOWS:
        was_enabled = _workflow_enabled(filename)
        should_enable = filename in selected_set

        if should_enable and not was_enabled:
            _enable_workflow(filename)
            changes.append(f"[green]✓[/green] Enabled {description}")
        elif not should_enable and was_enabled:
            _disable_workflow(filename)
            changes.append(f"[yellow]-[/yellow] Disabled {description}")
        elif should_enable:
            changes.append(f"[blue]·[/blue] {description} (already enabled)")
        else:
            changes.append(f"[blue]·[/blue] {description} (already disabled)")

    rprint(
        Panel(
            "\n".join(changes)
            + "\n\n[dim]Note: JULES_API_KEY secret must be configured in "
            "repository Actions settings.[/dim]",
            title="Jules Workflows",
            border_style="green",
        )
    )


# Register step functions for the orchestrator
STEP_FUNCTIONS.update(
    {
        "branding": branding,
        "rename": rename,
        "cli_name": cli_name,
        "deps": deps,
        "env": env,
        "hooks": hooks,
        "media": media,
        "jules": jules,
    }
)

if __name__ == "__main__":
    app()
