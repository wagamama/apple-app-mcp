from __future__ import annotations

from apple_calendar_mcp.index.search import search_events
from apple_calendar_mcp.index.sync import sync_from_snapshot


def _seed(calendar_db):
    sync_from_snapshot(
        calendar_db,
        {
            "calendars": [
                {
                    "id": "cal-1",
                    "name": "Work",
                    "color": "#ff0000",
                    "writable": True,
                    "description": "",
                }
            ],
            "events": [
                {
                    "event_id": "event-1",
                    "calendar_id": "cal-1",
                    "calendar_name": "Work",
                    "title": "Budget review",
                    "location": "Room 1",
                    "notes": "Discuss budget",
                    "url": "",
                    "status": "confirmed",
                    "all_day": False,
                    "start_date": "2026-05-01T10:00:00Z",
                    "end_date": "2026-05-01T11:00:00Z",
                    "modified_at": "2026-04-01T00:00:00Z",
                    "recurrence": "",
                    "excluded_dates": [],
                    "attendees": [],
                }
            ],
        },
        coverage_start="2026-01-01T00:00:00Z",
        coverage_end="2027-01-01T00:00:00Z",
        max_occurrences_per_series=100,
    )


def test_search_events_finds_notes(calendar_db):
    _seed(calendar_db)

    results = search_events(calendar_db, "budget", limit=20, offset=0)

    assert len(results) == 1
    assert results[0]["event_id"] == "event-1"
    assert results[0]["title"] == "Budget review"


def test_search_events_date_filter(calendar_db):
    _seed(calendar_db)

    results = search_events(
        calendar_db,
        "budget",
        start="2026-06-01T00:00:00Z",
        limit=20,
        offset=0,
    )

    assert results == []


def test_search_events_field_filter(calendar_db):
    _seed(calendar_db)

    assert (
        search_events(
            calendar_db, "Room", fields=["location"], limit=20, offset=0
        )[0]["event_id"]
        == "event-1"
    )
    assert (
        search_events(calendar_db, "Room", fields=["title"], limit=20, offset=0)
        == []
    )


def test_search_events_handles_malformed_fts_query(calendar_db):
    _seed(calendar_db)

    assert (
        search_events(calendar_db, "budget(", limit=20, offset=0)[0][
            "event_id"
        ]
        == "event-1"
    )


def test_search_events_handles_malformed_field_query(calendar_db):
    _seed(calendar_db)

    assert (
        search_events(
            calendar_db,
            "Room(",
            fields=["location"],
            limit=20,
            offset=0,
        )[0]["event_id"]
        == "event-1"
    )
