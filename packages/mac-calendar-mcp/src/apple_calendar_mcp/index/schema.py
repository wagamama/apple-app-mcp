from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

DEFAULT_PRAGMAS = {
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "busy_timeout": 5000,
    "foreign_keys": "ON",
}

INSERT_CALENDAR_SQL = """INSERT OR REPLACE INTO calendars
    (calendar_id, name, color, writable, description)
    VALUES (?, ?, ?, ?, ?)"""

INSERT_EVENT_SQL = """INSERT OR REPLACE INTO events
    (event_id, calendar_id, title, location, notes, url, status, all_day,
     start_date, end_date, modified_at, recurrence, unsupported_recurrence)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

INSERT_OCCURRENCE_SQL = """INSERT OR REPLACE INTO occurrences
    (event_id, calendar_id, occurrence_start, occurrence_end, is_detached)
    VALUES (?, ?, ?, ?, ?)"""

INSERT_ATTENDEE_SQL = """INSERT INTO attendees
    (event_id, display_name, email, participation_status)
    VALUES (?, ?, ?, ?)"""

INSERT_SEARCH_SQL = """INSERT INTO event_search
    (event_id, occurrence_start, title, location, notes, url, attendees,
     calendar_name)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""


def create_connection(db_path: Path) -> sqlite3.Connection:
    """Create a Calendar index SQLite connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for pragma, value in DEFAULT_PRAGMAS.items():
        conn.execute(f"PRAGMA {pragma}={value}")
    try:
        os.chmod(db_path, 0o600)
    except FileNotFoundError:
        pass
    return conn


def get_schema_sql() -> str:
    """Return the complete Calendar index schema SQL."""
    return """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS calendars (
    calendar_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,
    writable INTEGER,
    description TEXT,
    indexed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    calendar_id TEXT NOT NULL REFERENCES calendars(calendar_id),
    title TEXT,
    location TEXT,
    notes TEXT,
    url TEXT,
    status TEXT,
    all_day INTEGER DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    modified_at TEXT,
    recurrence TEXT,
    unsupported_recurrence INTEGER DEFAULT 0,
    indexed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS occurrences (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    calendar_id TEXT NOT NULL REFERENCES calendars(calendar_id),
    occurrence_start TEXT NOT NULL,
    occurrence_end TEXT NOT NULL,
    is_detached INTEGER DEFAULT 0,
    UNIQUE(event_id, occurrence_start)
);

CREATE INDEX IF NOT EXISTS idx_occurrences_range
    ON occurrences(occurrence_start, occurrence_end);
CREATE INDEX IF NOT EXISTS idx_occurrences_calendar
    ON occurrences(calendar_id, occurrence_start);

CREATE TABLE IF NOT EXISTS attendees (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    display_name TEXT,
    email TEXT,
    participation_status TEXT
);
CREATE INDEX IF NOT EXISTS idx_attendees_event ON attendees(event_id);

CREATE TABLE IF NOT EXISTS event_search (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    occurrence_start TEXT,
    title TEXT,
    location TEXT,
    notes TEXT,
    url TEXT,
    attendees TEXT,
    calendar_name TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
    title, location, notes, url, attendees, calendar_name,
    content='event_search',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS event_search_ai
AFTER INSERT ON event_search BEGIN
    INSERT INTO events_fts(rowid, title, location, notes, url, attendees,
                           calendar_name)
    VALUES (new.rowid, new.title, new.location, new.notes, new.url,
            new.attendees, new.calendar_name);
END;

CREATE TRIGGER IF NOT EXISTS event_search_ad
AFTER DELETE ON event_search BEGIN
    INSERT INTO events_fts(events_fts, rowid, title, location, notes, url,
                           attendees, calendar_name)
    VALUES('delete', old.rowid, old.title, old.location, old.notes, old.url,
           old.attendees, old.calendar_name);
END;

CREATE TRIGGER IF NOT EXISTS event_search_au
AFTER UPDATE ON event_search BEGIN
    INSERT INTO events_fts(events_fts, rowid, title, location, notes, url,
                           attendees, calendar_name)
    VALUES('delete', old.rowid, old.title, old.location, old.notes, old.url,
           old.attendees, old.calendar_name);
    INSERT INTO events_fts(rowid, title, location, notes, url, attendees,
                           calendar_name)
    VALUES (new.rowid, new.title, new.location, new.notes, new.url,
            new.attendees, new.calendar_name);
END;

CREATE TABLE IF NOT EXISTS failed_index_jobs (
    job_key TEXT PRIMARY KEY,
    calendar_id TEXT,
    event_id TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    first_seen TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now')),
    attempt_count INTEGER DEFAULT 1
);
"""
