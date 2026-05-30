"""Configuration for Apple Calendar MCP server."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

DEFAULT_INDEX_PATH = Path.home() / ".apple-calendar-mcp" / "index.db"
CONFIG_FILE_PATH = Path.home() / ".apple-calendar-mcp" / "config.toml"
CONFIG_SCHEMA_VERSION = 1

CONFIG_SCHEMA: dict[str, dict[str, tuple[type, ...]]] = {
    "defaults": {
        "calendars": (list,),
    },
    "index": {
        "path": (str,),
        "staleness_hours": (int, float),
        "past_years": (int,),
        "future_years": (int,),
        "max_occurrences_per_series": (int,),
    },
}


class ConfigError(RuntimeError):
    """Raised when the Calendar MCP config file is invalid."""


_NOT_LOADED = object()
_cached_config: object = _NOT_LOADED


def _invalidate_config_cache() -> None:
    """Reset the process-wide TOML config cache."""
    global _cached_config
    _cached_config = _NOT_LOADED


def _load_config_file() -> dict:
    """Load and validate the Calendar MCP TOML config file."""
    global _cached_config
    if _cached_config is not _NOT_LOADED:
        return _cached_config  # type: ignore[return-value]
    if not CONFIG_FILE_PATH.exists():
        _cached_config = {}
        return {}
    try:
        with CONFIG_FILE_PATH.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{CONFIG_FILE_PATH}: TOML syntax error: {e}") from e
    _validate(data)
    _cached_config = data
    return data


def _validate(data: dict) -> None:
    version = data.get("config_version")
    if version is None:
        raise ConfigError(
            f"{CONFIG_FILE_PATH}: missing required key `config_version`."
        )
    if version != CONFIG_SCHEMA_VERSION:
        raise ConfigError(
            f"{CONFIG_FILE_PATH}: unsupported config_version {version!r}."
        )

    allowed_top = {"config_version"} | set(CONFIG_SCHEMA)
    for key in data:
        if key not in allowed_top:
            raise ConfigError(f"{CONFIG_FILE_PATH}: unknown key `{key}`.")

    for section, keys in CONFIG_SCHEMA.items():
        section_data = data.get(section)
        if section_data is None:
            continue
        if not isinstance(section_data, dict):
            raise ConfigError(
                f"{CONFIG_FILE_PATH}: [{section}] must be a table."
            )
        for key, value in section_data.items():
            if key not in keys:
                raise ConfigError(
                    f"{CONFIG_FILE_PATH}: unknown key `[{section}] {key}`."
                )
            expected = keys[key]
            if (
                int in expected
                and bool not in expected
                and isinstance(value, bool)
            ):
                raise ConfigError(
                    f"{CONFIG_FILE_PATH}: `[{section}] {key}` expected int."
                )
            if not isinstance(value, expected):
                names = " | ".join(t.__name__ for t in expected)
                raise ConfigError(
                    f"{CONFIG_FILE_PATH}: `[{section}] {key}` expected {names}."
                )
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if not isinstance(item, str):
                        raise ConfigError(
                            f"{CONFIG_FILE_PATH}: "
                            f"`[{section}] {key}[{i}]` expected str."
                        )

    index = data.get("index", {})
    for key in (
        "staleness_hours",
        "past_years",
        "future_years",
        "max_occurrences_per_series",
    ):
        if key in index and index[key] < 0:
            raise ConfigError(
                f"{CONFIG_FILE_PATH}: `[index] {key}` must be >= 0."
            )


def _from_toml(*path: str):
    val: object = _load_config_file()
    for key in path:
        if not isinstance(val, dict) or key not in val:
            return None
        val = val[key]
    return val


def get_index_path() -> Path:
    """Return the Calendar MCP index database path."""
    env = os.environ.get("APPLE_CALENDAR_INDEX_PATH")
    if env:
        return Path(env).expanduser()
    val = _from_toml("index", "path")
    if val:
        return Path(val).expanduser()
    return DEFAULT_INDEX_PATH


def get_index_staleness_hours() -> float:
    """Return hours before the Calendar index is considered stale."""
    raw = os.environ.get("APPLE_CALENDAR_INDEX_STALENESS_HOURS")
    if raw is not None and raw != "":
        return float(raw)
    val = _from_toml("index", "staleness_hours")
    if val is not None:
        return float(val)
    return 24.0


def get_index_past_years() -> int | None:
    """Return optional archive backfill limit in years."""
    raw = os.environ.get("APPLE_CALENDAR_INDEX_PAST_YEARS")
    if raw is not None and raw != "":
        return int(raw)
    val = _from_toml("index", "past_years")
    if val is not None:
        return int(val)
    return None


def get_index_future_years() -> int:
    """Return future expansion window for recurring events."""
    raw = os.environ.get("APPLE_CALENDAR_INDEX_FUTURE_YEARS")
    if raw is not None and raw != "":
        return int(raw)
    val = _from_toml("index", "future_years")
    if val is not None:
        return int(val)
    return 1


def get_index_max_occurrences_per_series() -> int:
    """Return safety cap for recurring-event occurrence expansion."""
    raw = os.environ.get("APPLE_CALENDAR_INDEX_MAX_OCCURRENCES_PER_SERIES")
    if raw is not None and raw != "":
        return int(raw)
    val = _from_toml("index", "max_occurrences_per_series")
    if val is not None:
        return int(val)
    return 10000


def get_default_calendars() -> list[str] | None:
    """Return optional default calendar names or ids."""
    env = os.environ.get("APPLE_CALENDAR_DEFAULT_CALENDARS")
    if env is not None:
        calendars = [c.strip() for c in env.split(",") if c.strip()]
        return calendars or []
    val = _from_toml("defaults", "calendars")
    if val is not None:
        return list(val)
    return None
