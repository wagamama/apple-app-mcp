from __future__ import annotations

from typing import Any

from apple_calendar_mcp.eventkit_helper import (
    EventKitHelperError,
    execute_eventkit_helper,
    get_eventkit_helper,
)
from apple_calendar_mcp.executor import JXAError


def fetch_snapshot_from_eventkit(
    *,
    start: str,
    end: str,
    calendar_names_or_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Read an occurrence snapshot through Apple's supported EventKit API."""
    helper_path = get_eventkit_helper()
    if helper_path is None:
        raise JXAError(
            "EventKit helper is not installed or is invalid. Run "
            "'mac-calendar-mcp authorize'."
        )
    try:
        return execute_eventkit_helper(
            helper_path=helper_path,
            start=start,
            end=end,
            calendar_names_or_ids=calendar_names_or_ids,
        )
    except EventKitHelperError as exc:
        raise JXAError(
            f"{exc}. Run 'mac-calendar-mcp authorize' to repair Calendar "
            "access."
        ) from exc
