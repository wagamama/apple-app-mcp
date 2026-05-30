from __future__ import annotations

from apple_calendar_mcp.recurrence import expand_occurrences

BASE_EVENT = {
    "event_id": "e1",
    "start_date": "2026-01-05T10:00:00Z",
    "end_date": "2026-01-05T11:00:00Z",
    "excluded_dates": [],
}


def test_non_recurring_event_returns_single_occurrence():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": ""},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert result.unsupported is False
    assert [o.start for o in result.occurrences] == ["2026-01-05T10:00:00Z"]


def test_daily_count():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=DAILY;COUNT=3"},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2026-01-06T10:00:00Z",
        "2026-01-07T10:00:00Z",
    ]


def test_weekly_byday():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=WEEKLY;COUNT=4;BYDAY=MO,WE"},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2026-01-07T10:00:00Z",
        "2026-01-12T10:00:00Z",
        "2026-01-14T10:00:00Z",
    ]


def test_monthly_interval_count():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=MONTHLY;INTERVAL=2;COUNT=3"},
        "2026-01-01T00:00:00Z",
        "2026-08-01T00:00:00Z",
        max_occurrences=100,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2026-03-05T10:00:00Z",
        "2026-05-05T10:00:00Z",
    ]


def test_yearly_until():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=YEARLY;UNTIL=2028-01-06T00:00:00Z"},
        "2026-01-01T00:00:00Z",
        "2030-01-01T00:00:00Z",
        max_occurrences=100,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2027-01-05T10:00:00Z",
        "2028-01-05T10:00:00Z",
    ]


def test_excluded_dates_remove_occurrence():
    result = expand_occurrences(
        {
            **BASE_EVENT,
            "recurrence": "FREQ=DAILY;COUNT=3",
            "excluded_dates": ["2026-01-06T10:00:00Z"],
        },
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2026-01-07T10:00:00Z",
    ]


def test_max_occurrence_cap():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=DAILY"},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=2,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2026-01-06T10:00:00Z",
    ]


def test_unsupported_rule_is_reported():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=WEEKLY;BYSETPOS=1"},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert result.unsupported is True
    assert result.occurrences == []
    assert "BYSETPOS" in result.reason
