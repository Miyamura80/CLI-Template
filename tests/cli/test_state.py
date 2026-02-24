"""Tests for CLI global state."""

from src.cli.state import (
    OutputFormat,
    Verbosity,
    dry_run,
    dry_run_guard,
    is_debug,
    is_dry_run,
    is_quiet,
    is_verbose,
    output_format,
    verbosity,
)
from tests.test_template import TestTemplate


class TestVerbosity(TestTemplate):
    def test_default_is_normal(self):
        assert verbosity.get() == Verbosity.NORMAL

    def test_is_verbose_when_verbose(self):
        token = verbosity.set(Verbosity.VERBOSE)
        try:
            assert is_verbose()
            assert not is_quiet()
            assert not is_debug()
        finally:
            verbosity.reset(token)

    def test_is_quiet_when_quiet(self):
        token = verbosity.set(Verbosity.QUIET)
        try:
            assert is_quiet()
            assert not is_verbose()
        finally:
            verbosity.reset(token)

    def test_is_debug_when_debug(self):
        token = verbosity.set(Verbosity.DEBUG)
        try:
            assert is_debug()
            assert is_verbose()
        finally:
            verbosity.reset(token)


class TestOutputFormat(TestTemplate):
    def test_default_is_table(self):
        assert output_format.get() == OutputFormat.TABLE


class TestDryRun(TestTemplate):
    def test_default_is_false(self):
        assert not is_dry_run()

    def test_dry_run_guard_skips_when_active(self):
        token = dry_run.set(True)
        try:
            called = False

            @dry_run_guard("do something")
            def action():
                nonlocal called
                called = True

            action()
            assert not called
        finally:
            dry_run.reset(token)

    def test_dry_run_guard_runs_when_inactive(self):
        called = False

        @dry_run_guard("do something")
        def action():
            nonlocal called
            called = True

        action()
        assert called
