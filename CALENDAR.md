# Apple Calendar MCP - Domain Instructions

Calendar-specific architecture, tools, workflows, and caveats for this
repository. Read this file after `AGENTS.md` when working on the Apple Calendar
MCP server.

## Project Overview

Apple Calendar MCP is a read-only, JXA-only MCP server focused on
archive search across Apple Calendar events. It provides a small
assistant-friendly read surface, backed by a local SQLite + FTS5 index for
search across all accessible calendar history. The implementation should stay
separate from Apple Mail MCP as its own package and CLI while following the same
repo workflow and server patterns.

## Project Structure

Package layout:

```
packages/apple-calendar-mcp/src/apple_calendar_mcp/
├── __init__.py         # CLI entry point, exports main()
├── cli.py              # CLI commands (index, status, rebuild, serve)
├── server.py           # FastMCP server with 6 read-only MCP tools
├── config.py           # Environment variable and TOML configuration
├── builders.py         # Calendar query and script builders
├── executor.py         # run_jxa(), execute_with_core()
├── recurrence.py       # Built-in recurrence expansion for common RRULEs
├── index/              # FTS5 search index module
│   ├── __init__.py     # Exports IndexManager
│   ├── schema.py       # SQLite schema for events and occurrences
│   ├── manager.py      # IndexManager class
│   ├── sync.py         # JXA-backed index rebuild and refresh
│   └── search.py       # FTS5 search functions
└── jxa/
    ├── __init__.py     # Exports CALENDAR_CORE_JS
    └── calendar_core.js # Shared JXA utilities (CalendarCore object)
```

## MCP Tools (6 total)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `list_calendars()` | List accessible calendars | - |
| `get_events(...)` | List event occurrences in a date range | start, end, calendar_ids, limit, offset |
| `get_event(id, occurrence_start?)` | Full event or occurrence detail | event_id, occurrence_start |
| `search_events(query, ...)` | Archive search over indexed events | query, start, end, calendar_ids, fields, limit, offset |
| `get_agenda(...)` | Chronological agenda helper | start, days, calendar_ids |
| `calendar_index_status()` | Index health and coverage summary | - |

All tools are read-only. Do not add create, update, delete, RSVP, calendar
subscription, or UI-opening tools in v1.

## MCP Resources (1 total)

| URI | Purpose | MIME |
|-----|---------|------|
| `calendar-index://status` | Read-only JSON snapshot of Calendar index health: `event_count`, `occurrence_count`, `calendar_count`, `db_size_mb`, `coverage_start`, `coverage_end`, `unsupported_recurrence_count`, `failed_jobs_count`, and `last_sync`. Lets MCP clients assess index state without invoking a tool. | `application/json` |

### get_events() Filters

```python
get_events("2026-05-01", "2026-06-01")              # All calendars
get_events("2026-05-01", "2026-06-01", ["work"])    # Calendar subset
get_events("2026-05-01", "2026-06-01", limit=100)  # Larger page
get_agenda()                                        # Today
get_agenda(days=7)                                  # Next 7 days
```

### search_events() Scopes

```python
search_events("budget")                         # Search all indexed fields
search_events("budget", fields=["title"])       # Title only
search_events("alice", fields=["attendees"])    # Attendee names/emails
search_events("office", fields=["location"])    # Location only
search_events("retro", start="2024-01-01")      # Date-filtered archive search
search_events("planning", limit=20, offset=20)  # Page 2 of results
```

Search should include event title, location, notes, URL, attendee names/emails,
and calendar name by default. Notes are indexed and returned by default.

## Architecture

### JXA-Only Calendar Access

**Decision:** v1 uses Calendar.app JXA only, not EventKit/PyObjC.

**Reasoning:** This keeps Calendar MCP close to the existing Mail MCP runtime
model: `osascript -l JavaScript`, shared injected JS helpers, safe
`json.dumps()` serialization, and Python-side indexing/search.

**Caveat:** Calendar.app scripting exposes a recurrence string, not a complete
occurrence-expansion API. The Python recurrence layer must expand common
patterns and explicitly mark unsupported complex rules.

### Layer Separation

