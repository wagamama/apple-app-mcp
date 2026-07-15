from __future__ import annotations

import json
from typing import Any

from apple_calendar_mcp.eventkit_helper import (
    EventKitHelperError,
    execute_eventkit_helper,
    get_eventkit_helper_script,
)
from apple_calendar_mcp.executor import JXAError, execute_with_eventkit

EVENTKIT_FETCH_TIMEOUT_SECONDS = 30


def fetch_snapshot_from_eventkit(
    *,
    start: str,
    end: str,
    calendar_names_or_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Read an occurrence snapshot through Apple's supported EventKit API."""
    helper_script = get_eventkit_helper_script()
    if helper_script is not None:
        try:
            return execute_eventkit_helper(
                script_path=helper_script,
                start=start,
                end=end,
                calendar_names_or_ids=calendar_names_or_ids,
            )
        except EventKitHelperError as exc:
            raise JXAError(str(exc)) from exc

    script = (
        "JSON.stringify(EventKitCore.snapshot("
        f"{json.dumps(start)}, {json.dumps(end)}, "
        f"{json.dumps(calendar_names_or_ids or [])}));"
    )
    try:
        return execute_with_eventkit(
            script,
            timeout=EVENTKIT_FETCH_TIMEOUT_SECONDS,
        )
    except JXAError as exc:
        raise JXAError(
            f"{exc}. Run 'mac-calendar-mcp authorize' to install a stable "
            "Calendar permission identity.",
            exc.stderr,
        ) from exc
