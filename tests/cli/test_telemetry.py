"""Tests for telemetry integration."""

import json
from unittest.mock import patch

from src.cli.telemetry import (
    _post_event,
    is_enabled,
    record_event,
    show_first_run_notice,
)
from tests.test_template import TestTemplate


class TestFirstRunNotice(TestTemplate):
    """show_first_run_notice() displays once then never again."""

    @patch("src.cli.telemetry.save_state")
    @patch("src.cli.telemetry.load_state", side_effect=lambda: {})
    @patch("src.cli.telemetry.is_enabled", return_value=True)
    @patch("src.cli.telemetry.console")
    def test_notice_shown_on_first_run(self, mock_console, _enabled, _load, mock_save):
        show_first_run_notice()
        mock_console.print.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["telemetry_notice_shown"] is True

    @patch("src.cli.telemetry.save_state")
    @patch("src.cli.telemetry.load_state", side_effect=lambda: {})
    @patch("src.cli.telemetry.is_enabled", return_value=False)
    @patch("src.cli.telemetry.console")
    def test_notice_not_shown_when_disabled(
        self, mock_console, _enabled, _load, mock_save
    ):
        show_first_run_notice()
        mock_console.print.assert_not_called()
        # Still marks as shown so we don't re-check every run
        mock_save.assert_called_once()

    @patch("src.cli.telemetry.save_state")
    @patch(
        "src.cli.telemetry.load_state", return_value={"telemetry_notice_shown": True}
    )
    @patch("src.cli.telemetry.console")
    def test_notice_not_shown_again(self, mock_console, _load, mock_save):
        show_first_run_notice()
        mock_console.print.assert_not_called()
        mock_save.assert_not_called()


class TestIsEnabled(TestTemplate):
    """Telemetry can be disabled via state or env var."""

    @patch("src.cli.telemetry.load_state", return_value={})
    def test_enabled_by_default(self, _load):
        assert is_enabled() is True

    @patch("src.cli.telemetry.load_state", return_value={"telemetry_enabled": False})
    def test_disabled_via_state(self, _load):
        assert is_enabled() is False

    @patch.dict("os.environ", {"CLI_TELEMETRY_DISABLED": "1"})
    @patch("src.cli.telemetry.load_state", return_value={})
    def test_disabled_via_env_var(self, _load):
        assert is_enabled() is False

    @patch("src.cli.telemetry.global_config")
    @patch("src.cli.telemetry.load_state", return_value={})
    def test_disabled_via_config(self, _load, mock_gc):
        mock_gc.configure_mock(**{"telemetry.enabled": False})
        assert is_enabled() is False


class TestRecordEvent(TestTemplate):
    """record_event() writes to local JSON and optionally POSTs."""

    @patch("src.cli.telemetry._TELEMETRY_FILE")
    @patch("src.cli.telemetry._CONFIG_DIR")
    @patch("src.cli.telemetry.is_enabled", return_value=False)
    def test_noop_when_disabled(self, _enabled, _dir, mock_file):
        record_event("test", 1.0, True)
        mock_file.write_text.assert_not_called()

    @patch("src.cli.telemetry._post_event")
    @patch("src.cli.telemetry.global_config")
    @patch("src.cli.telemetry.is_enabled", return_value=True)
    @patch("src.cli.telemetry._TELEMETRY_FILE")
    @patch("src.cli.telemetry._CONFIG_DIR")
    def test_records_event_locally(self, _dir, mock_file, _enabled, mock_gc, mock_post):
        mock_file.configure_mock(**{"exists.return_value": False})
        mock_gc.configure_mock(**{"telemetry.endpoint": None})

        record_event("hello", 0.5, True)

        mock_file.write_text.assert_called_once()
        written = json.loads(mock_file.write_text.call_args[0][0])
        assert len(written) == 1
        assert written[0]["command"] == "hello"
        assert written[0]["success"] is True
        mock_post.assert_not_called()

    @patch("src.cli.telemetry._post_event")
    @patch("src.cli.telemetry.global_config")
    @patch("src.cli.telemetry.is_enabled", return_value=True)
    @patch("src.cli.telemetry._TELEMETRY_FILE")
    @patch("src.cli.telemetry._CONFIG_DIR")
    def test_posts_when_endpoint_configured(
        self, _dir, mock_file, _enabled, mock_gc, mock_post
    ):
        mock_file.configure_mock(**{"exists.return_value": False})
        mock_gc.configure_mock(
            **{"telemetry.endpoint": "https://example.com/telemetry"}
        )

        record_event("deploy", 2.1, False)

        mock_post.assert_called_once()
        event = mock_post.call_args[0][1]
        assert event["command"] == "deploy"
        assert event["success"] is False


class TestPostEvent(TestTemplate):
    """_post_event() POSTs JSON on a daemon thread and silently handles failures."""

    @patch("src.cli.telemetry.urllib.request.urlopen")
    @patch("src.cli.telemetry.urllib.request.Request")
    @patch("src.cli.telemetry.threading.Thread")
    def test_posts_json(self, mock_thread_cls, _request_cls, _urlopen):
        mock_thread = mock_thread_cls.return_value
        event = {"command": "test", "duration_s": 1.0}
        _post_event("https://example.com/t", event)

        mock_thread_cls.assert_called_once()
        assert mock_thread_cls.call_args[1]["daemon"] is True
        mock_thread.start.assert_called_once()

    @patch(
        "src.cli.telemetry.urllib.request.urlopen",
        side_effect=Exception("network error"),
    )
    @patch("src.cli.telemetry.urllib.request.Request")
    @patch("src.cli.telemetry.threading.Thread")
    def test_fires_daemon_thread(self, mock_thread_cls, _request_cls, _urlopen):
        mock_thread = mock_thread_cls.return_value
        _post_event("https://example.com/t", {"command": "test"})
        assert mock_thread_cls.call_args[1]["daemon"] is True
        mock_thread.start.assert_called_once()
