from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from apple_calendar_mcp import config
from apple_calendar_mcp.config import (
    CONFIG_SCHEMA_VERSION,
    CONFIG_TEMPLATE,
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


class TestInitTemplate:
    """The CONFIG_TEMPLATE that `mac-calendar-mcp init` writes."""

    def test_template_parses_as_valid_toml(self):
        tomllib.loads(CONFIG_TEMPLATE)

    def test_template_declares_current_schema_version(self):
        parsed = tomllib.loads(CONFIG_TEMPLATE)
        assert parsed.get("config_version") == CONFIG_SCHEMA_VERSION

    def test_template_passes_loader_validation(self, config_file):
        config_file.write_text(CONFIG_TEMPLATE)
        _invalidate_config_cache()

        get_default_calendars()

    def test_template_keys_all_commented_out(self):
        parsed = tomllib.loads(CONFIG_TEMPLATE)
        for section in ("defaults", "index"):
            section_data = parsed.get(section, {})
            assert section_data == {}, (
                f"Template's [{section}] section has live keys "
                f"{section_data}; all keys should be commented out."
            )


class TestInitCommand:
    """Behavior tests for `mac-calendar-mcp init`."""

    def test_writes_template_to_config_path(self, config_file):
        from apple_calendar_mcp.cli import cli_init

        cli_init()
        assert config_file.exists()
        assert config_file.read_text() == CONFIG_TEMPLATE

    def test_sets_owner_only_permissions(self, config_file):
        from apple_calendar_mcp.cli import cli_init

        cli_init()
        mode = config_file.stat().st_mode & 0o777
        assert mode == 0o600, f"expected 0o600, got {oct(mode)}"

    def test_creates_parent_directory_if_missing(self, monkeypatch, tmp_path):
        new_dir = tmp_path / "fresh" / "subdir"
        target = new_dir / "config.toml"
        monkeypatch.setattr(config, "CONFIG_FILE_PATH", target)
        from apple_calendar_mcp.cli import cli_init

        cli_init()
        assert target.exists()
        assert new_dir.is_dir()

    def test_refuses_to_overwrite_existing_file(self, config_file):
        config_file.write_text("# user-edited config")
        from apple_calendar_mcp.cli import cli_init

        with pytest.raises(SystemExit) as exc:
            cli_init(force=False)
        assert exc.value.code == 1
        assert config_file.read_text() == "# user-edited config"

    def test_force_overwrites_existing_file(self, config_file):
        config_file.write_text("# user-edited config")
        from apple_calendar_mcp.cli import cli_init

        cli_init(force=True)
        assert config_file.read_text() == CONFIG_TEMPLATE
