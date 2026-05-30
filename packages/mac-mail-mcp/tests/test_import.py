from __future__ import annotations

import importlib.metadata


def test_mail_package_imports():
    import apple_mail_mcp

    assert apple_mail_mcp.__all__ == ["main", "mcp"]
    assert callable(apple_mail_mcp.main)


def test_mail_distribution_exposes_console_scripts():
    dist = importlib.metadata.distribution("mac-mail-mcp")
    scripts = {
        entry.name: entry.value
        for entry in dist.entry_points
        if entry.group == "console_scripts"
    }

    assert dist.metadata["Name"] == "mac-mail-mcp"
    assert set(scripts) == {"mac-mail-mcp"}
    assert scripts["mac-mail-mcp"] == "apple_mail_mcp:main"
