from __future__ import annotations

import sqlite3
from sqlite3 import Connection

_FTS5_OPERATORS = {"OR", "AND", "NOT"}
_SPECIAL_CHARS = set("'\"-():^")


def _quote_fts_token(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'


def _sanitize_token(token: str) -> str:
    if token in _FTS5_OPERATORS:
        return token
    if token == "*":
        return ""

    has_wildcard = token.endswith("*") and len(token) > 1
    core = token[:-1] if has_wildcard else token
    if not core:
        return ""

    if any(char in _SPECIAL_CHARS for char in core):
        value = _quote_fts_token(core)
        return value + "*" if has_wildcard else value
    return token


def sanitize_fts_query(query: str) -> str:
    """Return an FTS5 query that treats malformed syntax as text."""
    return " ".join(
        token
        for token in (_sanitize_token(part) for part in query.split())
        if token
    )


def _field_query(query: str, fields: list[str] | None) -> str:
    escaped = sanitize_fts_query(query)
    if not fields or "all" in fields:
        return escaped
    allowed = {
        "title": "title",
        "location": "location",
        "notes": "notes",
        "attendees": "attendees",
        "calendar": "calendar_name",
    }
    columns = [allowed[field] for field in fields if field in allowed]
    if not columns:
        return escaped
    return " OR ".join(f"{column}:({escaped})" for column in columns)


def search_events(
    conn: Connection,
    query: str,
    *,
    start: str | None = None,
    end: str | None = None,
    calendar_ids: list[str] | None = None,
    fields: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    _is_retry: bool = False,
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
        c.name AS calendar_name,
        bm25(events_fts) AS score
    FROM events_fts
    JOIN event_search s ON s.rowid = events_fts.rowid
    JOIN events e ON e.event_id = s.event_id
    JOIN occurrences o
      ON o.event_id = s.event_id
     AND o.occurrence_start = s.occurrence_start
    JOIN calendars c ON c.calendar_id = e.calendar_id
    WHERE events_fts MATCH ?
    """
    params: list[object] = [query if _is_retry else _field_query(query, fields)]
    if start:
        sql += " AND o.occurrence_end >= ?"
        params.append(start)
    if end:
        sql += " AND o.occurrence_start <= ?"
        params.append(end)
    if calendar_ids:
        placeholders = ",".join("?" for _ in calendar_ids)
        sql += f" AND c.calendar_id IN ({placeholders})"
        params.extend(calendar_ids)
    sql += " ORDER BY score, o.occurrence_start LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        if "fts5: syntax error" in str(e).lower() and not _is_retry:
            return search_events(
                conn,
                " ".join(_quote_fts_token(part) for part in query.split()),
                start=start,
                end=end,
                calendar_ids=calendar_ids,
                fields=None,
                limit=limit,
                offset=offset,
                _is_retry=True,
            )
        raise
    return [dict(row) for row in rows]
