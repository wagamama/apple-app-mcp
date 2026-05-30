from __future__ import annotations

from apple_calendar_mcp.index.sync import sync_from_snapshot


def test_sync_from_snapshot_inserts_event_occurrence_attendee(calendar_db):
    snapshot = {
        "calendars": [
            {
                "id": "cal-1",
                "name": "Work",
                "color": "#ff0000",
                "writable": True,
                "description": "Work calendar",
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
                "url": "https://example.test",
                "status": "confirmed",
                "all_day": False,
                "start_date": "2026-05-01T10:00:00Z",
                "end_date": "2026-05-01T11:00:00Z",
                "modified_at": "2026-04-01T00:00:00Z",
                "recurrence": "",
                "excluded_dates": [],
                "attendees": [
                    {
                        "display_name": "Alice",
                        "email": "alice@example.test",
                        "participation_status": "accepted",
                    }
                ],
            }
        ],
    }

    result = sync_from_snapshot(
        calendar_db,
        snapshot,
        coverage_start="2026-01-01T00:00:00Z",
        coverage_end="2027-01-01T00:00:00Z",
        max_occurrences_per_series=100,
    )

    assert result.added == 1
    assert calendar_db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert (
        calendar_db.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]
        == 1
    )
    assert (
        calendar_db.execute("SELECT COUNT(*) FROM attendees").fetchone()[0] == 1
    )
