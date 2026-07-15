from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

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


def test_failed_refresh_preserves_existing_index(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)
    healthy_snapshot = {
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
                "title": "Keep me",
                "location": "",
                "notes": "",
                "url": "",
                "status": "confirmed",
                "all_day": False,
                "start_date": "2026-07-15T10:00:00Z",
                "end_date": "2026-07-15T11:00:00Z",
                "modified_at": "2026-07-15T09:00:00Z",
                "recurrence": "",
                "excluded_dates": [],
                "attendees": [],
            }
        ],
        "failed_jobs": [],
    }
    failed_snapshot = {
        "calendars": [{"id": "cal-1", "name": "Work"}],
        "events": [],
        "failed_jobs": [
            {
                "job_key": "calendar:cal-1",
                "calendar_id": "cal-1",
                "error_type": "calendar_event_fetch_failed",
                "error_message": "timed out",
            }
        ],
    }

    with patch.object(manager, "fetch_snapshot", return_value=healthy_snapshot):
        manager.build_from_jxa()

    with (
        patch.object(manager, "fetch_snapshot", return_value=failed_snapshot),
        pytest.raises(RuntimeError, match="Calendar index refresh failed"),
    ):
        manager.build_from_jxa()

    agenda = manager.get_agenda(start="2026-07-15", days=1)
    assert [event["title"] for event in agenda] == ["Keep me"]
    assert manager.get_stats().failed_jobs_count == 1


def test_unconfirmed_empty_legacy_snapshot_is_rejected(tmp_path):
    manager = IndexManager(db_path=tmp_path / "calendar.db")
    snapshot = {
        "source": "calendar-jxa",
        "calendars": [{"id": "cal-1", "name": "Work"}],
        "events": [],
        "failed_jobs": [],
    }

    with (
        patch.object(manager, "fetch_snapshot", return_value=snapshot),
        pytest.raises(RuntimeError, match="unconfirmed empty snapshot"),
    ):
        manager.build_from_jxa()

    assert manager.get_stats().failed_jobs_count == 1


def test_completely_empty_legacy_snapshot_is_rejected(tmp_path):
    manager = IndexManager(db_path=tmp_path / "calendar.db")
    snapshot = {
        "source": "calendar-jxa",
        "calendars": [],
        "events": [],
        "failed_jobs": [],
    }

    with (
        patch.object(manager, "fetch_snapshot", return_value=snapshot),
        pytest.raises(RuntimeError, match="unconfirmed empty snapshot"),
    ):
        manager.build_from_jxa()

    assert manager.get_stats().failed_jobs_count == 1


def test_refresh_exception_rolls_back_to_existing_index(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)
    healthy_snapshot = {
        "calendars": [
            {
                "id": "cal-1",
                "name": "Work",
                "color": None,
                "writable": True,
                "description": "",
            }
        ],
        "events": [
            {
                "event_id": "event-1",
                "calendar_id": "cal-1",
                "calendar_name": "Work",
                "title": "Keep me",
                "location": "",
                "notes": "",
                "url": "",
                "status": "confirmed",
                "all_day": False,
                "start_date": "2026-07-15T10:00:00Z",
                "end_date": "2026-07-15T11:00:00Z",
                "modified_at": None,
                "recurrence": "",
                "excluded_dates": [],
                "attendees": [],
            }
        ],
        "failed_jobs": [],
    }

    with patch.object(manager, "fetch_snapshot", return_value=healthy_snapshot):
        manager.build_from_jxa()

    with (
        patch.object(manager, "fetch_snapshot", return_value=healthy_snapshot),
        patch(
            "apple_calendar_mcp.index.sync.expand_occurrences",
            side_effect=ValueError("bad recurrence"),
        ),
        pytest.raises(ValueError, match="bad recurrence"),
    ):
        manager.build_from_jxa()

    agenda = manager.get_agenda(start="2026-07-15", days=1)
    assert [event["title"] for event in agenda] == ["Keep me"]


def test_manager_reports_stale_index_when_last_sync_exceeds_threshold(tmp_path):
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
        manager.build_from_jxa()

    stale_time = datetime.now(UTC) - timedelta(hours=3)
    manager._connection().execute(
        "UPDATE calendars SET indexed_at = ?",
        (stale_time.strftime("%Y-%m-%d %H:%M:%S"),),
    )
    manager._connection().commit()

    with patch(
        "apple_calendar_mcp.index.manager.get_index_staleness_hours",
        return_value=1,
    ):
        assert manager.is_stale() is True


