from __future__ import annotations

from apple_calendar_mcp.index.schema import (
    INSERT_ATTENDEE_SQL,
    INSERT_CALENDAR_SQL,
    INSERT_EVENT_SQL,
    INSERT_OCCURRENCE_SQL,
    INSERT_SEARCH_SQL,
)


def test_schema_creates_expected_tables(calendar_db):
    rows = calendar_db.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    ).fetchall()
    names = {row["name"] for row in rows}

    assert "calendars" in names
    assert "events" in names
    assert "occurrences" in names
    assert "attendees" in names
    assert "event_search" in names
    assert "events_fts" in names
    assert "failed_index_jobs" in names


def test_insert_rows_and_search(calendar_db):
    calendar_db.execute(
        INSERT_CALENDAR_SQL,
        ("cal-1", "Work", "#ff0000", 1, "Work calendar"),
    )
    calendar_db.execute(
        INSERT_EVENT_SQL,
        (
            "event-1",
            "cal-1",
            "Budget review",
            "Room 1",
            "Discuss budget",
            "https://example.test",
            "confirmed",
            0,
            "2026-05-01T10:00:00Z",
            "2026-05-01T11:00:00Z",
            "2026-04-01T00:00:00Z",
            "",
            0,
        ),
    )
    calendar_db.execute(
        INSERT_OCCURRENCE_SQL,
        (
            "event-1",
            "cal-1",
            "2026-05-01T10:00:00Z",
            "2026-05-01T11:00:00Z",
            0,
        ),
    )
    calendar_db.execute(
        INSERT_ATTENDEE_SQL,
        ("event-1", "Alice", "alice@example.test", "accepted"),
    )
    cursor = calendar_db.execute(
        INSERT_SEARCH_SQL,
        (
            "event-1",
            "2026-05-01T10:00:00Z",
            "Budget review",
            "Room 1",
            "Discuss budget",
            "https://example.test",
            "Alice alice@example.test",
            "Work",
        ),
    )
    calendar_db.commit()

    rows = calendar_db.execute(
        "SELECT title FROM events_fts WHERE events_fts MATCH ?",
        ("budget",),
    ).fetchall()

    assert cursor.lastrowid is not None
    assert [row["title"] for row in rows] == ["Budget review"]
