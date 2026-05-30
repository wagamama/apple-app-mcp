from __future__ import annotations

import asyncio
from typing import Literal

from fastmcp import FastMCP
from typing_extensions import TypedDict

from .builders import CalendarQueryBuilder
from .executor import execute_with_core_async
from .index import IndexManager

mcp = FastMCP("Apple Calendar")


class CalendarSummary(TypedDict, total=False):
    id: str
    name: str
    color: str
    writable: bool
    description: str | None


def _get_index_manager() -> IndexManager:
    return IndexManager.get_instance()


@mcp.tool
async def list_calendars() -> list[CalendarSummary]:
    script = CalendarQueryBuilder().list_calendars()
    return await execute_with_core_async(script)


@mcp.tool
async def get_events(
    start: str,
    end: str,
    calendar_ids: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    manager = _get_index_manager()
    if not manager.has_index():
        raise ValueError("No calendar index. Run 'apple-calendar-mcp index'.")
    return manager.events(
        start=start,
        end=end,
        calendar_ids=calendar_ids,
        limit=limit,
        offset=offset,
    )


@mcp.tool
async def get_event(
    event_id: str,
    occurrence_start: str | None = None,
) -> dict:
    manager = _get_index_manager()
    if not manager.has_index():
        raise ValueError("No calendar index. Run 'apple-calendar-mcp index'.")
    return await asyncio.to_thread(
        manager.get_event,
        event_id,
        occurrence_start=occurrence_start,
    )


@mcp.tool
async def search_events(
    query: str,
    start: str | None = None,
    end: str | None = None,
    calendar_ids: list[str] | None = None,
    fields: list[
        Literal[
            "all",
            "title",
            "location",
            "notes",
            "attendees",
            "calendar",
        ]
    ]
    | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    manager = _get_index_manager()
    if not manager.has_index():
        raise ValueError("No calendar index. Run 'apple-calendar-mcp index'.")
    return manager.search(
        query,
        start=start,
        end=end,
        calendar_ids=calendar_ids,
        fields=fields,
        limit=limit,
        offset=offset,
    )


@mcp.tool
async def get_agenda(
    start: str | None = None,
    days: int = 1,
    calendar_ids: list[str] | None = None,
) -> list[dict]:
    manager = _get_index_manager()
    if not manager.has_index():
        raise ValueError("No calendar index. Run 'apple-calendar-mcp index'.")
    return await asyncio.to_thread(
        manager.get_agenda,
        start=start,
        days=days,
        calendar_ids=calendar_ids,
    )


@mcp.tool
async def calendar_index_status() -> dict:
    manager = _get_index_manager()
    stats = await asyncio.to_thread(manager.get_stats)
    return stats.__dict__


@mcp.resource(
    "calendar-index://status",
    mime_type="application/json",
    description="Read-only snapshot of the Calendar search index.",
)
async def calendar_index_status_resource() -> dict:
    return await calendar_index_status()
