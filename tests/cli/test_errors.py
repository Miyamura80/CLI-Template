"""Tests for error handling."""

import sys

from rich.markup import MarkupError

from src.utils.errors import (
    _friendly_handler,
    _original_excepthook,
    install_error_handler,
)
from tests.test_template import TestTemplate


class TestErrorHandler(TestTemplate):
    def test_install_friendly_handler(self):
        install_error_handler(debug=False)
        assert sys.excepthook is not _original_excepthook
        # Restore
        sys.excepthook = _original_excepthook

    def test_install_debug_handler(self):
        install_error_handler(debug=True)
        assert sys.excepthook is not _original_excepthook
        # Restore
        sys.excepthook = _original_excepthook

    def test_bracket_laden_message_does_not_double_fault(self):
        # A MarkupError's own message embeds the offending brackets; rendering
        # it through the friendly panel must not raise a *second* MarkupError
        # inside sys.excepthook.
        exc = MarkupError("closing tag '[/]' at position 7 has nothing to close")
        _friendly_handler(type(exc), exc, None)  # must not raise

    def test_exception_message_with_open_tag_does_not_raise(self):
        exc = KeyError("[bold]red[/]")
        _friendly_handler(type(exc), exc, None)  # must not raise
