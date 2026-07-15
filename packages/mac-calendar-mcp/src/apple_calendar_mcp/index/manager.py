from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from sqlite3 import Connection
from sqlite3 import Error as SQLiteError
from threading import RLock
from typing import Any

from apple_calendar_mcp.config import (
    get_index_calendars,
    get_index_future_years,
    get_index_max_occurrences_per_series,
    get_index_past_years,
    get_index_path,
    get_index_source,
    get_index_staleness_hours,
)
from apple_calendar_mcp.executor import JXAError, execute_with_core

from .eventkit import fetch_snapshot_from_eventkit
from .schema import SCHEMA_VERSION, create_connection, get_schema_sql
from .search import search_events
from .store import DEFAULT_STORE_PATH, fetch_snapshot_from_store
from .sync import record_failed_jobs, sync_from_snapshot

CALENDAR_EVENT_FETCH_TIMEOUT_SECONDS = 15
logger = logging.getLogger(__name__)


class CalendarIndexRefreshError(RuntimeError):
    """Raised when a failed source snapshot cannot safely replace the index."""


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
        self._lock = RLock()
        self.last_build_source: str | None = None
        self.last_build_calendar_count = 0
        self.last_build_event_count = 0

    @classmethod
    def get_instance(cls) -> IndexManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _connection(self) -> Connection:
        with self._lock:
            if self._conn is None:
                self._conn = create_connection(self.db_path)
                self._conn.executescript(get_schema_sql())
                self._conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version) "
                    "VALUES (?)",
                    (SCHEMA_VERSION,),
                )
                self._conn.commit()
            return self._conn

    def has_index(self) -> bool:
        return self.db_path.exists()

    def fetch_snapshot(self) -> dict[str, Any]:
        future_years = get_index_future_years()
        past_years = get_index_past_years()
        now = datetime.now(UTC)
        start = (
            (now - timedelta(days=365 * past_years))
            .isoformat()
            .replace("+00:00", "Z")
        )
        end = (
            (now + timedelta(days=365 * future_years))
            .isoformat()
            .replace("+00:00", "Z")
        )
        configured_calendars = get_index_calendars()
        source = get_index_source()
        if source in {"auto", "store"} and DEFAULT_STORE_PATH.exists():
            try:
                store_snapshot = fetch_snapshot_from_store(
                    DEFAULT_STORE_PATH,
                    start=start,
                    end=end,
                    calendar_names_or_ids=configured_calendars,
                )
                if store_snapshot.get("events"):
                    store_snapshot["source"] = "calendar-store"
                    return store_snapshot
                if source == "store":
                    return _failed_source_snapshot(
                        source="calendar-store",
                        error_type="empty_calendar_snapshot",
                        message=(
                            "Local Calendar store returned no events and "
                            "the empty snapshot was not independently confirmed"
                        ),
                    )
                logger.warning(
                    "Local Calendar store returned no events; confirming "
                    "the empty snapshot with EventKit"
                )
            except (OSError, SQLiteError) as exc:
                logger.warning(
                    "Falling back to EventKit after local store read "
                    "failed for %s: %s: %s",
                    DEFAULT_STORE_PATH,
                    type(exc).__name__,
                    exc,
                )
                if source == "store":
                    return _failed_source_snapshot(
                        source="calendar-store",
                        error_type="store_fetch_failed",
                        message=(
                            "Local Calendar store snapshot failed: "
                            f"{type(exc).__name__}: {exc}"
                        ),
                    )
        elif source == "store":
            return _failed_source_snapshot(
                source="calendar-store",
                error_type="store_fetch_failed",
                message=f"Local Calendar store not found: {DEFAULT_STORE_PATH}",
            )

        if source in {"auto", "eventkit"}:
            try:
                return fetch_snapshot_from_eventkit(
                    start=start,
                    end=end,
                    calendar_names_or_ids=configured_calendars,
                )
            except JXAError as exc:
                if source == "eventkit":
                    return _failed_source_snapshot(
                        source="eventkit",
                        error_type="eventkit_fetch_failed",
                        message=f"EventKit snapshot failed: {exc}",
                    )
                logger.warning(
                    "Falling back to Calendar JXA after EventKit failed: %s",
                    exc,
                )

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
        try:
            calendars = execute_with_core(
                "JSON.stringify(CalendarCore.listCalendars());"
            )
        except JXAError as exc:
            return _failed_source_snapshot(
                source="calendar-jxa",
                error_type="calendar_discovery_failed",
                message=f"Calendar discovery failed: {exc}",
            )
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
            except JXAError as exc:
                calendar_name = _calendar_name_for_id(
                    calendars,
                    calendar_id,
                )
                failed_jobs.append(
                    {
                        "job_key": f"calendar:{calendar_id}",
                        "calendar_id": calendar_id,
                        "error_type": "calendar_event_fetch_failed",
                        "error_message": _format_calendar_fetch_error(
                            calendar_id,
                            calendar_name,
                            exc,
                        ),
                    }
                )
                continue

        return {
            "source": "calendar-jxa",
            "calendars": calendars,
            "events": events,
            "failed_jobs": failed_jobs,
        }

    def build_from_jxa(self, progress_callback=None) -> int:
        snapshot = self.fetch_snapshot()
        self.last_build_source = snapshot.get("source", "unknown")
        self.last_build_calendar_count = len(snapshot.get("calendars", []))
        self.last_build_event_count = len(snapshot.get("events", []))
        failed_jobs = list(snapshot.get("failed_jobs", []))
        if (
            self.last_build_source == "calendar-jxa"
            and not self.last_build_event_count
            and not failed_jobs
        ):
            failed_jobs.append(
                {
                    "job_key": "source:calendar-jxa:empty",
                    "calendar_id": None,
                    "error_type": "empty_calendar_snapshot",
                    "error_message": (
                        "Legacy Calendar JXA returned an unconfirmed "
                        "empty snapshot"
                    ),
                }
            )
        if failed_jobs:
            with self._lock:
                record_failed_jobs(self._connection(), failed_jobs)
            details = "; ".join(
                job.get("error_message", "unknown source failure")
                for job in failed_jobs
            )
            raise CalendarIndexRefreshError(
                "Calendar index refresh failed; active index preserved: "
                f"{details}"
            )
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
        with self._lock:
            result = sync_from_snapshot(
                self._connection(),
                snapshot,
                coverage_start=coverage_start,
                coverage_end=coverage_end,
                max_occurrences_per_series=(
                    get_index_max_occurrences_per_series()
                ),
            )
        if progress_callback is not None:
            progress_callback(result.added, result.errors)
        return result.added

    def sync_updates(self) -> int:
        return self.build_from_jxa()

    def search(self, query: str, **kwargs) -> list[dict]:
        with self._lock:
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
        with self._lock:
            rows = self._connection().execute(sql, params).fetchall()
        return [dict(row) for row in rows]

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
        with self._lock:
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
        stats = self.get_stats()
        if stats.last_sync is None:
            return True
        age = datetime.now(UTC) - stats.last_sync
        return age.total_seconds() / 3600 > get_index_staleness_hours()

    def get_stats(self) -> IndexStats:
        with self._lock:
            return self._get_stats_unlocked()

    def _get_stats_unlocked(self) -> IndexStats:
        conn = self._connection()
        coverage = conn.execute(
            """
            SELECT
                MIN(occurrence_start) AS coverage_start,
                MAX(occurrence_end) AS coverage_end
            FROM occurrences
            """
        ).fetchone()
        last_sync_row = conn.execute(
            """
            SELECT MAX(indexed_at) AS last_sync
            FROM (
                SELECT indexed_at FROM calendars
                UNION ALL
                SELECT indexed_at FROM events
            )
            """
        ).fetchone()
        last_sync = _parse_sqlite_timestamp(last_sync_row["last_sync"])
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
            last_sync=last_sync,
        )


def _parse_sqlite_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _failed_source_snapshot(
    *,
    source: str,
    error_type: str,
    message: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "calendars": [],
        "events": [],
        "failed_jobs": [
            {
                "job_key": f"source:{source}",
                "calendar_id": None,
                "error_type": error_type,
                "error_message": message,
            }
        ],
    }


def _calendar_name_for_id(
    calendars: list[dict[str, Any]],
    calendar_id: str,
) -> str | None:
    for calendar in calendars:
        if calendar.get("id") == calendar_id:
            name = calendar.get("name")
            return name if isinstance(name, str) else None
    for calendar in calendars:
        if calendar.get("name") == calendar_id:
            name = calendar.get("name")
            return name if isinstance(name, str) else None
    return None


def _format_calendar_fetch_error(
    calendar_id: str,
    calendar_name: str | None,
    exc: JXAError,
) -> str:
    label = f"calendar_id={calendar_id}"
    if calendar_name:
        label += f" calendar_name={calendar_name}"

    message = f"Calendar event fetch failed ({label}): {exc}"
    if exc.stderr:
        message += f"; stderr: {exc.stderr}"
    return message
