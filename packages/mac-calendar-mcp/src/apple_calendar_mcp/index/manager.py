from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from sqlite3 import Connection
from typing import Any

from apple_calendar_mcp.config import (
    get_default_calendars,
    get_index_future_years,
    get_index_max_occurrences_per_series,
    get_index_past_years,
    get_index_path,
)
from apple_calendar_mcp.executor import JXAError, execute_with_core

from .schema import SCHEMA_VERSION, create_connection, get_schema_sql
from .search import search_events
from .sync import sync_from_snapshot

CALENDAR_EVENT_FETCH_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class IndexStats:
    calendar_count: int
    event_count: int
    occurrence_count: int
    unsupported_recurrence_count: int
    failed_jobs_count: int
    db_size_mb: float
    coverage_start: str | None = None
    coverage_end: str | None = None
    last_sync: datetime | None = None


class IndexManager:
    _instance: IndexManager | None = None

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_index_path()
        self._conn: Connection | None = None

    @classmethod
    def get_instance(cls) -> IndexManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _connection(self) -> Connection:
        if self._conn is None:
            self._conn = create_connection(self.db_path)
            self._conn.executescript(get_schema_sql())
            self._conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            self._conn.commit()
        return self._conn

    def has_index(self) -> bool:
        return self.db_path.exists()

    def fetch_snapshot(self) -> dict[str, Any]:
        future_years = get_index_future_years()
        past_years = get_index_past_years()
        start_expr = (
            "new Date("
            f"now.getFullYear() - {past_years}, "
            "now.getMonth(), now.getDate()"
            ")"
        )
        window_script = f"""
const now = new Date();
const start = {start_expr}.toISOString();
const end = new Date(
  now.getFullYear() + {future_years}, now.getMonth(), now.getDate()
).toISOString();
"""
        calendars = execute_with_core(
            "JSON.stringify(CalendarCore.listCalendars());"
        )
        configured_calendars = get_default_calendars()
        if configured_calendars is not None:
            selected_ids = set(configured_calendars)
        else:
            selected_ids = {
                calendar["id"] for calendar in calendars if "id" in calendar
            }

        events: list[dict[str, Any]] = []
        failed_jobs: list[dict[str, str]] = []
        for calendar_id in selected_ids:
            script = (
                window_script
                + "JSON.stringify(CalendarCore.eventsInRange("
                + "start, end, "
                + json.dumps([calendar_id])
                + "));"
            )
            try:
                events.extend(
                    execute_with_core(
                        script, timeout=CALENDAR_EVENT_FETCH_TIMEOUT_SECONDS
                    )
                )
            except JXAError:
                failed_jobs.append(
                    {
                        "job_key": f"calendar:{calendar_id}",
                        "calendar_id": calendar_id,
                        "error_type": "calendar_event_fetch_failed",
                        "error_message": (
                            "Calendar event fetch timed out or failed"
                        ),
                    }
                )
                continue

        return {
            "calendars": calendars,
            "events": events,
            "failed_jobs": failed_jobs,
        }

    def build_from_jxa(self, progress_callback=None) -> int:
        snapshot = self.fetch_snapshot()
        now = datetime.now(UTC)
        past_years = get_index_past_years()
        if past_years is None:
            coverage_start = "1970-01-01T00:00:00Z"
        else:
            coverage_start = (
                (now - timedelta(days=365 * past_years))
                .isoformat()
                .replace("+00:00", "Z")
            )
        coverage_end = (
            (now + timedelta(days=365 * get_index_future_years()))
            .isoformat()
            .replace("+00:00", "Z")
        )
        result = sync_from_snapshot(
            self._connection(),
            snapshot,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            max_occurrences_per_series=(get_index_max_occurrences_per_series()),
        )
        if progress_callback is not None:
            progress_callback(result.added, result.errors)
        return result.added

    def sync_updates(self) -> int:
        return self.build_from_jxa()

    def search(self, query: str, **kwargs) -> list[dict]:
        return search_events(self._connection(), query, **kwargs)

    def events(
        self,
        *,
        start: str,
        end: str,
        calendar_ids: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        sql = """
        SELECT
            e.event_id,
            e.title,
            e.location,
            e.notes,
            e.url,
            e.status,
            e.all_day,
            o.occurrence_start,
            o.occurrence_end,
            c.calendar_id,
            c.name AS calendar_name
        FROM occurrences o
        JOIN events e ON e.event_id = o.event_id
        JOIN calendars c ON c.calendar_id = e.calendar_id
        WHERE o.occurrence_end >= ?
          AND o.occurrence_start <= ?
        """
        params: list[object] = [start, end]
        if calendar_ids:
            placeholders = ",".join("?" for _ in calendar_ids)
            sql += f" AND c.calendar_id IN ({placeholders})"
            params.extend(calendar_ids)
        sql += " ORDER BY o.occurrence_start LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return [dict(row) for row in self._connection().execute(sql, params)]

    def get_event(
        self,
        event_id: str,
        *,
        occurrence_start: str | None = None,
    ) -> dict:
        sql = """
        SELECT
            e.*,
            c.name AS calendar_name,
            o.occurrence_start,
            o.occurrence_end
        FROM events e
        JOIN calendars c ON c.calendar_id = e.calendar_id
        LEFT JOIN occurrences o ON o.event_id = e.event_id
        WHERE e.event_id = ?
        """
        params: list[object] = [event_id]
        if occurrence_start is not None:
            sql += " AND o.occurrence_start = ?"
            params.append(occurrence_start)
        sql += " ORDER BY o.occurrence_start LIMIT 1"
        row = self._connection().execute(sql, params).fetchone()
        if row is None:
            raise ValueError(f"Calendar event {event_id} not found.")
        result = dict(row)
        attendee_rows = (
            self._connection()
            .execute(
                """
            SELECT display_name, email, participation_status
            FROM attendees
            WHERE event_id = ?
            ORDER BY display_name, email
            """,
                (event_id,),
            )
            .fetchall()
        )
        result["attendees"] = [dict(attendee) for attendee in attendee_rows]
        return result

    def get_agenda(
        self,
        *,
        start: str | None = None,
        days: int = 1,
        calendar_ids: list[str] | None = None,
    ) -> list[dict]:
        if start:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        else:
            start_dt = datetime.now(UTC).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        end_dt = start_dt + timedelta(days=days)
        return self.events(
            start=start_dt.isoformat().replace("+00:00", "Z"),
            end=end_dt.isoformat().replace("+00:00", "Z"),
            calendar_ids=calendar_ids,
            limit=500,
            offset=0,
        )

    def is_stale(self) -> bool:
        return False

    def get_stats(self) -> IndexStats:
        conn = self._connection()
        coverage = conn.execute(
            """
            SELECT
                MIN(occurrence_start) AS coverage_start,
                MAX(occurrence_end) AS coverage_end
            FROM occurrences
            """
        ).fetchone()
        db_size_mb = (
            self.db_path.stat().st_size / 1024 / 1024
            if self.db_path.exists()
            else 0.0
        )
        return IndexStats(
            calendar_count=conn.execute(
                "SELECT COUNT(*) FROM calendars"
            ).fetchone()[0],
            event_count=conn.execute("SELECT COUNT(*) FROM events").fetchone()[
                0
            ],
            occurrence_count=conn.execute(
                "SELECT COUNT(*) FROM occurrences"
            ).fetchone()[0],
            unsupported_recurrence_count=conn.execute(
                "SELECT COUNT(*) FROM events WHERE unsupported_recurrence = 1"
            ).fetchone()[0],
            failed_jobs_count=conn.execute(
                "SELECT COUNT(*) FROM failed_index_jobs"
            ).fetchone()[0],
            db_size_mb=db_size_mb,
            coverage_start=coverage["coverage_start"],
            coverage_end=coverage["coverage_end"],
        )
