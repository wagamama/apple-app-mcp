from __future__ import annotations

import importlib.metadata


def test_calendar_package_imports():
    import apple_calendar_mcp

    assert apple_calendar_mcp.__all__ == ["main"]
    assert callable(apple_calendar_mcp.main)


def test_calendar_distribution_exposes_console_scripts():
    dist = importlib.metadata.distribution("mac-calendar-mcp")
    scripts = {
        entry.name: entry.value
        for entry in dist.entry_points
        if entry.group == "console_scripts"
    }

    assert dist.metadata["Name"] == "mac-calendar-mcp"
    assert set(scripts) == {"mac-calendar-mcp"}
    assert scripts["mac-calendar-mcp"] == "apple_calendar_mcp:main"
