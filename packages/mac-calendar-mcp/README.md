# Mac Calendar MCP

<!-- mcp-name: io.github.wagamama/mac-calendar-mcp -->

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Read-only Mac Calendar MCP server with indexed archive search. It exposes
Apple Calendar data to MCP clients through a small read surface for listing
calendars, browsing event ranges, reading event details, searching archived
events, and building agendas.

This package is developed in the
[`apple-app-mcp`](https://github.com/wagamama/apple-app-mcp) workspace alongside
Mac Mail MCP.

## Quick Start

```bash
pipx install mac-calendar-mcp
```

Add to your MCP client:

```json
{
  "mcpServers": {
    "calendar": {
      "command": "mac-calendar-mcp",
      "args": ["--watch", "serve"]
    }
  }
}
```

### Build the Search Index (Recommended)

```bash
# One-time setup: approve Full Calendar Access for the helper app
mac-calendar-mcp authorize

mac-calendar-mcp index
```

The index enables fast archive search and date-range reads from a local SQLite
and FTS5 database.

Rebuilds use Calendar's local database when it is readable, then fall back to
Apple's supported EventKit API. Calendar.app scripting is retained only as a
legacy final fallback. A failed or suspiciously empty refresh never replaces a
previously healthy index.

The authorization command installs a small signed helper app under
`$HOME/Applications`. Its stable macOS privacy identity lets the EventKit
fallback work consistently from terminals, MCP hosts, and scheduled launchd
jobs. Calendar inputs are passed as app arguments rather than interpolated into
executable scripts. Each rebuild verifies the helper's code signature,
metadata, source hash, compiled script source, and applet executable against a
locally built package reference, then launches the signed app bundle
itself—not its internal script through `osascript`.

Run the MCP server with watch mode to keep the index current while events
change in Calendar.app:

```bash
mac-calendar-mcp serve --watch
```

The server performs a background sync at startup. Watch mode then checks
Calendar's local SQLite database, WAL, and SHM files every 3600 seconds and
refreshes the index when those files change. Override the interval with
`--watch-interval SECONDS` when you need faster or slower updates.

### Configure (Optional)

```bash
mac-calendar-mcp init   # writes ~/.mac-calendar-mcp/config.toml
```

Mac Calendar MCP reads settings from environment variables and an optional
TOML config file at `$HOME/.mac-calendar-mcp/config.toml`. The `init`
command writes a commented template with every available key and refuses to
overwrite an existing config unless `--force` is passed.

Common environment variables:

| Variable | Purpose |
|----------|---------|
| `APPLE_CALENDAR_INDEX_PATH` | Override the SQLite index location. |
| `APPLE_CALENDAR_INDEX_SOURCE` | Snapshot source: `auto` (default), `store`, `eventkit`, or `jxa`. |
| `APPLE_CALENDAR_INDEX_STALENESS_HOURS` | Hours before an index is considered stale. |
| `APPLE_CALENDAR_INDEX_CALENDARS` | Comma-separated calendar names or IDs to index; unset indexes all calendars. |
| `APPLE_CALENDAR_INDEX_PAST_YEARS` | Historical indexing window; defaults to 1 year. |
| `APPLE_CALENDAR_INDEX_FUTURE_YEARS` | Limit future indexing window. |
| `APPLE_CALENDAR_DEFAULT_CALENDARS` | Comma-separated tool-default calendar names or IDs when `calendar_ids` is omitted. |

`[defaults].calendars` only controls MCP tool defaults. `[index].calendars`
controls which calendars are stored in the local search index.

## Tools

| Tool | Purpose |
|------|---------|
| `list_calendars()` | List accessible calendars |
| `get_events(start, end, calendar_ids?, limit?, offset?)` | List event occurrences in a date range |
| `get_event(event_id, occurrence_start?)` | Get full event or occurrence detail |
| `search_events(query, start?, end?, calendar_ids?, fields?, limit?, offset?)` | Search indexed event archives |
| `get_agenda(start?, days?, calendar_ids?)` | Chronological agenda helper |
| `calendar_index_status()` | Index health and coverage summary |

All tools are read-only. The server does not create, update, delete, RSVP,
subscribe to calendars, or open Calendar.app UI in v1.

## Search and Indexing

Calendar search is backed by SQLite and FTS5. Indexed fields include event
title, location, notes, URL, attendee names/emails, and calendar name.

Recurring events are expanded into occurrence rows for listing and search. The
current recurrence layer supports common daily, weekly, monthly, and yearly
patterns, including intervals, counts, until dates, weekly `BYDAY`, and Calendar
exception dates. Unsupported recurrence rules are counted in index status
instead of being silently treated as complete.

## Configuration

Per-client env overrides via the MCP client's launch config work:

```json
{
  "mcpServers": {
    "calendar": {
      "command": "mac-calendar-mcp",
      "env": {
        "APPLE_CALENDAR_DEFAULT_CALENDARS": "Work,Personal",
        "APPLE_CALENDAR_INDEX_FUTURE_YEARS": "2"
      }
    }
  }
}
```

The default index path is `$HOME/.mac-calendar-mcp/index.db`.

## CLI Usage

All read tools are also available as standalone CLI commands:

```bash
mac-calendar-mcp calendars
mac-calendar-mcp authorize
mac-calendar-mcp init
mac-calendar-mcp index
mac-calendar-mcp status
mac-calendar-mcp search "quarterly planning" --limit 10
mac-calendar-mcp events 2026-05-01 2026-06-01 --limit 50
mac-calendar-mcp agenda --days 7
mac-calendar-mcp rebuild
mac-calendar-mcp rebuild --verbose  # source and snapshot counts
```

All data commands output JSON where practical.

## Development

```bash
git clone https://github.com/wagamama/apple-app-mcp
cd apple-app-mcp
uv sync
uv run ruff check packages/mac-calendar-mcp/src
uv run --package mac-calendar-mcp pytest packages/mac-calendar-mcp/tests
uv build --package mac-calendar-mcp
```

See [`CALENDAR.md`](../../CALENDAR.md) for domain architecture, tool design,
testing guidance, and implementation notes.

## License

GPL-3.0-or-later
