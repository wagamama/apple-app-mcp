# Apple Calendar MCP

<!-- mcp-name: io.github.wagamama/apple-calendar-mcp -->

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Read-only Apple Calendar MCP server with indexed archive search. It exposes
Apple Calendar data to MCP clients through a small read surface for listing
calendars, browsing event ranges, reading event details, searching archived
events, and building agendas.

This package is developed in the
[`apple-app-mcp`](https://github.com/wagamama/apple-app-mcp) workspace alongside
Apple Mail MCP.

## Quick Start

```bash
pipx install apple-calendar-mcp
```

Add to your MCP client:

```json
{
  "mcpServers": {
    "calendar": {
      "command": "apple-calendar-mcp"
    }
  }
}
```

### Build the Search Index (Recommended)

```bash
# Requires Calendar automation permission for Terminal or your MCP client
# System Settings -> Privacy & Security -> Automation

apple-calendar-mcp index
```

The index enables fast archive search and date-range reads from a local SQLite
and FTS5 database.

### Configure (Optional)

Apple Calendar MCP reads settings from environment variables and an optional
TOML config file at `$HOME/.apple-calendar-mcp/config.toml`.

Common environment variables:

| Variable | Purpose |
|----------|---------|
| `APPLE_CALENDAR_INDEX_PATH` | Override the SQLite index location. |
| `APPLE_CALENDAR_INDEX_STALENESS_HOURS` | Hours before an index is considered stale. |
| `APPLE_CALENDAR_INDEX_PAST_YEARS` | Limit historical indexing window. |
| `APPLE_CALENDAR_INDEX_FUTURE_YEARS` | Limit future indexing window. |
| `APPLE_CALENDAR_DEFAULT_CALENDARS` | Comma-separated default calendar names or IDs. |

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
      "command": "apple-calendar-mcp",
      "env": {
        "APPLE_CALENDAR_DEFAULT_CALENDARS": "Work,Personal",
        "APPLE_CALENDAR_INDEX_FUTURE_YEARS": "2"
      }
    }
  }
}
```

The default index path is `$HOME/.apple-calendar-mcp/index.db`.

## CLI Usage

All read tools are also available as standalone CLI commands:

```bash
apple-calendar-mcp calendars
apple-calendar-mcp index
apple-calendar-mcp status
apple-calendar-mcp search "quarterly planning" --limit 10
apple-calendar-mcp events 2026-05-01 2026-06-01 --limit 50
apple-calendar-mcp agenda --days 7
apple-calendar-mcp rebuild
```

All data commands output JSON where practical.

## Development

```bash
git clone https://github.com/wagamama/apple-app-mcp
cd apple-app-mcp
uv sync
uv run ruff check packages/apple-calendar-mcp/src
uv run --package apple-calendar-mcp pytest packages/apple-calendar-mcp/tests
uv build --package apple-calendar-mcp
```

See [`CALENDAR.md`](../../CALENDAR.md) for domain architecture, tool design,
testing guidance, and implementation notes.

## License

GPL-3.0-or-later
