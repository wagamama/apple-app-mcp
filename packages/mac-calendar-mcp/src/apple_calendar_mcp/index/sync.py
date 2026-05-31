from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Connection

from apple_calendar_mcp.recurrence import expand_occurrences

from .schema import (
    INSERT_ATTENDEE_SQL,
    INSERT_CALENDAR_SQL,
    INSERT_EVENT_SQL,
    INSERT_OCCURRENCE_SQL,
    INSERT_SEARCH_SQL,
)

INSERT_FAILED_JOB_SQL = """
INSERT OR REPLACE INTO failed_index_jobs
    (job_key, calendar_id, event_id, error_type, error_message, last_seen,
     attempt_count)
VALUES
    (?, ?, ?, ?, ?, datetime('now'),
     COALESCE((SELECT attempt_count + 1 FROM failed_index_jobs
               WHERE job_key = ?), 1))
"""


@dataclass(frozen=True)
class SyncResult:
    added: int = 0
    updated: int = 0
    deleted: int = 0
    errors: int = 0


def _attendees_text(attendees: list[dict]) -> str:
    parts: list[str] = []
    for attendee in attendees:
        parts.append(attendee.get("display_name") or "")
        parts.append(attendee.get("email") or "")
    return " ".join(part for part in parts if part)


def sync_from_snapshot(
    conn: Connection,
    snapshot: dict,
    *,
    coverage_start: str,
    coverage_end: str,
    max_occurrences_per_series: int,
) -> SyncResult:
    conn.execute("DELETE FROM event_search")
    conn.execute("DELETE FROM attendees")
    conn.execute("DELETE FROM occurrences")
    conn.execute("DELETE FROM events")
    conn.execute("DELETE FROM calendars")
    conn.execute("DELETE FROM failed_index_jobs")

    calendars = snapshot.get("calendars", [])
    for calendar in calendars:
        conn.execute(
            INSERT_CALENDAR_SQL,
            (
                calendar["id"],
                calendar["name"],
                calendar.get("color"),
                1 if calendar.get("writable") else 0,
                calendar.get("description"),
            ),
        )

    added = 0
    errors = 0
    for event in snapshot.get("events", []):
        expansion = expand_occurrences(
            event,
            coverage_start,
            coverage_end,
            max_occurrences=max_occurrences_per_series,
        )
        unsupported = 1 if expansion.unsupported else 0
        conn.execute(
            INSERT_EVENT_SQL,
            (
                event["event_id"],
                event["calendar_id"],
                event.get("title", ""),
                event.get("location", ""),
                event.get("notes", ""),
                event.get("url", ""),
                event.get("status", ""),
                1 if event.get("all_day") else 0,
                event.get("start_date"),
                event.get("end_date"),
                event.get("modified_at"),
                event.get("recurrence", ""),
                unsupported,
            ),
        )
        for attendee in event.get("attendees", []):
            conn.execute(
                INSERT_ATTENDEE_SQL,
                (
                    event["event_id"],
                    attendee.get("display_name"),
                    attendee.get("email"),
                    attendee.get("participation_status"),
                ),
            )
        attendee_text = _attendees_text(event.get("attendees", []))
        for occurrence in expansion.occurrences:
            conn.execute(
                INSERT_OCCURRENCE_SQL,
                (
                    event["event_id"],
                    event["calendar_id"],
                    occurrence.start,
                    occurrence.end,
                    0,
                ),
            )
            conn.execute(
                INSERT_SEARCH_SQL,
                (
                    event["event_id"],
                    occurrence.start,
                    event.get("title", ""),
                    event.get("location", ""),
                    event.get("notes", ""),
                    event.get("url", ""),
                    attendee_text,
                    event.get("calendar_name", ""),
                ),
            )
            added += 1
        if expansion.unsupported:
            errors += 1
    for job in snapshot.get("failed_jobs", []):
        conn.execute(
            INSERT_FAILED_JOB_SQL,
            (
                job["job_key"],
                job.get("calendar_id"),
                job.get("event_id"),
                job["error_type"],
                job["error_message"],
                job["job_key"],
            ),
        )
        errors += 1
    conn.commit()
    return SyncResult(added=added, errors=errors)
