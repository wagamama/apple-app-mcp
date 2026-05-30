from __future__ import annotations

from pathlib import Path

import pytest

from apple_calendar_mcp import config
from apple_calendar_mcp.config import (
    CONFIG_SCHEMA_VERSION,
    ConfigError,
    _invalidate_config_cache,
    get_default_calendars,
    get_index_future_years,
    get_index_max_occurrences_per_series,
    get_index_past_years,
    get_index_path,
    get_index_staleness_hours,
)


@pytest.fixture
def config_file(monkeypatch, tmp_path):
    path = tmp_path / "config.toml"
    monkeypatch.setattr(config, "CONFIG_FILE_PATH", path)
    _invalidate_config_cache()
    yield path
    _invalidate_config_cache()


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for key in list(__import__("os").environ.keys()):
        if key.startswith("APPLE_CALENDAR_"):
            monkeypatch.delenv(key, raising=False)


def _write(path: Path, body: str) -> None:
    path.write_text(body)
    _invalidate_config_cache()


def test_defaults(config_file):
    assert get_index_path() == config.DEFAULT_INDEX_PATH
    assert get_index_staleness_hours() == 24.0
    assert get_index_past_years() is None
    assert get_index_future_years() == 1
    assert get_index_max_occurrences_per_series() == 10000
    assert get_default_calendars() is None


def test_file_values(config_file):
    _write(
        config_file,
        f"""
config_version = {CONFIG_SCHEMA_VERSION}
[defaults]
calendars = ["Work", "Personal"]
[index]
path = "~/calendar.db"
staleness_hours = 12
past_years = 5
future_years = 2
max_occurrences_per_series = 500
""",
    )

    assert get_default_calendars() == ["Work", "Personal"]
    assert get_index_path() == Path("~/calendar.db").expanduser()
    assert get_index_staleness_hours() == 12.0
    assert get_index_past_years() == 5
    assert get_index_future_years() == 2
    assert get_index_max_occurrences_per_series() == 500


def test_env_overrides_file(config_file, monkeypatch):
    _write(
        config_file,
        f"""
config_version = {CONFIG_SCHEMA_VERSION}
[index]
future_years = 2
""",
    )
    monkeypatch.setenv("APPLE_CALENDAR_INDEX_FUTURE_YEARS", "3")

    assert get_index_future_years() == 3


def test_csv_env_default_calendars(monkeypatch, config_file):
    monkeypatch.setenv("APPLE_CALENDAR_DEFAULT_CALENDARS", "Work,Personal")

    assert get_default_calendars() == ["Work", "Personal"]


def test_bad_type_raises(config_file):
    _write(
        config_file,
        f"""
config_version = {CONFIG_SCHEMA_VERSION}
[index]
future_years = true
""",
    )

    with pytest.raises(ConfigError, match="future_years"):
        get_index_future_years()


def test_negative_values_raise(config_file):
    _write(
        config_file,
        f"""
config_version = {CONFIG_SCHEMA_VERSION}
[index]
max_occurrences_per_series = -1
""",
    )

    with pytest.raises(ConfigError, match="max_occurrences_per_series"):
        get_index_max_occurrences_per_series()
