from __future__ import annotations

from unittest.mock import patch

import pytest

from apple_calendar_mcp.executor import (
    JXAError,
    execute_with_core,
    run_jxa,
)


@patch("subprocess.run")
def test_run_jxa_invokes_osascript(mock_run):
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = '{"ok": true}\n'
    mock_run.return_value.stderr = ""

    assert run_jxa("JSON.stringify({ok: true})") == '{"ok": true}'
    mock_run.assert_called_once()
    args = mock_run.call_args.args[0]
    assert args[:3] == ["osascript", "-l", "JavaScript"]


@patch("apple_calendar_mcp.executor.run_jxa")
def test_execute_with_core_parses_json(mock_run):
    mock_run.return_value = '{"calendars": []}'

    assert execute_with_core("JSON.stringify({calendars: []})") == {
        "calendars": []
    }


@patch("apple_calendar_mcp.executor.run_jxa")
def test_execute_with_core_invalid_json_raises(mock_run):
    mock_run.return_value = "debug output"

    with pytest.raises(JXAError, match="Failed to parse JXA output"):
        execute_with_core("script")
