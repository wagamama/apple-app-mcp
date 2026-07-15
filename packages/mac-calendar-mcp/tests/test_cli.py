from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from apple_calendar_mcp import cli
from apple_calendar_mcp.index.manager import CalendarIndexRefreshError


def test_format_size():
    assert cli._format_size(0.5) == "512.0 KB"
    assert cli._format_size(2.0) == "2.0 MB"


def test_status_no_index_exits(monkeypatch, capsys):
    manager = MagicMock()
    manager.has_index.return_value = False
    monkeypatch.setattr(cli, "IndexManager", lambda: manager)

    try:
        cli.status()
    except SystemExit as exc:
        assert exc.code == 1

    captured = capsys.readouterr()
    assert "No index found" in captured.out


@pytest.mark.parametrize(
    ("failed_jobs", "expected"),
    [
        (1, "1 failed job"),
        (2, "2 failed jobs"),
    ],
)
def test_index_exits_nonzero_when_failed_jobs_exist(
    monkeypatch, capsys, failed_jobs, expected
):
    manager = MagicMock()
    manager.build_from_jxa.return_value = 0
    manager.get_stats.return_value = SimpleNamespace(
        failed_jobs_count=failed_jobs
    )
    monkeypatch.setattr(cli, "IndexManager", lambda: manager)

    with pytest.raises(SystemExit) as excinfo:
        cli.index()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Indexed 0 occurrences" in captured.out
    assert expected in captured.err
    assert "failed_index_jobs" in captured.err


def test_index_succeeds_when_zero_occurrences_and_no_failed_jobs(
    monkeypatch, capsys
):
    manager = MagicMock()
    manager.build_from_jxa.return_value = 0
    manager.get_stats.return_value = SimpleNamespace(failed_jobs_count=0)
    monkeypatch.setattr(cli, "IndexManager", lambda: manager)

    cli.index()

    manager.get_stats.assert_called_once()
    captured = capsys.readouterr()
    assert "Indexed 0 occurrences" in captured.out
    assert captured.err == ""


def test_index_reports_preserved_refresh_failure(monkeypatch, capsys):
    manager = MagicMock()
    manager.build_from_jxa.side_effect = CalendarIndexRefreshError(
        "Calendar index refresh failed; active index preserved: timed out"
    )
    monkeypatch.setattr(cli, "IndexManager", lambda: manager)

    with pytest.raises(SystemExit) as excinfo:
        cli.index()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "active index preserved" in captured.err
    assert "Traceback" not in captured.err


def test_index_verbose_reports_failed_snapshot_source(monkeypatch, capsys):
    manager = MagicMock()
    manager.build_from_jxa.side_effect = CalendarIndexRefreshError(
        "Calendar index refresh failed; active index preserved: denied"
    )
    manager.last_build_source = "eventkit"
    manager.last_build_calendar_count = 0
    manager.last_build_event_count = 0
    monkeypatch.setattr(cli, "IndexManager", lambda: manager)

    with pytest.raises(SystemExit) as excinfo:
        cli.index(verbose=True)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Source: eventkit; calendars: 0; events: 0" in captured.err
    assert "active index preserved" in captured.err


def test_index_verbose_reports_snapshot_source(monkeypatch, capsys):
    manager = MagicMock()
    manager.build_from_jxa.return_value = 42
    manager.get_stats.return_value = SimpleNamespace(failed_jobs_count=0)
    manager.last_build_source = "eventkit"
    manager.last_build_calendar_count = 1
    manager.last_build_event_count = 42
    monkeypatch.setattr(cli, "IndexManager", lambda: manager)

    cli.index(verbose=True)

    captured = capsys.readouterr()
    assert "Source: eventkit; calendars: 1; events: 42" in captured.out


