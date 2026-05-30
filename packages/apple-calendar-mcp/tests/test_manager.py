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
