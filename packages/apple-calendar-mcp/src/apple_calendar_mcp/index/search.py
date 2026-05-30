from __future__ import annotations

from sqlite3 import Connection


def _escape_fts(query: str) -> str:
    return " ".join(part.replace('"', '""') for part in query.split())


def _field_query(query: str, fields: list[str] | None) -> str:
    escaped = _escape_fts(query)
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
    params: list[object] = [_field_query(query, fields)]
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

    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