def test_fetch_snapshot_uses_configured_year_windows(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_eventkit",
            side_effect=JXAError("EventKit unavailable"),
        ),
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
            "source": "calendar-jxa",
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
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_store"
        ) as fetch,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_eventkit"
        ) as eventkit,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        store.exists.return_value = True
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = ["Calendar"]
        fetch.return_value = {
            "calendars": [{"id": "Calendar", "name": "Calendar"}],
            "events": [{"event_id": "event-1"}],
            "failed_jobs": [],
            "source": "calendar-jxa",
        }

        assert manager.fetch_snapshot() == {
            "calendars": [{"id": "Calendar", "name": "Calendar"}],
            "events": [{"event_id": "event-1"}],
            "failed_jobs": [],
            "source": "calendar-store",
        }

    fetch.assert_called_once()
    assert fetch.call_args.kwargs["calendar_names_or_ids"] == ["Calendar"]
    eventkit.assert_not_called()
    execute.assert_not_called()


def test_fetch_snapshot_logs_local_store_fallback_reason(tmp_path, caplog):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)
    caplog.set_level(logging.WARNING)

    with (
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_store"
        ) as fetch,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_eventkit",
            side_effect=JXAError("EventKit unavailable"),
        ),
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        store.exists.return_value = True
        store.__str__.return_value = "/Calendar.sqlitedb"
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
            "source": "calendar-jxa",
        }

    assert fetch.call_count == 1
    assert execute.call_count == 2
    assert "Falling back to Calendar JXA" in caplog.text
    assert "OSError: store unavailable" in caplog.text


def test_fetch_snapshot_uses_eventkit_after_store_failure(tmp_path):
    manager = IndexManager(db_path=tmp_path / "calendar.db")
    eventkit_snapshot = {
        "calendars": [{"id": "cal-1", "name": "Calendar"}],
        "events": [{"event_id": "event-1"}],
        "failed_jobs": [],
    }

    with (
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_store",
            side_effect=OSError("store unavailable"),
        ),
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_eventkit",
            return_value=eventkit_snapshot,
        ) as eventkit,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as legacy,
    ):
        store.exists.return_value = True
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = ["Calendar"]

        assert manager.fetch_snapshot() == eventkit_snapshot

    eventkit.assert_called_once()
    assert eventkit.call_args.kwargs["calendar_names_or_ids"] == ["Calendar"]
    legacy.assert_not_called()


def test_fetch_snapshot_confirms_empty_store_with_eventkit(tmp_path):
    manager = IndexManager(db_path=tmp_path / "calendar.db")
    empty_store_snapshot = {
        "calendars": [{"id": "Calendar", "name": "Calendar"}],
        "events": [],
        "failed_jobs": [],
    }
    eventkit_snapshot = {
        "calendars": [{"id": "cal-1", "name": "Calendar"}],
        "events": [{"event_id": "event-1"}],
        "failed_jobs": [],
    }

    with (
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_store",
            return_value=empty_store_snapshot,
        ),
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_eventkit",
            return_value=eventkit_snapshot,
        ) as eventkit,
    ):
        store.exists.return_value = True
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = ["Calendar"]

        assert manager.fetch_snapshot() == eventkit_snapshot

    eventkit.assert_called_once()


def test_fetch_snapshot_can_force_eventkit_source(tmp_path):
    manager = IndexManager(db_path=tmp_path / "calendar.db")
    eventkit_snapshot = {
        "source": "eventkit",
        "calendars": [{"id": "cal-1", "name": "Calendar"}],
        "events": [{"event_id": "event-1"}],
        "failed_jobs": [],
    }

    with (
        patch(
            "apple_calendar_mcp.index.manager.get_index_source",
            return_value="eventkit",
        ),
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_eventkit",
            return_value=eventkit_snapshot,
        ) as eventkit,
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_store"
        ) as local_store,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as legacy,
    ):
        store.exists.return_value = True

        assert manager.fetch_snapshot() == eventkit_snapshot

    eventkit.assert_called_once()
    local_store.assert_not_called()
    legacy.assert_not_called()


def test_forced_eventkit_failure_becomes_preserved_refresh_failure(tmp_path):
    manager = IndexManager(db_path=tmp_path / "calendar.db")

    with (
        patch(
            "apple_calendar_mcp.index.manager.get_index_source",
            return_value="eventkit",
        ),
        patch(
            "apple_calendar_mcp.index.manager.fetch_snapshot_from_eventkit",
            side_effect=JXAError("EventKit unavailable"),
        ),
    ):
        snapshot = manager.fetch_snapshot()

    assert snapshot["source"] == "eventkit"
    assert snapshot["calendars"] == []
    assert snapshot["events"] == []
    assert snapshot["failed_jobs"] == [
        {
            "job_key": "source:eventkit",
            "calendar_id": None,
            "error_type": "eventkit_fetch_failed",
            "error_message": "EventKit snapshot failed: EventKit unavailable",
        }
    ]