1. **cli.py** - CLI entry point, commands for indexing
2. **server.py** - 6 read-only MCP tools, uses builders and index
3. **builders.py** - Constructs JXA scripts from Python, type-safe
4. **executor.py** - Runs scripts via osascript, handles JSON parsing
5. **recurrence.py** - Expands common recurrence rules into occurrences
6. **index/** - FTS5 search index for archive search
7. **jxa/calendar_core.js** - Shared JS utilities injected into all scripts

### Data Flow (JXA Path)

```
MCP Tool → CalendarQueryBuilder method → executor.execute_with_core()
                                                 ↓
                                      CALENDAR_CORE_JS + script body
                                                 ↓
                                       osascript -l JavaScript
                                                 ↓
                                       JSON.parse(stdout)
```

### Data Flow (Index Sync)

```
CLI/server startup → IndexManager.sync_updates()
                            ↓
              JXA list calendars + raw events
                            ↓
              recurrence.expand_occurrences()
                            ↓
              UPSERT event records + occurrence rows
                            ↓
              FTS5 tables updated for archive search
```

### Hybrid Access Pattern

| Access Method | Use Case | Latency | When Used |
|---------------|----------|---------|-----------|
| **FTS5 (Cached)** | Archive text search | ~2-10ms target | `search_events()` |
| **SQLite (Cached)** | Date-range occurrence reads | ~1-5ms target | `get_events()`, `get_agenda()` |
| **JXA (Live)** | Calendar discovery and index refresh | ~100ms+ target | `list_calendars()`, `index`, `rebuild` |
| **Python Recurrence** | Recurring event expansion | depends on range | indexing and refresh |

### Recurrence Strategy

Recurring events should appear as expanded occurrences in search and listing
results. v1 supports common recurrence strings:

- `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`
- `INTERVAL`
- `COUNT`
- `UNTIL`
- weekly `BYDAY`
- Calendar exception dates (`excluded dates`)

Unsupported recurrence rules must be counted in status output and visible in
event detail metadata. Do not silently treat unsupported recurring events as
fully expanded.

### Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Builder** | `CalendarQueryBuilder` | Safe JXA script construction, prevents injection |
| **Singleton** | `IndexManager` | Single SQLite writer |
| **Facade** | `CalendarCore` JS | Clean API over verbose Calendar Apple Events |
| **Factory** | `create_connection()` | Consistent DB configuration |
| **State Reconciliation** | `sync_updates()` | Refresh event and occurrence cache |

## FTS5 Search Index

### Database Schema

```sql
-- Calendar metadata cache
CREATE TABLE calendars (
    calendar_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,
    writable INTEGER,
    description TEXT,
    indexed_at TEXT DEFAULT (datetime('now'))
);

-- Event series/master records from Calendar.app
CREATE TABLE events (
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

-- Expanded occurrences used by list/search/agenda tools
CREATE TABLE occurrences (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    calendar_id TEXT NOT NULL REFERENCES calendars(calendar_id),
    occurrence_start TEXT NOT NULL,
    occurrence_end TEXT NOT NULL,
    is_detached INTEGER DEFAULT 0,
    UNIQUE(event_id, occurrence_start)
);

CREATE INDEX idx_occurrences_range
    ON occurrences(occurrence_start, occurrence_end);
CREATE INDEX idx_occurrences_calendar
    ON occurrences(calendar_id, occurrence_start);

-- Attendee metadata, included in event detail and indexed text
CREATE TABLE attendees (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    display_name TEXT,
    email TEXT,
    participation_status TEXT
);
CREATE INDEX idx_attendees_event ON attendees(event_id);

-- Flattened search document per event/occurrence for FTS5
CREATE TABLE event_search (
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

CREATE VIRTUAL TABLE events_fts USING fts5(
    title, location, notes, url, attendees, calendar_name,
    content='event_search',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

-- Dead letter queue for JXA/index failures
CREATE TABLE failed_index_jobs (
    job_key TEXT PRIMARY KEY,
    calendar_id TEXT,
    event_id TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    first_seen TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now')),
    attempt_count INTEGER DEFAULT 1
);
```

Final implementation may normalize the FTS backing table differently, but it
must not rely on an FTS external-content table whose indexed columns are absent
from the backing table. Public behavior must preserve searchable title,
location, notes, URL, attendees, and calendar name.

### IndexManager API

```python
from apple_calendar_mcp.index import IndexManager

manager = IndexManager.get_instance()

# Build index from Calendar.app via JXA
manager.build_from_jxa(progress_callback=None)

# Refresh cached calendars, events, and occurrences
changes = manager.sync_updates()

# Search indexed event text
results = manager.search(query, start=None, end=None, calendar_ids=None)

# Get statistics and recurrence coverage
stats = manager.get_stats()

# Check staleness
if manager.is_stale():
    manager.sync_updates()
```

### Recurrence Functions

```python
from apple_calendar_mcp.recurrence import expand_occurrences

occurrences = expand_occurrences(
    event,
    coverage_start,
    coverage_end,
    max_occurrences=10000,
)
```

The recurrence layer must be deterministic, independently unit-tested, and
clear about unsupported recurrence rules.

### Sync Functions

```python
from apple_calendar_mcp.index.sync import (
    sync_from_snapshot,
    SyncResult,
)

snapshot = manager.fetch_snapshot()
result = sync_from_snapshot(
    conn,
    snapshot,
    coverage_start="1970-01-01T00:00:00Z",
    coverage_end="2027-01-01T00:00:00Z",
    max_occurrences_per_series=10000,
)
# result.added, result.updated, result.deleted, result.errors
```

## Adding New Query Tools

Prefer extending `get_events()` filters or `search_events()` fields before
adding new tools.

```python
# In server.py - adding a new search field
async def search_events(
    query: str,
    fields: list[Literal[
        "all", "title", "location", "notes", "attendees", "calendar"
    ]] | None = None,
    ...
):
    ...
```

For completely new read operations, use `execute_with_core_async()` and keep
JXA string inputs serialized with `json.dumps()`.

## CalendarCore Date Helpers

```javascript
// Get today at local midnight
CalendarCore.today()  // Date

// Parse ISO date or datetime strings
CalendarCore.parseDate("2026-05-30")  // Date

// Format for JSON
CalendarCore.formatDate(date)  // ISO string or null
```

## CLI Commands

```bash
apple-calendar-mcp              # Run MCP server (default)
apple-calendar-mcp serve        # Run MCP server explicitly
apple-calendar-mcp index        # Build search index from Calendar.app
apple-calendar-mcp status       # Show index statistics
apple-calendar-mcp rebuild      # Force rebuild index
apple-calendar-mcp search       # Search events (JSON output)
apple-calendar-mcp events       # List event occurrences (JSON output)
apple-calendar-mcp calendars    # List calendars (JSON output)
apple-calendar-mcp agenda       # Show agenda (JSON output)
```

## Calendar Smoke Checks

```bash
uv run --package apple-calendar-mcp --group dev pytest \
  packages/apple-calendar-mcp/tests
uv run --package apple-calendar-mcp --group dev apple-calendar-mcp --help
uv run --package apple-calendar-mcp --group dev python -c \
  "from apple_calendar_mcp import main; print(callable(main))"
```

## Critical: JXA Performance

**ALWAYS batch property fetching where Calendar.app allows it.** Avoid
per-event Apple Event IPC inside large loops.

```javascript
// WRONG - repeated IPC per event
for (let event of calendar.events()) {
    results.push({ title: event.summary() });
}

// RIGHT - collect references, then batch common property arrays in CalendarCore
const events = CalendarCore.eventsInRange(calendar, start, end);
const data = CalendarCore.batchFetchEvents(events, ["summary", "startDate"]);
```

If Calendar scripting does not support a Mail-style batch path for a property,
prefer bounded date ranges, clear timeouts, and cached index reads over live
wide scans.

## Configuration

Values should resolve in this precedence order (highest first):

1. CLI flag
2. Environment variable (`APPLE_CALENDAR_*`)
3. `~/.apple-calendar-mcp/config.toml`
4. Built-in default

| Variable | TOML key | Default | Description |
|----------|----------|---------|-------------|
| `APPLE_CALENDAR_INDEX_PATH` | `[index] path` | `~/.apple-calendar-mcp/index.db` | Index database location |
| `APPLE_CALENDAR_INDEX_STALENESS_HOURS` | `[index] staleness_hours` | `24` | Hours before refresh |
| `APPLE_CALENDAR_INDEX_PAST_YEARS` | `[index] past_years` | _unset_ | Optional archive backfill limit; unset means all available history |
| `APPLE_CALENDAR_INDEX_FUTURE_YEARS` | `[index] future_years` | `1` | Future expansion window for recurring events |
| `APPLE_CALENDAR_INDEX_MAX_OCCURRENCES_PER_SERIES` | `[index] max_occurrences_per_series` | `10000` | Safety cap for recurring event expansion |
| `APPLE_CALENDAR_DEFAULT_CALENDARS` | `[defaults] calendars` | _unset_ | Optional default calendar IDs/names for list and agenda tools |

## Benchmarks

Calendar benchmarks should be added after the first implementation stabilizes.
They should measure:

```bash
# Planned benchmark scenarios
apple-calendar-mcp calendars
apple-calendar-mcp events --start 2026-01-01 --end 2026-02-01
apple-calendar-mcp search budget
apple-calendar-mcp agenda --days 7
```

Key files should mirror the Mail benchmark structure if Calendar benchmarks are
added to this repo.

## Known Limitations

1. **macOS Only** - Requires Apple Calendar and `osascript`.
2. **Calendar Permission** - macOS grants Calendar read access through the
   system privacy prompt; the OS permission is not a read-only-only grant.
3. **JXA-Only Backend** - v1 does not use EventKit/PyObjC.
4. **Recurrence Coverage** - Common recurrence rules are expanded; complex
   unsupported recurrence strings must be reported clearly.
5. **Future Recurrences** - Recurring events are expanded through the configured
   future window, defaulting to one year.

## Security

### Planned Protections

| Threat | Mitigation | Location |
|--------|------------|----------|
| **SQL Injection** | Parameterized queries with `?` placeholders | search.py, sync.py |
| **JXA Injection** | `json.dumps()` serialization for all strings | builders.py, sync.py |
| **FTS5 Query Injection** | Special character escaping via parser helpers | search.py |
| **Data Exposure** | Index database created with 0o600 permissions | schema.py |
| **Runaway Recurrence** | Per-series occurrence cap and future window | recurrence.py |
| **Unbounded Live Scans** | Prefer indexed reads and bounded JXA ranges | server.py, builders.py |
| **Unsupported Recurrence Drift** | Explicit unsupported counts and metadata | recurrence.py, manager.py |
