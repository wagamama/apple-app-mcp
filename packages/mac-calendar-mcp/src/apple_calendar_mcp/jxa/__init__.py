"""JXA script resources for Apple Calendar automation."""

from pathlib import Path

CALENDAR_CORE_JS = (Path(__file__).parent / "calendar_core.js").read_text()

__all__ = ["CALENDAR_CORE_JS"]
