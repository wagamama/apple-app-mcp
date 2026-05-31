from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch(
    "apple_calendar_mcp.server.execute_with_core_async",
    new_callable=AsyncMock,
)
async def test_list_calendars(mock_exec):
    mock_exec.return_value = [{"id": "cal-1", "name": "Work"}]

    from apple_calendar_mcp.server import list_calendars

    assert await list_calendars() == [{"id": "cal-1", "name": "Work"}]


@pytest.mark.asyncio
async def test_search_events_uses_index(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = True
    manager.search.return_value = [{"event_id": "event-1"}]
    monkeypatch.setattr(
        "apple_calendar_mcp.server._get_index_manager", lambda: manager
    )

    from apple_calendar_mcp.server import search_events

    assert await search_events("budget") == [{"event_id": "event-1"}]
    manager.search.assert_called_once()


@pytest.mark.asyncio
async def test_get_events_uses_default_calendars_when_omitted(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = True
    manager.events.return_value = [{"event_id": "event-1"}]
    monkeypatch.setattr(
        "apple_calendar_mcp.server._get_index_manager", lambda: manager
    )
    monkeypatch.setattr(
        "apple_calendar_mcp.server.get_default_calendars",
        lambda: ["Calendar"],
    )

    from apple_calendar_mcp.server import get_events

    assert await get_events("2026-01-01", "2026-01-02") == [
        {"event_id": "event-1"}
    ]
    assert manager.events.call_args.kwargs["calendar_ids"] == ["Calendar"]


@pytest.mark.asyncio
async def test_search_events_uses_default_calendars_when_omitted(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = True
    manager.search.return_value = [{"event_id": "event-1"}]
    monkeypatch.setattr(
        "apple_calendar_mcp.server._get_index_manager", lambda: manager
    )
    monkeypatch.setattr(
        "apple_calendar_mcp.server.get_default_calendars",
        lambda: ["Calendar"],
    )

    from apple_calendar_mcp.server import search_events

    await search_events("budget")

    assert manager.search.call_args.kwargs["calendar_ids"] == ["Calendar"]


@pytest.mark.asyncio
async def test_search_events_requires_index(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = False
    monkeypatch.setattr(
        "apple_calendar_mcp.server._get_index_manager", lambda: manager
    )

    from apple_calendar_mcp.server import search_events

    with pytest.raises(ValueError, match="No calendar index"):
        await search_events("budget")