def test_watch_loop_syncs_until_stopped(capsys):
    manager = MagicMock()
    manager.sync_updates.side_effect = [3, 0]
    sleep = MagicMock()

    cli._watch_calendar_index(
        manager,
        interval_seconds=1,
        store_path=None,
        sleep=sleep,
        max_iterations=2,
    )

    assert manager.sync_updates.call_count == 2
    sleep.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Calendar index updated: 3 changes" in captured.err
    assert "Calendar index up to date" in captured.err


def test_watch_loop_syncs_when_calendar_store_changes(tmp_path, capsys):
    store = tmp_path / "Calendar.sqlitedb"
    store.write_text("initial")
    manager = MagicMock()
    manager.sync_updates.return_value = 4
    sleep = MagicMock(side_effect=lambda _: store.write_text("changed"))

    cli._watch_calendar_index(
        manager,
        interval_seconds=1,
        store_path=store,
        sleep=sleep,
        max_iterations=2,
    )

    assert manager.sync_updates.call_count == 1
    captured = capsys.readouterr()
    assert "Calendar index updated: 4 changes" in captured.err


def test_watch_loop_polling_falls_back_when_store_missing(capsys):
    manager = MagicMock()
    manager.sync_updates.return_value = 0
    sleep = MagicMock()

    cli._watch_calendar_index(
        manager,
        interval_seconds=1,
        store_path=Path("/missing/Calendar.sqlitedb"),
        sleep=sleep,
        max_iterations=2,
    )

    assert manager.sync_updates.call_count == 2
    captured = capsys.readouterr()
    assert "Calendar index up to date" in captured.err


def test_run_serve_background_syncs_without_watch(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = True
    manager.sync_updates.return_value = 0
    mcp = MagicMock()

    class ImmediateThread:
        def __init__(self, target, kwargs=None, daemon=False):
            self.target = target
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            self.target(**self.kwargs)

    monkeypatch.setattr(cli.IndexManager, "get_instance", lambda: manager)
    monkeypatch.setattr(cli.threading, "Thread", ImmediateThread)
    monkeypatch.setitem(
        __import__("sys").modules,
        "apple_calendar_mcp.server",
        MagicMock(mcp=mcp),
    )

    cli._run_serve(watch=False)

    manager.sync_updates.assert_called_once()
    mcp.run.assert_called_once()


def test_run_serve_starts_calendar_watch_thread(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = True
    started_targets = []
    mcp = MagicMock()

    class ImmediateThread:
        def __init__(self, target, kwargs=None, daemon=False):
            self.target = target
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            started_targets.append(self.target)
            self.target(**self.kwargs)

    monkeypatch.setattr(cli.IndexManager, "get_instance", lambda: manager)
    monkeypatch.setattr(cli.threading, "Thread", ImmediateThread)
    watch = MagicMock()
    monkeypatch.setattr(cli, "_watch_calendar_index", watch)
    monkeypatch.setitem(
        __import__("sys").modules,
        "apple_calendar_mcp.server",
        MagicMock(mcp=mcp),
    )

    cli._run_serve(watch=True, watch_interval=7)

    assert len(started_targets) == 1
    watch.assert_called_once()
    assert watch.call_args.kwargs["interval_seconds"] == 7
    mcp.run.assert_called_once()


def test_run_serve_uses_hourly_watch_interval_by_default(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = True
    mcp = MagicMock()

    class ImmediateThread:
        def __init__(self, target, kwargs=None, daemon=False):
            self.target = target
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            self.target(**self.kwargs)

    monkeypatch.setattr(cli.IndexManager, "get_instance", lambda: manager)
    monkeypatch.setattr(cli.threading, "Thread", ImmediateThread)
    watch = MagicMock()
    monkeypatch.setattr(cli, "_watch_calendar_index", watch)
    monkeypatch.setitem(
        __import__("sys").modules,
        "apple_calendar_mcp.server",
        MagicMock(mcp=mcp),
    )

    cli._run_serve(watch=True)

    assert watch.call_args.kwargs["interval_seconds"] == 3600
