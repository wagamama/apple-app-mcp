from __future__ import annotations

from unittest.mock import patch

import pytest

from apple_calendar_mcp.executor import JXAError
from apple_calendar_mcp.index.eventkit import (
    fetch_snapshot_from_eventkit,
)


def test_fetch_snapshot_requires_authorized_helper():
    with (
        patch(
            "apple_calendar_mcp.index.eventkit.get_eventkit_helper",
            return_value=None,
        ),
        pytest.raises(JXAError, match="mac-calendar-mcp authorize"),
    ):
        fetch_snapshot_from_eventkit(
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
        )


def test_fetch_snapshot_uses_authorized_helper_when_installed(tmp_path):
    expected = {
        "source": "eventkit",
        "calendars": [{"id": "cal-1", "name": "Work"}],
        "events": [{"event_id": "event-1"}],
        "failed_jobs": [],
    }

    with (
        patch(
            "apple_calendar_mcp.index.eventkit.get_eventkit_helper",
            return_value=tmp_path,
        ),
        patch(
            "apple_calendar_mcp.index.eventkit.execute_eventkit_helper",
            return_value=expected,
        ) as execute,
    ):
        result = fetch_snapshot_from_eventkit(
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
            calendar_names_or_ids=["Work"],
        )

    assert result == expected
    execute.assert_called_once_with(
        helper_path=tmp_path,
        start="2026-01-01T00:00:00Z",
        end="2027-01-01T00:00:00Z",
        calendar_names_or_ids=["Work"],
    )
