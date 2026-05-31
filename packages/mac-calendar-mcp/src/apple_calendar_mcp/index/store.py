from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

APPLE_EPOCH_OFFSET = 978_307_200
DEFAULT_STORE_PATH = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "group.com.apple.calendar"
    / "Calendar.sqlitedb"
)


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _to_apple_seconds(value: str) -> float:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.timestamp() - APPLE_EPOCH_OFFSET


def _to_iso(value: float | int | None) -> str | None:
    if value is None:
        return None
    return (
        datetime.fromtimestamp(float(value) + APPLE_EPOCH_OFFSET, UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _status_name(value: int | None) -> str:
    return {
        1: "none",
        2: "accepted",
        3: "declined",
        4: "tentative",
    }.get(value or 0, "")


def _calendar_filter(
    calendar_names_or_ids: list[str] | None,
) -> tuple[str, list]:
    if not calendar_names_or_ids:
        return "", []
    placeholders = ",".join("?" for _ in calendar_names_or_ids)
    return (
        f" AND (c.title IN ({placeholders}) OR c.UUID IN ({placeholders}))",
        [*calendar_names_or_ids, *calendar_names_or_ids],
    )


def _fetch_attendees(conn: sqlite3.Connection, event_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            i.display_name AS display_name,
            COALESCE(p.email, i.address) AS email,
            p.status AS status
        FROM Participant p
        LEFT JOIN Identity i ON i.rowid = p.identity_id
        WHERE p.owner_id = ?
        ORDER BY p.ROWID
        """,
        (event_id,),
    ).fetchall()
    return [
        {
            "display_name": row["display_name"],
            "email": row["email"],
            "participation_status": _status_name(row["status"]),
        }
        for row in rows
    ]


def _fetch_excluded_dates(conn: sqlite3.Connection, event_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT orig_date
        FROM CalendarItem
        WHERE orig_item_id = ?
          AND orig_date IS NOT NULL
        ORDER BY orig_date
        """,
        (event_id,),
    ).fetchall()
    return [value for row in rows if (value := _to_iso(row["orig_date"]))]


def _recurrence_to_rrule(row: sqlite3.Row) -> str:
    frequency = {
        1: "DAILY",
        2: "WEEKLY",
        3: "MONTHLY",
        4: "YEARLY",
    }.get(row["recurrence_frequency"])
    if not frequency:
        return ""

    parts = [f"FREQ={frequency}"]
    interval = row["recurrence_interval"]
    if interval and interval > 1:
        parts.append(f"INTERVAL={interval}")
    count = row["recurrence_count"]
    if count:
        parts.append(f"COUNT={count}")
    until = _to_iso(row["recurrence_end_date"])
    if until:
        parts.append(f"UNTIL={until}")

    byday = _specifier_to_byday(row["recurrence_specifier"] or "")
    if byday:
        parts.append(f"BYDAY={byday}")

    return ";".join(parts)


def _specifier_to_byday(specifier: str) -> str:
    if not specifier.startswith("D="):
        return ""
    days = []
    for raw_day in specifier.removeprefix("D=").split(","):
        day = raw_day.removeprefix("0")
        if day:
            days.append(day)
    return ",".join(days)


def fetch_snapshot_from_store(
    path: Path = DEFAULT_STORE_PATH,
    *,
    start: str,
    end: str,
    calendar_names_or_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Read an indexed Calendar snapshot from Calendar's local SQLite store."""
    conn = _connect(path)
    try:
        start_seconds = _to_apple_seconds(start)
        end_seconds = _to_apple_seconds(end)
        where_sql, where_params = _calendar_filter(calendar_names_or_ids)

        calendars = [
            {
                "id": row["title"],
                "name": row["title"],
                "color": row["color"],
                "writable": True,
                "description": row["notes"],
            }
            for row in conn.execute(
                f"""
                SELECT c.title, c.color, c.UUID, c.notes
                FROM Calendar c
                WHERE 1=1 {where_sql}
                ORDER BY c.display_order, c.ROWID
                """,
                where_params,
            )
        ]

        rows = conn.execute(
            f"""
            SELECT
                ci.ROWID AS item_rowid,
                ci.summary,
                ci.description,
                ci.start_date,
                ci.end_date,
                ci.all_day,
                ci.status,
                ci.url,
                ci.last_modified,
                ci.unique_identifier,
                ci.UUID AS item_uuid,
                c.title AS calendar_title,
                l.title AS location_title,
                r.frequency AS recurrence_frequency,
                r.interval AS recurrence_interval,
                r.count AS recurrence_count,
                r.end_date AS recurrence_end_date,
                r.specifier AS recurrence_specifier
            FROM CalendarItem ci
            JOIN Calendar c ON c.ROWID = ci.calendar_id
            LEFT JOIN Location l ON l.ROWID = ci.location_id
            LEFT JOIN Recurrence r ON r.owner_id = ci.ROWID
            WHERE ci.start_date <= ?
              AND (
                ci.end_date >= ?
                OR (
                  r.ROWID IS NOT NULL
                  AND (
                    r.end_date IS NULL
                    OR r.end_date >= ?
                  )
                )
              )
              {where_sql}
            ORDER BY ci.start_date, ci.ROWID
            """,
            [end_seconds, start_seconds, start_seconds, *where_params],
        ).fetchall()

        events: list[dict[str, Any]] = []
        for row in rows:
            occurrence_start = _to_iso(row["start_date"]) or ""
            occurrence_end = _to_iso(row["end_date"]) or ""
            base_id = (
                row["unique_identifier"]
                or row["item_uuid"]
                or row["item_rowid"]
            )
            events.append(
                {
                    "event_id": f"{base_id}:{occurrence_start}",
                    "calendar_id": row["calendar_title"],
                    "calendar_name": row["calendar_title"],
                    "title": row["summary"] or "",
                    "location": row["location_title"] or "",
                    "notes": row["description"] or "",
                    "url": row["url"] or "",
                    "status": str(row["status"] or ""),
                    "all_day": bool(row["all_day"]),
                    "start_date": occurrence_start,
                    "end_date": occurrence_end,
                    "modified_at": _to_iso(row["last_modified"]),
                    "recurrence": _recurrence_to_rrule(row),
                    "excluded_dates": _fetch_excluded_dates(
                        conn, row["item_rowid"]
                    ),
                    "attendees": _fetch_attendees(conn, row["item_rowid"]),
                }
            )

        return {"calendars": calendars, "events": events, "failed_jobs": []}
    finally:
        conn.close()
