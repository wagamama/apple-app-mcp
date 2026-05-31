from __future__ import annotations

from unittest.mock import patch

from apple_calendar_mcp.executor import JXAError
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
        patch("apple_calendar_mcp.index.manager.get_default_calendars") as cals,
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        past.return_value = 3
        fut.return_value = 2
        cals.return_value = None
        store.exists.return_value = False
        execute.side_effect = [
            [{"id": "cal-1", "name": "Work"}],
            [{"event_id": "event-1"}],
        ]

        assert manager.fetch_snapshot() == {
            "calendars": [{"id": "cal-1", "name": "Work"}],
            "events": [{"event_id": "event-1"}],
            "failed_jobs": [],
        }

    script = execute.call_args.args[0]
    assert "now.getFullYear() - 3" in script
    assert "now.getFullYear() + 2" in script
    assert '["cal-1"]' in script


def test_fetch_snapshot_prefers_local_store_when_available(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_default_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_store"
        ) as fetch,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        store.exists.return_value = True
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = ["Calendar"]
        fetch.return_value = {"calendars": [], "events": [], "failed_jobs": []}

        assert manager.fetch_snapshot() == {
            "calendars": [],
            "events": [],
            "failed_jobs": [],
        }

    fetch.assert_called_once()
    assert fetch.call_args.kwargs["calendar_names_or_ids"] == ["Calendar"]
    execute.assert_not_called()


def test_fetch_snapshot_falls_back_to_jxa_when_local_store_fails(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_default_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_store"
        ) as fetch,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        store.exists.return_value = True
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = ["Calendar"]
        fetch.side_effect = OSError("store unavailable")
        execute.side_effect = [
            [{"id": "Calendar", "name": "Calendar"}],
            [{"event_id": "event-1"}],
        ]

        assert manager.fetch_snapshot() == {
            "calendars": [{"id": "Calendar", "name": "Calendar"}],
            "events": [{"event_id": "event-1"}],
            "failed_jobs": [],
        }

    assert fetch.call_count == 1
    assert execute.call_count == 2


def test_fetch_snapshot_defaults_to_bounded_past_window(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_default_calendars") as cals,
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = None
        store.exists.return_value = False
        execute.side_effect = [
            [{"id": "cal-1", "name": "Work"}],
            [],
        ]

        manager.fetch_snapshot()

    script = execute.call_args.args[0]
    assert "new Date(1970, 0, 1)" not in script
    assert "now.getFullYear() - 1" in script


def test_fetch_snapshot_uses_default_calendars_as_event_scope(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_default_calendars") as cals,
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = ["Work"]
        store.exists.return_value = False
        execute.side_effect = [
            [{"id": "cal-1", "name": "Work"}],
            [{"event_id": "event-1"}],
        ]

        manager.fetch_snapshot()

    assert execute.call_count == 2
    script = execute.call_args.args[0]
    assert '["Work"]' in script


def test_fetch_snapshot_skips_calendar_when_event_fetch_times_out(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_default_calendars") as cals,
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = None
        store.exists.return_value = False
        execute.side_effect = [
            [{"id": "slow", "name": "Slow"}],
            JXAError("JXA script timed out after 15s"),
        ]

        assert manager.fetch_snapshot() == {
            "calendars": [{"id": "slow", "name": "Slow"}],
            "events": [],
            "failed_jobs": [
                {
                    "job_key": "calendar:slow",
                    "calendar_id": "slow",
                    "error_type": "calendar_event_fetch_failed",
                    "error_message": (
                        "Calendar event fetch timed out or failed"
                    ),
                }
            ],
        }
