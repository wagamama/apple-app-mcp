from __future__ import annotations

import pytest

from apple_calendar_mcp.index.sync import record_failed_jobs, sync_from_snapshot


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


def test_sync_from_snapshot_rejects_failed_source_jobs(calendar_db):
    snapshot = {
        "calendars": [
            {
                "id": "slow",
                "name": "Slow",
                "color": "#ff0000",
                "writable": True,
                "description": "",
            }
        ],
        "events": [],
        "failed_jobs": [
            {
                "job_key": "calendar:slow",
                "calendar_id": "slow",
                "error_type": "calendar_event_fetch_failed",
                "error_message": "Calendar event fetch timed out or failed",
            }
        ],
    }

    with pytest.raises(ValueError, match="failed source jobs"):
        sync_from_snapshot(
            calendar_db,
            snapshot,
            coverage_start="2026-01-01T00:00:00Z",
            coverage_end="2027-01-01T00:00:00Z",
            max_occurrences_per_series=100,
        )

    calendar_count = calendar_db.execute(
        "SELECT COUNT(*) FROM calendars"
    ).fetchone()[0]
    assert calendar_count == 0


def test_record_failed_jobs_preserves_first_seen_on_retry(calendar_db):
    job = {
        "job_key": "source:eventkit",
        "calendar_id": None,
        "error_type": "eventkit_fetch_failed",
        "error_message": "access denied",
    }
    record_failed_jobs(calendar_db, [job])
    calendar_db.execute(
        "UPDATE failed_index_jobs SET first_seen = ? WHERE job_key = ?",
        ("2026-01-01 00:00:00", job["job_key"]),
    )
    calendar_db.commit()

    record_failed_jobs(calendar_db, [job])

    row = calendar_db.execute(
        "SELECT first_seen, attempt_count FROM failed_index_jobs "
        "WHERE job_key = ?",
        (job["job_key"],),
    ).fetchone()
    assert tuple(row) == ("2026-01-01 00:00:00", 2)
