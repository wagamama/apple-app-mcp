"""Command-line interface for apple-calendar-mcp."""

from __future__ import annotations

import json
import sys
import time

import cyclopts

from .config import get_index_path
from .index import IndexManager

app = cyclopts.App(
    name="apple-calendar-mcp",
    help="Read-only MCP server for Apple Calendar with indexed search.",
)


def _format_size(size_mb: float) -> str:
    if size_mb < 1:
        return f"{size_mb * 1024:.1f} KB"
    return f"{size_mb:.1f} MB"


def _format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def _print_json(value) -> None:
    print(json.dumps(value, indent=2, default=str))


def _run_serve() -> None:
    from .server import mcp

    manager = IndexManager.get_instance()
    if manager.has_index() and manager.is_stale():
        manager.sync_updates()
    mcp.run()


@app.default
def default_handler() -> None:
    _run_serve()


@app.command
def serve() -> None:
    _run_serve()


@app.command
def index(verbose: bool = False) -> None:
    manager = IndexManager()
    start = time.time()
    count = manager.build_from_jxa()
    elapsed = _format_time(time.time() - start)
    print(f"Indexed {count:,} occurrences in {elapsed}")


@app.command
def status(verbose: bool = False) -> None:
    manager = IndexManager()
    if not manager.has_index():
        print("No index found.")
        print(f"Expected location: {get_index_path()}")
        sys.exit(1)
    stats = manager.get_stats()
    print("Apple Calendar MCP Index Status")
    print("=" * 40)
    print(f"Location:     {get_index_path()}")
    print(f"Calendars:    {stats.calendar_count:,}")
    print(f"Events:       {stats.event_count:,}")
    print(f"Occurrences:  {stats.occurrence_count:,}")
    print(f"Unsupported:  {stats.unsupported_recurrence_count:,}")
    print(f"Failed jobs:  {stats.failed_jobs_count:,}")
    print(f"Database:     {_format_size(stats.db_size_mb)}")


@app.command
def rebuild(verbose: bool = False) -> None:
    index(verbose=verbose)


@app.command
def search(query: str, limit: int = 20, offset: int = 0) -> None:
    manager = IndexManager()
    if not manager.has_index():
        print(
            "No index found. Run 'apple-calendar-mcp index'.", file=sys.stderr
        )
        sys.exit(1)
    _print_json(manager.search(query, limit=limit, offset=offset))


@app.command
def events(start: str, end: str, limit: int = 50, offset: int = 0) -> None:
    manager = IndexManager()
    _print_json(
        manager.events(start=start, end=end, limit=limit, offset=offset)
    )


@app.command
def calendars() -> None:
    from .builders import CalendarQueryBuilder
    from .executor import execute_with_core

    _print_json(execute_with_core(CalendarQueryBuilder().list_calendars()))


@app.command
def agenda(start: str | None = None, days: int = 1) -> None:
    manager = IndexManager()
    _print_json(manager.get_agenda(start=start, days=days))


def main() -> None:
    """Run the Apple Calendar MCP CLI."""
    app()
