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
