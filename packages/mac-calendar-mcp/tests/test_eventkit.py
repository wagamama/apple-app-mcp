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

    with patch(
        "apple_calendar_mcp.index.eventkit.execute_with_eventkit",
        return_value=expected,
    ) as execute:
        result = fetch_snapshot_from_eventkit(
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
            calendar_names_or_ids=[calendar_name],
        )

    assert result == expected
    script = execute.call_args.args[0]
    assert json.dumps(calendar_name) in script
    assert execute.call_args.kwargs["timeout"] == EVENTKIT_FETCH_TIMEOUT_SECONDS
