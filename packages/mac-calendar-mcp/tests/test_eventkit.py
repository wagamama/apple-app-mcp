from __future__ import annotations

import json
from unittest.mock import patch

from apple_calendar_mcp.index.eventkit import (
    EVENTKIT_FETCH_TIMEOUT_SECONDS,
    fetch_snapshot_from_eventkit,
)


def test_fetch_snapshot_from_eventkit_serializes_inputs_safely():
    calendar_name = 'Work "); throw new Error("injected") //'
    expected = {
        "source": "eventkit",
        "calendars": [],
        "events": [],
        "failed_jobs": [],
    }

    with (
        patch(
            "apple_calendar_mcp.index.eventkit.get_eventkit_helper_script",
            return_value=None,
        ),
        patch(
            "apple_calendar_mcp.index.eventkit.execute_with_eventkit",
            return_value=expected,
        ) as execute,
    ):
        result = fetch_snapshot_from_eventkit(
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
            calendar_names_or_ids=[calendar_name],
        )

    assert result == expected
    script = execute.call_args.args[0]
    assert json.dumps(calendar_name) in script
    assert execute.call_args.kwargs["timeout"] == EVENTKIT_FETCH_TIMEOUT_SECONDS


def test_fetch_snapshot_uses_authorized_helper_when_installed(tmp_path):
    script_path = tmp_path / "main.scpt"
    script_path.write_bytes(b"compiled")
    expected = {
        "source": "eventkit",
        "calendars": [{"id": "cal-1", "name": "Work"}],
        "events": [{"event_id": "event-1"}],
        "failed_jobs": [],
    }

    with (
        patch(
            "apple_calendar_mcp.index.eventkit.get_eventkit_helper_script",
            return_value=script_path,
        ),
        patch(
            "apple_calendar_mcp.index.eventkit.execute_eventkit_helper",
            return_value=expected,
        ) as execute,
        patch("apple_calendar_mcp.index.eventkit.execute_with_eventkit") as raw,
    ):
        result = fetch_snapshot_from_eventkit(
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
            calendar_names_or_ids=["Work"],
        )

    assert result == expected
    execute.assert_called_once_with(
        script_path=script_path,
        start="2026-01-01T00:00:00Z",
        end="2027-01-01T00:00:00Z",
        calendar_names_or_ids=["Work"],
    )
    raw.assert_not_called()
