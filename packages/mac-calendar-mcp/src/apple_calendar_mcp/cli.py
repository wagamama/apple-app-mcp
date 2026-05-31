"""Command-line interface for mac-calendar-mcp.

Usage:
    mac-calendar-mcp                 # Run MCP server
    mac-calendar-mcp serve           # Run MCP server explicitly
    mac-calendar-mcp serve --watch   # Run with periodic index updates
    mac-calendar-mcp init            # Write config.toml template
    mac-calendar-mcp index           # Build index from Calendar
    mac-calendar-mcp status          # Show index status
    mac-calendar-mcp rebuild         # Force rebuild index
"""

from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import cyclopts

from .config import get_index_path
from .index import IndexManager
from .index.store import DEFAULT_STORE_PATH

app = cyclopts.App(
    name="mac-calendar-mcp",
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


def _calendar_store_signature(
    store_path: Path,
) -> tuple[tuple[str, int, int], ...] | None:
    paths = [
        store_path,
        Path(f"{store_path}-wal"),
        Path(f"{store_path}-shm"),
    ]
    signature = []
    for path in paths:
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        signature.append((str(path), stat.st_mtime_ns, stat.st_size))
    if not signature:
        return None
    return tuple(signature)


def _watch_calendar_index(
    manager: IndexManager,
    *,
    interval_seconds: int,
    store_path: Path | None = DEFAULT_STORE_PATH,
    sleep: Callable[[float], None] = time.sleep,
    max_iterations: int | None = None,
) -> None:
    iterations = 0
    last_signature = (
        _calendar_store_signature(store_path)
        if store_path is not None
        else None
    )
    while max_iterations is None or iterations < max_iterations:
        should_sync = store_path is None
        if store_path is not None:
            current_signature = _calendar_store_signature(store_path)
            should_sync = (
                current_signature is None
                or last_signature is None
                or current_signature != last_signature
            )
            last_signature = current_signature
        if should_sync:
            _sync_calendar_index(manager, prefix="Calendar index")

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        sleep(interval_seconds)


def _sync_calendar_index(manager: IndexManager, *, prefix: str) -> None:
    start = time.time()
    try:
        count = manager.sync_updates()
        elapsed = _format_time(time.time() - start)
        if count:
            print(
                f"{prefix} updated: {count} changes ({elapsed})",
                file=sys.stderr,
            )
        else:
            print(
                f"{prefix} up to date ({elapsed})",
                file=sys.stderr,
            )
    except Exception as e:
        print(f"Warning: {prefix.lower()} sync failed: {e}", file=sys.stderr)


def _run_serve(watch: bool = False, watch_interval: int = 300) -> None:
    from .server import mcp

    manager = IndexManager.get_instance()

    def _background_sync() -> None:
        _sync_calendar_index(manager, prefix="Background sync")
        if watch:
            if manager.has_index():
                print(
                    f"Calendar watch started ({watch_interval}s interval)",
                    file=sys.stderr,
                )
                _watch_calendar_index(
                    manager,
                    interval_seconds=watch_interval,
                )
            else:
                print(
                    "Warning: No calendar index found after sync. "
                    "Run 'mac-calendar-mcp index'.",
                    file=sys.stderr,
                )

    sync_thread = threading.Thread(target=_background_sync, daemon=True)
    sync_thread.start()
    if watch:
        if manager.has_index():
            print(
                "Syncing calendar index in background before watch...",
                file=sys.stderr,
            )
        else:
            print("Building calendar index in background...", file=sys.stderr)
    else:
        print("Syncing calendar index in background...", file=sys.stderr)
    mcp.run()


@app.default
def default_handler(
    watch: Annotated[
        bool,
        cyclopts.Parameter(
            name=["--watch", "-w"],
            help="Poll Calendar and update the index while serving",
        ),
    ] = False,
    watch_interval: Annotated[
        int,
        cyclopts.Parameter(
            name=["--watch-interval"],
            help="Seconds between Calendar index refreshes in watch mode",
        ),
    ] = 300,
) -> None:
    _run_serve(watch=watch, watch_interval=watch_interval)


@app.command
def serve(
    watch: Annotated[
        bool,
        cyclopts.Parameter(
            name=["--watch", "-w"],
            help="Poll Calendar and update the index while serving",
        ),
    ] = False,
    watch_interval: Annotated[
        int,
        cyclopts.Parameter(
            name=["--watch-interval"],
            help="Seconds between Calendar index refreshes in watch mode",
        ),
    ] = 300,
) -> None:
    _run_serve(watch=watch, watch_interval=watch_interval)


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
    print("Mac Calendar MCP Index Status")
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


@app.command(name="init")
def cli_init(
    force: Annotated[
        bool,
        cyclopts.Parameter(
            name=["--force", "-f"],
            help="Overwrite an existing config.toml",
        ),
    ] = False,
) -> None:
    """
    Write a commented config.toml template to ~/.mac-calendar-mcp/.

    The template documents every available key alongside its matching
    environment variable. Edit and uncomment to override defaults.
    Existing config files are not overwritten unless --force is given.
    """
    from .config import CONFIG_FILE_PATH, CONFIG_TEMPLATE

    path = CONFIG_FILE_PATH

    if path.exists() and not force:
        print(f"Config file already exists: {path}", file=sys.stderr)
        print("Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONFIG_TEMPLATE)
    path.chmod(0o600)

    print(f"Wrote config template to {path}")
    print("Edit and uncomment keys to override defaults.")


@app.command
def search(query: str, limit: int = 20, offset: int = 0) -> None:
    manager = IndexManager()
    if not manager.has_index():
        print("No index found. Run 'mac-calendar-mcp index'.", file=sys.stderr)
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
    """Run the Mac Calendar MCP CLI."""
    app()
