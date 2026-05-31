"""Mac Calendar MCP - read-only archive search for Apple Calendar.

Usage:
    mac-calendar-mcp index
    mac-calendar-mcp serve --watch
"""

from .cli import main

__all__ = ["main"]
