from __future__ import annotations

from unittest.mock import patch

from apple_calendar_mcp.index.manager import IndexManager


def test_manager_builds_index_from_snapshot(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)
    snapshot = {
        "calendars": [
            {
                "id": "cal-1",
                "name": "Work",
                "color": "#ff0000",
                "writable": True,
                "description": "",
            }
        ],
        "events": [],
    }

    with patch.object(manager, "fetch_snapshot", return_value=snapshot):
        count = manager.build_from_jxa()

    assert count == 0
    assert manager.has_index() is True
    stats = manager.get_stats()
    assert stats.calendar_count == 1
    assert stats.occurrence_count == 0


def test_manager_search_returns_results(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)
    snapshot = {
        "calendars": [
            {
                "id": "cal-1",
                "name": "Work",
                "color": "#ff0000",
                "writable": True,
                "description": "",
            }
        ],
        "events": [
            {
                "event_id": "event-1",
                "calendar_id": "cal-1",
                "calendar_name": "Work",
                "title": "Budget review",
                "location": "",
                "notes": "Discuss budget",
                "url": "",
                "status": "confirmed",
                "all_day": False,
                "start_date": "2026-05-01T10:00:00Z",
                "end_date": "2026-05-01T11:00:00Z",
                "modified_at": "2026-04-01T00:00:00Z",
                "recurrence": "",
                "excluded_dates": [],
                "attendees": [],
            }
        ],
    }

    with patch.object(manager, "fetch_snapshot", return_value=snapshot):
        manager.build_from_jxa()

    assert manager.search("budget")[0]["event_id"] == "event-1"
    stats = manager.get_stats()
    assert stats.coverage_start == "2026-05-01T10:00:00Z"
    assert stats.coverage_end == "2026-05-01T11:00:00Z"


def test_fetch_snapshot_uses_configured_year_windows(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        past.return_value = 3
        fut.return_value = 2
        execute.return_value = {"calendars": [], "events": []}

        assert manager.fetch_snapshot() == {"calendars": [], "events": []}

    script = execute.call_args.args[0]
    assert "now.getFullYear() - 3" in script
    assert "now.getFullYear() + 2" in script