def test_read_waits_for_atomic_index_publication(tmp_path):
    manager = IndexManager(db_path=tmp_path / "calendar.db")
    initial_snapshot = {
        "calendars": [{"id": "cal-1", "name": "Work"}],
        "events": [],
    }
    with patch.object(manager, "fetch_snapshot", return_value=initial_snapshot):
        manager.build_from_jxa()

    publish_started = threading.Event()
    release_publish = threading.Event()
    reader_finished = threading.Event()

    def slow_publish(*args, **kwargs):
        publish_started.set()
        assert release_publish.wait(timeout=2)
        return type("Result", (), {"added": 0, "errors": 0})()

    with (
        patch.object(manager, "fetch_snapshot", return_value=initial_snapshot),
        patch(
            "apple_calendar_mcp.index.manager.sync_from_snapshot",
            side_effect=slow_publish,
        ),
    ):
        publisher = threading.Thread(target=manager.build_from_jxa)
        publisher.start()
        assert publish_started.wait(timeout=2)

        reader = threading.Thread(
            target=lambda: (
                manager.events(
                    start="2026-01-01T00:00:00Z",
                    end="2027-01-01T00:00:00Z",
                ),
                reader_finished.set(),
            )
        )
        reader.start()
        assert not reader_finished.wait(timeout=0.1)

        release_publish.set()
        publisher.join(timeout=2)
        reader.join(timeout=2)

    assert not publisher.is_alive()
    assert not reader.is_alive()
    assert reader_finished.is_set()


def test_fetch_snapshot_defaults_to_bounded_past_window(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.get_index_source",
            return_value="jxa",
        ),
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


def test_fetch_snapshot_uses_index_calendars_as_event_scope(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.get_index_source",
            return_value="jxa",
        ),
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


def test_fetch_snapshot_records_jxa_error_detail(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.get_index_source",
            return_value="jxa",
        ),
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

        snapshot = manager.fetch_snapshot()

    assert snapshot["calendars"] == [{"id": "slow", "name": "Slow"}]
    assert snapshot["events"] == []
    assert snapshot["failed_jobs"][0]["job_key"] == "calendar:slow"
    assert snapshot["failed_jobs"][0]["calendar_id"] == "slow"
    assert (
        snapshot["failed_jobs"][0]["error_type"]
        == "calendar_event_fetch_failed"
    )
    assert "slow" in snapshot["failed_jobs"][0]["error_message"]
    assert "Slow" in snapshot["failed_jobs"][0]["error_message"]
    assert (
        "JXA script timed out after 15s"
        in snapshot["failed_jobs"][0]["error_message"]
    )


def test_fetch_snapshot_records_calendar_discovery_error(tmp_path):
    manager = IndexManager(db_path=tmp_path / "calendar.db")

    with (
        patch(
            "apple_calendar_mcp.index.manager.get_index_source",
            return_value="jxa",
        ),
        patch(
            "apple_calendar_mcp.index.manager.execute_with_core",
            side_effect=JXAError("Calendar discovery timed out"),
        ),
    ):
        snapshot = manager.fetch_snapshot()

    assert snapshot["source"] == "calendar-jxa"
    assert snapshot["calendars"] == []
    assert snapshot["events"] == []
    assert snapshot["failed_jobs"] == [
        {
            "job_key": "source:calendar-jxa",
            "calendar_id": None,
            "error_type": "calendar_discovery_failed",
            "error_message": (
                "Calendar discovery failed: Calendar discovery timed out"
            ),
        }
    ]

    with (
        patch.object(manager, "fetch_snapshot", return_value=snapshot),
        pytest.raises(RuntimeError, match="Calendar discovery failed"),
    ):
        manager.build_from_jxa()

    rows = (
        manager._connection()
        .execute("SELECT job_key FROM failed_index_jobs")
        .fetchall()
    )
    assert [row["job_key"] for row in rows] == ["source:calendar-jxa"]


def test_fetch_snapshot_records_jxa_stderr_when_available(tmp_path):
    db_path = tmp_path / "calendar.db"
    manager = IndexManager(db_path=db_path)

    with (
        patch("apple_calendar_mcp.index.manager.get_index_past_years") as past,
        patch("apple_calendar_mcp.index.manager.get_index_future_years") as fut,
        patch("apple_calendar_mcp.index.manager.get_index_calendars") as cals,
        patch(
            "apple_calendar_mcp.index.manager.get_index_source",
            return_value="jxa",
        ),
        patch("apple_calendar_mcp.index.manager.DEFAULT_STORE_PATH") as store,
        patch("apple_calendar_mcp.index.manager.execute_with_core") as execute,
    ):
        past.return_value = 1
        fut.return_value = 1
        cals.return_value = None
        store.exists.return_value = False
        execute.side_effect = [
            [{"id": "slow", "name": "Slow"}],
            JXAError(
                "JXA script failed",
                stderr="execution error: Calendar got an error",
            ),
        ]

        snapshot = manager.fetch_snapshot()

    assert "JXA script failed" in snapshot["failed_jobs"][0]["error_message"]
    assert (
        "execution error: Calendar got an error"
        in snapshot["failed_jobs"][0]["error_message"]
    )
