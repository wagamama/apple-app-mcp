"""JXA script builders for Apple Calendar operations."""

from __future__ import annotations

import json


class CalendarQueryBuilder:
    """Build JXA snippets that use CalendarCore."""

    def list_calendars(self) -> str:
        """Build a script that lists Calendar.app calendars."""
        return "JSON.stringify(CalendarCore.listCalendars());"

    def events_in_range(
        self,
        start: str,
        end: str,
        calendar_ids: list[str] | None = None,
    ) -> str:
        """Build a script that fetches event series overlapping a date range."""
        if not start or not end:
            raise ValueError("start and end are required")
        return (
            "JSON.stringify(CalendarCore.eventsInRange("
            f"{json.dumps(start)}, "
            f"{json.dumps(end)}, "
            f"{json.dumps(calendar_ids or [])}"
            "));"
        )
