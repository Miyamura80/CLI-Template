"""Tests for the scaffold command."""

from pathlib import Path

from typer.testing import CliRunner

from cli import _register_builtin_commands, _register_user_commands, app
from tests.test_template import TestTemplate

runner = CliRunner()

_register_builtin_commands()
_register_user_commands()

_COMMANDS_DIR = Path(__file__).parent.parent.parent / "commands"


class TestScaffold(TestTemplate):
    def test_init_creates_file(self):
        target = _COMMANDS_DIR / "test_scaffold_cmd.py"
        try:
            result = runner.invoke(
                app, ["init", "test_scaffold_cmd", "--desc", "A test command"]
            )
            assert result.exit_code == 0
            assert target.exists()
            content = target.read_text()
            assert "A test command" in content
        finally:
            if target.exists():
                target.unlink()

    def test_init_rejects_bad_name(self):
        result = runner.invoke(app, ["init", "Bad-Name"])
        assert result.exit_code == 1

    def test_init_rejects_duplicate(self):
        target = _COMMANDS_DIR / "test_dup_cmd.py"
        try:
            target.write_text("# existing command\n")
            result = runner.invoke(app, ["init", "test_dup_cmd"])
            assert result.exit_code == 1
        finally:
            if target.exists():
                target.unlink()
