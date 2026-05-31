from __future__ import annotations

from unittest.mock import MagicMock

from apple_calendar_mcp import cli


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


def test_watch_loop_syncs_until_stopped(capsys):
    manager = MagicMock()
    manager.sync_updates.side_effect = [3, 0]
    sleep = MagicMock()

    cli._watch_calendar_index(
        manager,
        interval_seconds=1,
        sleep=sleep,
        max_iterations=2,
    )

    assert manager.sync_updates.call_count == 2
    sleep.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Calendar index updated: 3 changes" in captured.err
    assert "Calendar index up to date" in captured.err


def test_run_serve_starts_calendar_watch_thread(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = True
    fake_thread = MagicMock()
    thread_factory = MagicMock(return_value=fake_thread)
    mcp = MagicMock()

    monkeypatch.setattr(cli.IndexManager, "get_instance", lambda: manager)
    monkeypatch.setattr(cli.threading, "Thread", thread_factory)
    monkeypatch.setattr(cli, "_watch_calendar_index", MagicMock())
    monkeypatch.setitem(
        __import__("sys").modules,
        "apple_calendar_mcp.server",
        MagicMock(mcp=mcp),
    )

    cli._run_serve(watch=True, watch_interval=7)

    thread_factory.assert_called_once()
    assert thread_factory.call_args.kwargs["daemon"] is True
    fake_thread.start.assert_called_once()
    mcp.run.assert_called_once()
