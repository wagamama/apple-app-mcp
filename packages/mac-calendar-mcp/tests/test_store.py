from __future__ import annotations

import sqlite3

from apple_calendar_mcp.index.store import fetch_snapshot_from_store

INSERT_CALENDAR_ITEM_SQL = (
    "INSERT INTO CalendarItem VALUES "
    "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _create_store(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE Calendar (
            ROWID INTEGER PRIMARY KEY,
            title TEXT,
            color TEXT,
            UUID TEXT,
            notes TEXT,
            display_order INTEGER
        );
        CREATE TABLE CalendarItem (
            ROWID INTEGER PRIMARY KEY,
            summary TEXT,
            location_id INTEGER,
            description TEXT,
            start_date REAL,
            end_date REAL,
            all_day INTEGER,
            calendar_id INTEGER,
            status INTEGER,
            url TEXT,
            last_modified REAL,
            unique_identifier TEXT,
            UUID TEXT,
            entity_type INTEGER,
            orig_item_id INTEGER,
            orig_date REAL
        );
        CREATE TABLE OccurrenceCache (
            event_id INTEGER,
            calendar_id INTEGER,
            occurrence_start_date REAL,
            occurrence_end_date REAL
        );
        CREATE TABLE Location (
            ROWID INTEGER PRIMARY KEY,
            title TEXT
        );
        CREATE TABLE Participant (
            identity_id INTEGER,
            email TEXT,
            status INTEGER,
            owner_id INTEGER
        );
        CREATE TABLE Identity (
            display_name TEXT,
            address TEXT
        );
        CREATE TABLE Recurrence (
            ROWID INTEGER PRIMARY KEY,
            frequency INTEGER,
            interval INTEGER,
            count INTEGER,
            end_date REAL,
            specifier TEXT,
            owner_id INTEGER
        );
        """
    )
    return conn


def test_fetch_snapshot_from_store_reads_scoped_occurrences(tmp_path):
    db_path = tmp_path / "Calendar.sqlitedb"
    conn = _create_store(db_path)
    conn.execute(
        "INSERT INTO Calendar VALUES (?, ?, ?, ?, ?, ?)",
        (1, "Calendar", "#a2845e", "cal-uuid", "Main calendar", 1),
    )
    conn.execute("INSERT INTO Location VALUES (?, ?)", (10, "Room 1"))
    conn.execute(
        INSERT_CALENDAR_ITEM_SQL,
        (
            20,
            "Budget review",
            10,
            "Discuss budget",
            788954400.0,
            788958000.0,
            0,
            1,
            1,
            "https://example.test",
            788868000.0,
            "event-uid",
            "event-uuid",
            2,
            None,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO OccurrenceCache VALUES (?, ?, ?, ?)",
        (20, 1, 788954400.0, 788958000.0),
    )
    conn.execute(
        "INSERT INTO Identity VALUES (?, ?)",
        ("Alice", "alice@example.test"),
    )
    conn.execute(
        "INSERT INTO Participant VALUES (?, ?, ?, ?)",
        (1, "alice@example.test", 2, 20),
    )
    conn.commit()
    conn.close()

    snapshot = fetch_snapshot_from_store(
        db_path,
        start="2026-01-01T00:00:00Z",
        end="2026-01-02T00:00:00Z",
        calendar_names_or_ids=["Calendar"],
    )

    assert snapshot["calendars"] == [
        {
            "id": "Calendar",
            "name": "Calendar",
            "color": "#a2845e",
            "writable": True,
            "description": "Main calendar",
        }
    ]
    assert snapshot["events"][0]["event_id"] == "event-uid:2026-01-01T10:00:00Z"
    assert snapshot["events"][0]["calendar_id"] == "Calendar"
    assert snapshot["events"][0]["title"] == "Budget review"
    assert snapshot["events"][0]["location"] == "Room 1"
    assert snapshot["events"][0]["attendees"] == [
        {
            "display_name": "Alice",
            "email": "alice@example.test",
            "participation_status": "accepted",
        }
    ]


def test_fetch_snapshot_from_store_reads_items_without_occurrence_cache(
    tmp_path,
):
    db_path = tmp_path / "Calendar.sqlitedb"
    conn = _create_store(db_path)
    conn.execute(
        "INSERT INTO Calendar VALUES (?, ?, ?, ?, ?, ?)",
        (1, "Calendar", "#a2845e", "cal-uuid", None, 1),
    )
    conn.execute(
        INSERT_CALENDAR_ITEM_SQL,
        (
            20,
            "Direct item",
            None,
            "",
            802249200.0,
            802252800.0,
            0,
            1,
            1,
            "",
            None,
            "event-uid",
            "event-uuid",
            2,
            None,
            None,
        ),
    )
    conn.commit()
    conn.close()

    snapshot = fetch_snapshot_from_store(
        db_path,
        start="2026-06-01T00:00:00Z",
        end="2026-06-05T00:00:00Z",
        calendar_names_or_ids=["Calendar"],
    )

    assert len(snapshot["events"]) == 1
    assert snapshot["events"][0]["event_id"] == "event-uid:2026-06-04T07:00:00Z"
    assert snapshot["events"][0]["title"] == "Direct item"


def test_fetch_snapshot_from_store_converts_weekly_recurrence(tmp_path):
    db_path = tmp_path / "Calendar.sqlitedb"
    conn = _create_store(db_path)
    conn.execute(
        "INSERT INTO Calendar VALUES (?, ?, ?, ?, ?, ?)",
        (1, "Calendar", "#a2845e", "cal-uuid", None, 1),
    )
    conn.execute(
        INSERT_CALENDAR_ITEM_SQL,
        (
            20,
            "Weekly sync",
            None,
            "",
            801385200.0,
            801388800.0,
            0,
            1,
            1,
            "",
            None,
            "event-uid",
            "event-uuid",
            2,
            None,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO Recurrence VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, 2, 1, 0, 804527999.0, "D=0MO", 20),
    )
    conn.commit()
    conn.close()

    snapshot = fetch_snapshot_from_store(
        db_path,
        start="2026-06-01T00:00:00Z",
        end="2026-06-05T00:00:00Z",
        calendar_names_or_ids=["Calendar"],
    )

    assert len(snapshot["events"]) == 1
    assert snapshot["events"][0]["recurrence"] == (
        "FREQ=WEEKLY;UNTIL=2026-06-30T15:59:59Z;BYDAY=MO"
    )


def test_fetch_snapshot_from_store_excludes_overridden_recurrence_dates(
    tmp_path,
):
    db_path = tmp_path / "Calendar.sqlitedb"
    conn = _create_store(db_path)
    conn.execute(
        "INSERT INTO Calendar VALUES (?, ?, ?, ?, ?, ?)",
        (1, "Calendar", "#a2845e", "cal-uuid", None, 1),
    )
    conn.execute(
        INSERT_CALENDAR_ITEM_SQL,
        (
            20,
            "Weekly sync",
            None,
            "",
            801385200.0,
            801388800.0,
            0,
            1,
            1,
            "",
            None,
            "event-uid",
            "event-uuid",
            2,
            None,
            None,
        ),
    )
    conn.execute(
        INSERT_CALENDAR_ITEM_SQL,
        (
            21,
            "Weekly sync moved",
            None,
            "",
            802252800.0,
            802256400.0,
            0,
            1,
            1,
            "",
            None,
            "event-uid/RID=802249200",
            "event-uuid-rid",
            2,
            20,
            802249200.0,
        ),
    )
    conn.execute(
        "INSERT INTO Recurrence VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, 2, 1, 0, 804527999.0, "D=0TH", 20),
    )
    conn.commit()
    conn.close()

    snapshot = fetch_snapshot_from_store(
        db_path,
        start="2026-06-01T00:00:00Z",
        end="2026-06-05T00:00:00Z",
        calendar_names_or_ids=["Calendar"],
    )

    master = next(
        event
        for event in snapshot["events"]
        if event["event_id"] == "event-uid:2026-05-25T07:00:00Z"
    )
    assert master["excluded_dates"] == ["2026-06-04T07:00:00Z"]


def test_fetch_snapshot_from_store_ignores_out_of_range_occurrences(tmp_path):
    db_path = tmp_path / "Calendar.sqlitedb"
    conn = _create_store(db_path)
    conn.execute(
        "INSERT INTO Calendar VALUES (?, ?, ?, ?, ?, ?)",
        (1, "Calendar", "#a2845e", "cal-uuid", None, 1),
    )
    conn.execute(
        INSERT_CALENDAR_ITEM_SQL,
        (
            20,
            "Old event",
            None,
            "",
            757382400.0,
            757386000.0,
            0,
            1,
            1,
            "",
            None,
            "event-uid",
            "event-uuid",
            2,
            None,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO OccurrenceCache VALUES (?, ?, ?, ?)",
        (20, 1, 757382400.0, 757386000.0),
    )
    conn.commit()
    conn.close()

    snapshot = fetch_snapshot_from_store(
        db_path,
        start="2026-01-01T00:00:00Z",
        end="2026-01-02T00:00:00Z",
        calendar_names_or_ids=["Calendar"],
    )

    assert snapshot["events"] == []
