from __future__ import annotations

import json
from typing import Any

from apple_calendar_mcp.executor import execute_with_eventkit

EVENTKIT_FETCH_TIMEOUT_SECONDS = 30


def fetch_snapshot_from_eventkit(
    *,
    start: str,
    end: str,
    calendar_names_or_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Read an occurrence snapshot through Apple's supported EventKit API."""
    script = (
        "JSON.stringify(EventKitCore.snapshot("
        f"{json.dumps(start)}, {json.dumps(end)}, "
        f"{json.dumps(calendar_names_or_ids or [])}));"
    )
    return execute_with_eventkit(script, timeout=EVENTKIT_FETCH_TIMEOUT_SECONDS)
