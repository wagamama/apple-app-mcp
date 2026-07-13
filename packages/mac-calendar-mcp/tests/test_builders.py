from __future__ import annotations

import pytest

from apple_calendar_mcp.builders import CalendarQueryBuilder
from apple_calendar_mcp.jxa import CALENDAR_CORE_JS


def test_list_calendars_script_uses_calendar_core():
    js = CalendarQueryBuilder().list_calendars()

    assert "CalendarCore.listCalendars()" in js
    assert "JSON.stringify" in js


def test_events_in_range_serializes_inputs_safely():
    js = CalendarQueryBuilder().events_in_range(
        start="2026-01-01",
        end="2026-02-01",
        calendar_ids=['Work "Calendar"'],
    )

    assert '\\"Calendar\\"' in js
    assert "CalendarCore.eventsInRange" in js


def test_events_in_range_requires_start_and_end():
    with pytest.raises(ValueError, match="start and end"):
        CalendarQueryBuilder().events_in_range(start="", end="2026-01-01")


def test_calendar_core_uses_safe_calendar_id_helper():
    assert "safeCalendarId(calendar)" in CALENDAR_CORE_JS
    assert ".calendarIdentifier()" not in CALENDAR_CORE_JS


def test_calendar_core_resolves_calendar_by_absolute_path():
    assert "function getCalendarApplication()" in CALENDAR_CORE_JS
    assert '"/System/Applications/Calendar.app"' in CALENDAR_CORE_JS
    assert '"/Applications/Calendar.app"' in CALENDAR_CORE_JS
    assert '"Calendar"' in CALENDAR_CORE_JS
    assert "app.name();" in CALENDAR_CORE_JS
    assert "app.calendars();" not in CALENDAR_CORE_JS
    assert "const Calendar = getCalendarApplication();" in CALENDAR_CORE_JS
    assert 'const Calendar = Application("Calendar");' not in CALENDAR_CORE_JS


def test_calendar_core_uses_supported_calendar_date_filter_operator():
    assert "if (!start || !end || start >= end) return [];" in CALENDAR_CORE_JS
    assert "endDate: { _greaterThan: start }" in CALENDAR_CORE_JS
    assert "eventOverlapsRange(event, start, end)" in CALENDAR_CORE_JS
    assert "_and" not in CALENDAR_CORE_JS
    assert "_lt" not in CALENDAR_CORE_JS
    assert "_gt" not in CALENDAR_CORE_JS
