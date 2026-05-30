# Apple Calendar MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate read-only `apple-calendar-mcp` package and CLI in this
repo, exposing six Calendar MCP read tools backed by a local SQLite + FTS5
archive index.

**Architecture:** Keep Apple Mail unchanged as the root package and add Apple
Calendar as a `uv` workspace member under `packages/apple-calendar-mcp`. Calendar
uses JXA only for Calendar.app reads, Python for config/index/search/recurrence,
and FastMCP for the server surface.

**Tech Stack:** Python 3.11+, FastMCP, Cyclopts, stdlib SQLite/FTS5, stdlib
`tomllib`, JXA via `osascript -l JavaScript`, pytest, ruff.

---

## File Structure

- Modify root `pyproject.toml`: add `uv` workspace membership, keep existing
  `apple-mail-mcp` metadata/script intact, and include Calendar source in
  pytest/ruff paths.
- Create `packages/apple-calendar-mcp/pyproject.toml`: standalone package
  metadata and script `apple-calendar-mcp = "apple_calendar_mcp:main"`.
- Create `packages/apple-calendar-mcp/src/apple_calendar_mcp/`: Calendar
  package with `__init__.py`, `cli.py`, `config.py`, `executor.py`,
  `builders.py`, `recurrence.py`, `server.py`, `py.typed`, `jxa/`, and `index/`.
- Create `packages/apple-calendar-mcp/tests/`: Calendar-specific tests colocated
  with the package so they can run via
  `uv run --package apple-calendar-mcp pytest packages/apple-calendar-mcp/tests`.
- Modify `CALENDAR.md`: replace the earlier root `src/apple_calendar_mcp/`
  layout with the workspace member path once the package scaffold exists.
- Leave `src/apple_mail_mcp/` behavior unchanged.

## Task 1: Workspace Packaging and Empty Calendar Package

**Files:**
- Modify: `pyproject.toml`
- Create: `packages/apple-calendar-mcp/pyproject.toml`
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/__init__.py`
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/py.typed`
- Create: `packages/apple-calendar-mcp/tests/__init__.py`
- Create: `packages/apple-calendar-mcp/tests/test_import.py`

- [ ] **Step 1: Write the failing import/script metadata test**

Create `packages/apple-calendar-mcp/tests/test_import.py`:

```python
from __future__ import annotations

import importlib.metadata


def test_calendar_package_imports():
    import apple_calendar_mcp

    assert apple_calendar_mcp.__all__ == ["main"]
    assert callable(apple_calendar_mcp.main)


def test_calendar_distribution_exposes_console_script():
    dist = importlib.metadata.distribution("apple-calendar-mcp")
    scripts = {
        entry.name: entry.value
        for entry in dist.entry_points
        if entry.group == "console_scripts"
    }

    assert scripts["apple-calendar-mcp"] == "apple_calendar_mcp:main"
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_import.py -v
```

Expected: FAIL because the `apple-calendar-mcp` workspace package does not
exist yet.

- [ ] **Step 3: Add workspace metadata**

Modify root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["packages/apple-calendar-mcp"]

[tool.pytest.ini_options]
testpaths = ["tests", "packages/apple-calendar-mcp/tests"]
pythonpath = ["src", "packages/apple-calendar-mcp/src"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

[tool.ruff]
target-version = "py311"
line-length = 80
src = ["src", "packages/apple-calendar-mcp/src"]
```

Keep existing root project metadata unchanged.

- [ ] **Step 4: Add Calendar package metadata**

Create `packages/apple-calendar-mcp/pyproject.toml`:

```toml
[project]
name = "apple-calendar-mcp"
version = "0.1.0"
description = "Read-only Apple Calendar MCP server with indexed archive search."
readme = "../../CALENDAR.md"
license = "GPL-3.0-or-later"
requires-python = ">=3.11"
authors = [
    { name = "Ioan-Mihail Dinu", email = "iodinu@icloud.com" },
]
keywords = [
    "apple-calendar",
    "calendar",
    "jxa",
    "macos",
    "mcp",
    "model-context-protocol",
    "search",
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: MacOS X",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: MacOS",
    "Programming Language :: JavaScript",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Office/Business :: Scheduling",
]
dependencies = [
    "fastmcp>=3.0.0b1,<4",
    "cyclopts>=4.10",
]

[project.scripts]
apple-calendar-mcp = "apple_calendar_mcp:main"

[tool.hatch.build.targets.wheel]
packages = ["src/apple_calendar_mcp"]

[tool.hatch.build.targets.sdist]
include = ["src/", "tests/"]

[tool.hatch.build]
artifacts = ["src/**/*.js", "src/**/py.typed"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 5: Add minimal package entrypoint**

Create `packages/apple-calendar-mcp/src/apple_calendar_mcp/__init__.py`:

```python
"""Apple Calendar MCP - read-only archive search for Apple Calendar."""

from .cli import main

__all__ = ["main"]
```

Create `packages/apple-calendar-mcp/src/apple_calendar_mcp/cli.py`:

```python
"""Command-line interface for apple-calendar-mcp."""

import cyclopts

app = cyclopts.App(
    name="mac-calendar-mcp",
    help="Read-only MCP server for Apple Calendar with indexed search.",
)


def main() -> None:
    """Run the Apple Calendar MCP CLI."""
    app()
```

Create an empty marker:

```bash
touch packages/apple-calendar-mcp/src/apple_calendar_mcp/py.typed
```

- [ ] **Step 6: Verify import/package test passes**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_import.py -v
```

Expected: PASS.

- [ ] **Step 7: Verify existing Mail import still works**

Run:

```bash
uv run python -c "from apple_mail_mcp import main; print(callable(main))"
```

Expected output includes:

```text
True
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml packages/apple-calendar-mcp
git commit -m "Add Apple Calendar MCP workspace package"
```

## Task 2: Calendar Config Loader

**Files:**
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/config.py`
- Create: `packages/apple-calendar-mcp/tests/test_config.py`

- [ ] **Step 1: Write config tests**

Create `packages/apple-calendar-mcp/tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Run failing config tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_config.py -v
```

Expected: FAIL because `apple_calendar_mcp.config` does not exist.

- [ ] **Step 3: Implement config loader**

Create `packages/apple-calendar-mcp/src/apple_calendar_mcp/config.py` with the
same layered model as Mail, but Calendar-specific keys:

```python
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
    global _cached_config
    _cached_config = _NOT_LOADED


def _load_config_file() -> dict:
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
            raise ConfigError(f"{CONFIG_FILE_PATH}: [{section}] must be a table.")
        for key, value in section_data.items():
            if key not in keys:
                raise ConfigError(
                    f"{CONFIG_FILE_PATH}: unknown key `[{section}] {key}`."
                )
            expected = keys[key]
            if int in expected and bool not in expected and isinstance(value, bool):
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
                            f"{CONFIG_FILE_PATH}: `[{section}] {key}[{i}]` "
                            "expected str."
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
    env = os.environ.get("APPLE_CALENDAR_INDEX_PATH")
    if env:
        return Path(env).expanduser()
    val = _from_toml("index", "path")
    if val:
        return Path(val).expanduser()
    return DEFAULT_INDEX_PATH


def get_index_staleness_hours() -> float:
    raw = os.environ.get("APPLE_CALENDAR_INDEX_STALENESS_HOURS")
    if raw is not None and raw != "":
        return float(raw)
    val = _from_toml("index", "staleness_hours")
    if val is not None:
        return float(val)
    return 24.0


def get_index_past_years() -> int | None:
    raw = os.environ.get("APPLE_CALENDAR_INDEX_PAST_YEARS")
    if raw is not None and raw != "":
        return int(raw)
    val = _from_toml("index", "past_years")
    if val is not None:
        return int(val)
    return None


def get_index_future_years() -> int:
    raw = os.environ.get("APPLE_CALENDAR_INDEX_FUTURE_YEARS")
    if raw is not None and raw != "":
        return int(raw)
    val = _from_toml("index", "future_years")
    if val is not None:
        return int(val)
    return 1


def get_index_max_occurrences_per_series() -> int:
    raw = os.environ.get(
        "APPLE_CALENDAR_INDEX_MAX_OCCURRENCES_PER_SERIES"
    )
    if raw is not None and raw != "":
        return int(raw)
    val = _from_toml("index", "max_occurrences_per_series")
    if val is not None:
        return int(val)
    return 10000


def get_default_calendars() -> list[str] | None:
    env = os.environ.get("APPLE_CALENDAR_DEFAULT_CALENDARS")
    if env is not None:
        calendars = [c.strip() for c in env.split(",") if c.strip()]
        return calendars or []
    val = _from_toml("defaults", "calendars")
    if val is not None:
        return list(val)
    return None
```

- [ ] **Step 4: Verify config tests pass**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp/config.py \
  packages/apple-calendar-mcp/tests/test_config.py
git commit -m "Add Calendar MCP configuration loader"
```

## Task 3: JXA Executor, Core Script, and Builders

**Files:**
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/executor.py`
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/builders.py`
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/jxa/__init__.py`
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/jxa/calendar_core.js`
- Create: `packages/apple-calendar-mcp/tests/test_executor.py`
- Create: `packages/apple-calendar-mcp/tests/test_builders.py`

- [ ] **Step 1: Write executor tests**

Create tests matching Mail's executor behavior:

```python
from unittest.mock import patch

import pytest

from apple_calendar_mcp.executor import (
    JXAError,
    execute_with_core,
    run_jxa,
)


@patch("subprocess.run")
def test_run_jxa_invokes_osascript(mock_run):
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = '{"ok": true}\n'
    mock_run.return_value.stderr = ""

    assert run_jxa("JSON.stringify({ok: true})") == '{"ok": true}'
    mock_run.assert_called_once()
    args = mock_run.call_args.args[0]
    assert args[:3] == ["osascript", "-l", "JavaScript"]


@patch("apple_calendar_mcp.executor.run_jxa")
def test_execute_with_core_parses_json(mock_run):
    mock_run.return_value = '{"calendars": []}'

    assert execute_with_core("JSON.stringify({calendars: []})") == {
        "calendars": []
    }


@patch("apple_calendar_mcp.executor.run_jxa")
def test_execute_with_core_invalid_json_raises(mock_run):
    mock_run.return_value = "debug output"

    with pytest.raises(JXAError, match="Failed to parse JXA output"):
        execute_with_core("script")
```

- [ ] **Step 2: Write builder tests**

Create `packages/apple-calendar-mcp/tests/test_builders.py`:

```python
from __future__ import annotations

import pytest

from apple_calendar_mcp.builders import CalendarQueryBuilder


def test_list_calendars_script_uses_calendar_core():
    js = CalendarQueryBuilder().list_calendars()

    assert "CalendarCore.listCalendars()" in js
    assert "JSON.stringify" in js


def test_events_in_range_serializes_inputs_safely():
    js = CalendarQueryBuilder().events_in_range(
        start="2026-01-01",
        end="2026-02-01",
        calendar_ids=['Work "Calendar"'],
    )

    assert '\\"Calendar\\"' in js
    assert "CalendarCore.eventsInRange" in js


def test_events_in_range_requires_start_and_end():
    with pytest.raises(ValueError, match="start and end"):
        CalendarQueryBuilder().events_in_range(start="", end="2026-01-01")
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_executor.py \
  packages/apple-calendar-mcp/tests/test_builders.py -v
```

Expected: FAIL because executor/builders/JXA files do not exist.

- [ ] **Step 4: Implement executor**

Create `executor.py` with the same behavior as Mail's executor and these exact
public names:

```python
from __future__ import annotations

import asyncio
import json
import subprocess
from typing import Any

from .jxa import CALENDAR_CORE_JS


class JXAError(Exception):
    """Raised when a JXA script fails to execute."""

    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr


def run_jxa(script: str, timeout: int = 120) -> str:
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise JXAError(f"JXA script failed: {result.stderr}", result.stderr)
    return result.stdout.strip()


def execute_with_core(script_body: str, timeout: int = 120) -> Any:
    output = run_jxa(f"{CALENDAR_CORE_JS}\n\n{script_body}", timeout)
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        preview = output[:500] + "..." if len(output) > 500 else output
        raise JXAError(
            f"Failed to parse JXA output as JSON: {e}\nOutput: {preview}",
            stderr=output,
        ) from e


async def run_jxa_async(script: str, timeout: int = 120) -> str:
    process = await asyncio.create_subprocess_exec(
        "osascript",
        "-l",
        "JavaScript",
        "-e",
        script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except TimeoutError:
        process.kill()
        await process.wait()
        raise
    if process.returncode != 0:
        stderr_text = stderr.decode("utf-8", errors="replace")
        raise JXAError(f"JXA script failed: {stderr_text}", stderr_text)
    return stdout.decode("utf-8", errors="replace").strip()


async def execute_with_core_async(
    script_body: str, timeout: int = 120
) -> Any:
    output = await run_jxa_async(
        f"{CALENDAR_CORE_JS}\n\n{script_body}", timeout
    )
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        preview = output[:500] + "..." if len(output) > 500 else output
        raise JXAError(
            f"Failed to parse JXA output as JSON: {e}\nOutput: {preview}",
            stderr=output,
        ) from e
```

- [ ] **Step 5: Implement JXA package and core**

Create `jxa/__init__.py`:

```python
"""JXA script resources for Apple Calendar automation."""

from pathlib import Path

CALENDAR_CORE_JS = (Path(__file__).parent / "calendar_core.js").read_text()

__all__ = ["CALENDAR_CORE_JS"]
```

Create `calendar_core.js` with these functions:

```javascript
const Calendar = Application("Calendar");
Calendar.includeStandardAdditions = true;

const CalendarCore = {
  formatDate(date) {
    if (!date) return null;
    try {
      return new Date(date).toISOString();
    } catch (e) {
      return null;
    }
  },

  parseDate(value) {
    if (!value) return null;
    return new Date(value);
  },

  today() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  },

  listCalendars() {
    const calendars = Calendar.calendars();
    const results = [];
    for (let cal of calendars) {
      results.push({
        id: cal.calendarIdentifier(),
        name: cal.name(),
        color: String(cal.color()),
        writable: cal.writable(),
        description: cal.description() || null
      });
    }
    return results;
  },

  calendarMatches(calendar, ids) {
    if (!ids || ids.length === 0) return true;
    const id = calendar.calendarIdentifier();
    const name = calendar.name();
    return ids.indexOf(id) !== -1 || ids.indexOf(name) !== -1;
  },

  eventToObject(calendar, event) {
    let attendees = [];
    try {
      attendees = event.attendees().map((att) => ({
        display_name: att.displayName() || null,
        email: att.email() || null,
        participation_status: String(att.participationStatus()) || null
      }));
    } catch (e) {}
    return {
      event_id: event.uid(),
      calendar_id: calendar.calendarIdentifier(),
      calendar_name: calendar.name(),
      title: event.summary() || "",
      location: event.location() || "",
      notes: event.description() || "",
      url: event.url() || "",
      status: String(event.status()) || "",
      all_day: event.alldayEvent(),
      start_date: CalendarCore.formatDate(event.startDate()),
      end_date: CalendarCore.formatDate(event.endDate()),
      modified_at: CalendarCore.formatDate(event.stampDate()),
      recurrence: event.recurrence() || "",
      excluded_dates: (event.excludedDates() || []).map(CalendarCore.formatDate),
      attendees: attendees
    };
  },

  eventsInRange(startValue, endValue, calendarIds) {
    const start = CalendarCore.parseDate(startValue);
    const end = CalendarCore.parseDate(endValue);
    const results = [];
    for (let calendar of Calendar.calendars()) {
      if (!CalendarCore.calendarMatches(calendar, calendarIds)) continue;
      const events = calendar.events.whose({
        _and: [
          { startDate: { _lt: end } },
          { endDate: { _gt: start } }
        ]
      })();
      for (let event of events) {
        results.push(CalendarCore.eventToObject(calendar, event));
      }
    }
    return results;
  }
};
```

- [ ] **Step 6: Implement builders**

Create `builders.py`:

```python
"""JXA script builders for Apple Calendar operations."""

from __future__ import annotations

import json


class CalendarQueryBuilder:
    """Build JXA snippets that use CalendarCore."""

    def list_calendars(self) -> str:
        return "JSON.stringify(CalendarCore.listCalendars());"

    def events_in_range(
        self,
        start: str,
        end: str,
        calendar_ids: list[str] | None = None,
    ) -> str:
        if not start or not end:
            raise ValueError("start and end are required")
        return (
            "JSON.stringify(CalendarCore.eventsInRange("
            f"{json.dumps(start)}, "
            f"{json.dumps(end)}, "
            f"{json.dumps(calendar_ids or [])}"
            "));"
        )
```

- [ ] **Step 7: Verify executor/builder tests pass**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_executor.py \
  packages/apple-calendar-mcp/tests/test_builders.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp/executor.py \
  packages/apple-calendar-mcp/src/apple_calendar_mcp/builders.py \
  packages/apple-calendar-mcp/src/apple_calendar_mcp/jxa \
  packages/apple-calendar-mcp/tests/test_executor.py \
  packages/apple-calendar-mcp/tests/test_builders.py
git commit -m "Add Calendar JXA execution layer"
```

## Task 4: Calendar Index Schema

**Files:**
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/index/__init__.py`
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/index/schema.py`
- Create: `packages/apple-calendar-mcp/tests/test_schema.py`
- Create/Modify: `packages/apple-calendar-mcp/tests/conftest.py`

- [ ] **Step 1: Write schema tests**

Create `packages/apple-calendar-mcp/tests/conftest.py`:

```python
from __future__ import annotations

import sqlite3

import pytest

from apple_calendar_mcp.index.schema import SCHEMA_VERSION, get_schema_sql


@pytest.fixture
def calendar_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(get_schema_sql())
    conn.execute(
        "INSERT INTO schema_version (version) VALUES (?)",
        (SCHEMA_VERSION,),
    )
    conn.commit()
    yield conn
    conn.close()
```

Create `packages/apple-calendar-mcp/tests/test_schema.py`:

```python
from __future__ import annotations

from apple_calendar_mcp.index.schema import (
    INSERT_ATTENDEE_SQL,
    INSERT_CALENDAR_SQL,
    INSERT_EVENT_SQL,
    INSERT_OCCURRENCE_SQL,
    INSERT_SEARCH_SQL,
)


def test_schema_creates_expected_tables(calendar_db):
    rows = calendar_db.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    ).fetchall()
    names = {row["name"] for row in rows}

    assert "calendars" in names
    assert "events" in names
    assert "occurrences" in names
    assert "attendees" in names
    assert "event_search" in names
    assert "events_fts" in names
    assert "failed_index_jobs" in names


def test_insert_rows_and_search(calendar_db):
    calendar_db.execute(
        INSERT_CALENDAR_SQL,
        ("cal-1", "Work", "#ff0000", 1, "Work calendar"),
    )
    calendar_db.execute(
        INSERT_EVENT_SQL,
        (
            "event-1",
            "cal-1",
            "Budget review",
            "Room 1",
            "Discuss budget",
            "https://example.test",
            "confirmed",
            0,
            "2026-05-01T10:00:00Z",
            "2026-05-01T11:00:00Z",
            "2026-04-01T00:00:00Z",
            "",
            0,
        ),
    )
    calendar_db.execute(
        INSERT_OCCURRENCE_SQL,
        ("event-1", "cal-1", "2026-05-01T10:00:00Z", "2026-05-01T11:00:00Z", 0),
    )
    calendar_db.execute(
        INSERT_ATTENDEE_SQL,
        ("event-1", "Alice", "alice@example.test", "accepted"),
    )
    cursor = calendar_db.execute(
        INSERT_SEARCH_SQL,
        (
            "event-1",
            "2026-05-01T10:00:00Z",
            "Budget review",
            "Room 1",
            "Discuss budget",
            "https://example.test",
            "Alice alice@example.test",
            "Work",
        ),
    )
    calendar_db.commit()

    rows = calendar_db.execute(
        "SELECT title FROM events_fts WHERE events_fts MATCH ?",
        ("budget",),
    ).fetchall()

    assert cursor.lastrowid is not None
    assert [row["title"] for row in rows] == ["Budget review"]
```

- [ ] **Step 2: Run failing schema tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_schema.py -v
```

Expected: FAIL because `apple_calendar_mcp.index.schema` does not exist.

- [ ] **Step 3: Implement schema**

Create `index/__init__.py`:

```python
"""Calendar index package."""

from .manager import IndexManager

__all__ = ["IndexManager"]
```

This import will fail until Task 7 adds `manager.py`; if that blocks schema
tests, temporarily import schema directly in tests and leave `__init__.py` with
`__all__: list[str] = []` until Task 7.

Create `index/schema.py` with:

```python
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

DEFAULT_PRAGMAS = {
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "busy_timeout": 5000,
    "foreign_keys": "ON",
}

INSERT_CALENDAR_SQL = """INSERT OR REPLACE INTO calendars
    (calendar_id, name, color, writable, description)
    VALUES (?, ?, ?, ?, ?)"""

INSERT_EVENT_SQL = """INSERT OR REPLACE INTO events
    (event_id, calendar_id, title, location, notes, url, status, all_day,
     start_date, end_date, modified_at, recurrence, unsupported_recurrence)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

INSERT_OCCURRENCE_SQL = """INSERT OR REPLACE INTO occurrences
    (event_id, calendar_id, occurrence_start, occurrence_end, is_detached)
    VALUES (?, ?, ?, ?, ?)"""

INSERT_ATTENDEE_SQL = """INSERT INTO attendees
    (event_id, display_name, email, participation_status)
    VALUES (?, ?, ?, ?)"""

INSERT_SEARCH_SQL = """INSERT INTO event_search
    (event_id, occurrence_start, title, location, notes, url, attendees,
     calendar_name)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""


def create_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for pragma, value in DEFAULT_PRAGMAS.items():
        conn.execute(f"PRAGMA {pragma}={value}")
    try:
        os.chmod(db_path, 0o600)
    except FileNotFoundError:
        pass
    return conn


def get_schema_sql() -> str:
    return """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS calendars (
    calendar_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,
    writable INTEGER,
    description TEXT,
    indexed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    calendar_id TEXT NOT NULL REFERENCES calendars(calendar_id),
    title TEXT,
    location TEXT,
    notes TEXT,
    url TEXT,
    status TEXT,
    all_day INTEGER DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    modified_at TEXT,
    recurrence TEXT,
    unsupported_recurrence INTEGER DEFAULT 0,
    indexed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS occurrences (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    calendar_id TEXT NOT NULL REFERENCES calendars(calendar_id),
    occurrence_start TEXT NOT NULL,
    occurrence_end TEXT NOT NULL,
    is_detached INTEGER DEFAULT 0,
    UNIQUE(event_id, occurrence_start)
);

CREATE INDEX IF NOT EXISTS idx_occurrences_range
    ON occurrences(occurrence_start, occurrence_end);
CREATE INDEX IF NOT EXISTS idx_occurrences_calendar
    ON occurrences(calendar_id, occurrence_start);

CREATE TABLE IF NOT EXISTS attendees (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    display_name TEXT,
    email TEXT,
    participation_status TEXT
);
CREATE INDEX IF NOT EXISTS idx_attendees_event ON attendees(event_id);

CREATE TABLE IF NOT EXISTS event_search (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    occurrence_start TEXT,
    title TEXT,
    location TEXT,
    notes TEXT,
    url TEXT,
    attendees TEXT,
    calendar_name TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
    title, location, notes, url, attendees, calendar_name,
    content='event_search',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS event_search_ai
AFTER INSERT ON event_search BEGIN
    INSERT INTO events_fts(rowid, title, location, notes, url, attendees,
                           calendar_name)
    VALUES (new.rowid, new.title, new.location, new.notes, new.url,
            new.attendees, new.calendar_name);
END;

CREATE TRIGGER IF NOT EXISTS event_search_ad
AFTER DELETE ON event_search BEGIN
    INSERT INTO events_fts(events_fts, rowid, title, location, notes, url,
                           attendees, calendar_name)
    VALUES('delete', old.rowid, old.title, old.location, old.notes, old.url,
           old.attendees, old.calendar_name);
END;

CREATE TRIGGER IF NOT EXISTS event_search_au
AFTER UPDATE ON event_search BEGIN
    INSERT INTO events_fts(events_fts, rowid, title, location, notes, url,
                           attendees, calendar_name)
    VALUES('delete', old.rowid, old.title, old.location, old.notes, old.url,
           old.attendees, old.calendar_name);
    INSERT INTO events_fts(rowid, title, location, notes, url, attendees,
                           calendar_name)
    VALUES (new.rowid, new.title, new.location, new.notes, new.url,
            new.attendees, new.calendar_name);
END;

CREATE TABLE IF NOT EXISTS failed_index_jobs (
    job_key TEXT PRIMARY KEY,
    calendar_id TEXT,
    event_id TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    first_seen TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now')),
    attempt_count INTEGER DEFAULT 1
);
"""
```

- [ ] **Step 4: Verify schema tests pass**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_schema.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp/index \
  packages/apple-calendar-mcp/tests/conftest.py \
  packages/apple-calendar-mcp/tests/test_schema.py
git commit -m "Add Calendar index schema"
```

## Task 5: Recurrence Expansion

**Files:**
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/recurrence.py`
- Create: `packages/apple-calendar-mcp/tests/test_recurrence.py`

- [ ] **Step 1: Write recurrence tests**

Create `tests/test_recurrence.py` with cases for non-recurring, daily interval,
weekly BYDAY, monthly, yearly, COUNT, UNTIL, excluded dates, cap, and unsupported
rules:

```python
from __future__ import annotations

from apple_calendar_mcp.recurrence import expand_occurrences


BASE_EVENT = {
    "event_id": "e1",
    "start_date": "2026-01-05T10:00:00Z",
    "end_date": "2026-01-05T11:00:00Z",
    "excluded_dates": [],
}


def test_non_recurring_event_returns_single_occurrence():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": ""},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert result.unsupported is False
    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z"
    ]


def test_daily_count():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=DAILY;COUNT=3"},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2026-01-06T10:00:00Z",
        "2026-01-07T10:00:00Z",
    ]


def test_weekly_byday():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=WEEKLY;COUNT=4;BYDAY=MO,WE"},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2026-01-07T10:00:00Z",
        "2026-01-12T10:00:00Z",
        "2026-01-14T10:00:00Z",
    ]


def test_excluded_dates_remove_occurrence():
    result = expand_occurrences(
        {
            **BASE_EVENT,
            "recurrence": "FREQ=DAILY;COUNT=3",
            "excluded_dates": ["2026-01-06T10:00:00Z"],
        },
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert [o.start for o in result.occurrences] == [
        "2026-01-05T10:00:00Z",
        "2026-01-07T10:00:00Z",
    ]


def test_unsupported_rule_is_reported():
    result = expand_occurrences(
        {**BASE_EVENT, "recurrence": "FREQ=WEEKLY;BYSETPOS=1"},
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        max_occurrences=100,
    )

    assert result.unsupported is True
    assert result.occurrences == []
    assert "BYSETPOS" in result.reason
```

- [ ] **Step 2: Run failing recurrence tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_recurrence.py -v
```

Expected: FAIL because `recurrence.py` does not exist.

- [ ] **Step 3: Implement recurrence parser**

Implement dataclasses:

```python
@dataclass(frozen=True)
class Occurrence:
    event_id: str
    start: str
    end: str


@dataclass(frozen=True)
class ExpansionResult:
    occurrences: list[Occurrence]
    unsupported: bool = False
    reason: str = ""
```

Implement:

```python
def expand_occurrences(
    event: dict,
    coverage_start: str,
    coverage_end: str,
    *,
    max_occurrences: int,
) -> ExpansionResult:
    """Return expanded occurrences or an unsupported result."""
```

Rules:
- Parse ISO strings by replacing trailing `Z` with `+00:00` and using
  `datetime.fromisoformat`.
- Return one occurrence for empty recurrence if it overlaps the coverage range.
- Support only keys `FREQ`, `INTERVAL`, `COUNT`, `UNTIL`, `BYDAY`.
- Support `FREQ=DAILY|WEEKLY|MONTHLY|YEARLY`.
- For weekly `BYDAY`, generate occurrences on listed weekdays while preserving
  the original event time.
- Treat unsupported keys or invalid values as `unsupported=True`.
- Apply `excluded_dates` by exact start datetime.
- Stop when `COUNT`, `UNTIL`, `coverage_end`, or `max_occurrences` is reached.

- [ ] **Step 4: Verify recurrence tests pass**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_recurrence.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp/recurrence.py \
  packages/apple-calendar-mcp/tests/test_recurrence.py
git commit -m "Add Calendar recurrence expansion"
```

## Task 6: Index Sync and Search Functions

**Files:**
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/index/sync.py`
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/index/search.py`
- Create: `packages/apple-calendar-mcp/tests/test_sync.py`
- Create: `packages/apple-calendar-mcp/tests/test_search.py`

- [ ] **Step 1: Write sync tests**

Create tests using an in-memory snapshot. Expected raw event shape is the JXA
output from `CalendarCore.eventToObject`.

```python
from __future__ import annotations

from apple_calendar_mcp.index.sync import sync_from_snapshot


def test_sync_from_snapshot_inserts_event_occurrence_attendee(calendar_db):
    snapshot = {
        "calendars": [
            {
                "id": "cal-1",
                "name": "Work",
                "color": "#ff0000",
                "writable": True,
                "description": "Work calendar",
            }
        ],
        "events": [
            {
                "event_id": "event-1",
                "calendar_id": "cal-1",
                "calendar_name": "Work",
                "title": "Budget review",
                "location": "Room 1",
                "notes": "Discuss budget",
                "url": "https://example.test",
                "status": "confirmed",
                "all_day": False,
                "start_date": "2026-05-01T10:00:00Z",
                "end_date": "2026-05-01T11:00:00Z",
                "modified_at": "2026-04-01T00:00:00Z",
                "recurrence": "",
                "excluded_dates": [],
                "attendees": [
                    {
                        "display_name": "Alice",
                        "email": "alice@example.test",
                        "participation_status": "accepted",
                    }
                ],
            }
        ],
    }

    result = sync_from_snapshot(
        calendar_db,
        snapshot,
        coverage_start="2026-01-01T00:00:00Z",
        coverage_end="2027-01-01T00:00:00Z",
        max_occurrences_per_series=100,
    )

    assert result.added == 1
    assert calendar_db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert calendar_db.execute(
        "SELECT COUNT(*) FROM occurrences"
    ).fetchone()[0] == 1
    assert calendar_db.execute(
        "SELECT COUNT(*) FROM attendees"
    ).fetchone()[0] == 1
```

- [ ] **Step 2: Write search tests**

Create `test_search.py`:

```python
from __future__ import annotations

from apple_calendar_mcp.index.search import search_events
from apple_calendar_mcp.index.sync import sync_from_snapshot


def _seed(calendar_db):
    sync_from_snapshot(
        calendar_db,
        {
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
                    "location": "Room 1",
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
        },
        coverage_start="2026-01-01T00:00:00Z",
        coverage_end="2027-01-01T00:00:00Z",
        max_occurrences_per_series=100,
    )


def test_search_events_finds_notes(calendar_db):
    _seed(calendar_db)

    results = search_events(calendar_db, "budget", limit=20, offset=0)

    assert len(results) == 1
    assert results[0]["event_id"] == "event-1"
    assert results[0]["title"] == "Budget review"


def test_search_events_date_filter(calendar_db):
    _seed(calendar_db)

    results = search_events(
        calendar_db,
        "budget",
        start="2026-06-01T00:00:00Z",
        limit=20,
        offset=0,
    )

    assert results == []


def test_search_events_field_filter(calendar_db):
    _seed(calendar_db)

    assert search_events(
        calendar_db, "Room", fields=["location"], limit=20, offset=0
    )[0]["event_id"] == "event-1"
    assert search_events(
        calendar_db, "Room", fields=["title"], limit=20, offset=0
    ) == []
```

- [ ] **Step 3: Run failing sync/search tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_sync.py \
  packages/apple-calendar-mcp/tests/test_search.py -v
```

Expected: FAIL because sync/search functions do not exist.

- [ ] **Step 4: Implement sync**

Create `index/sync.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Connection

from apple_calendar_mcp.recurrence import expand_occurrences

from .schema import (
    INSERT_ATTENDEE_SQL,
    INSERT_CALENDAR_SQL,
    INSERT_EVENT_SQL,
    INSERT_OCCURRENCE_SQL,
    INSERT_SEARCH_SQL,
)


@dataclass(frozen=True)
class SyncResult:
    added: int = 0
    updated: int = 0
    deleted: int = 0
    errors: int = 0


def _attendees_text(attendees: list[dict]) -> str:
    parts: list[str] = []
    for attendee in attendees:
        parts.append(attendee.get("display_name") or "")
        parts.append(attendee.get("email") or "")
    return " ".join(part for part in parts if part)


def sync_from_snapshot(
    conn: Connection,
    snapshot: dict,
    *,
    coverage_start: str,
    coverage_end: str,
    max_occurrences_per_series: int,
) -> SyncResult:
    conn.execute("DELETE FROM event_search")
    conn.execute("DELETE FROM attendees")
    conn.execute("DELETE FROM occurrences")
    conn.execute("DELETE FROM events")
    conn.execute("DELETE FROM calendars")

    calendars = snapshot.get("calendars", [])
    for calendar in calendars:
        conn.execute(
            INSERT_CALENDAR_SQL,
            (
                calendar["id"],
                calendar["name"],
                calendar.get("color"),
                1 if calendar.get("writable") else 0,
                calendar.get("description"),
            ),
        )

    added = 0
    errors = 0
    for event in snapshot.get("events", []):
        expansion = expand_occurrences(
            event,
            coverage_start,
            coverage_end,
            max_occurrences=max_occurrences_per_series,
        )
        unsupported = 1 if expansion.unsupported else 0
        conn.execute(
            INSERT_EVENT_SQL,
            (
                event["event_id"],
                event["calendar_id"],
                event.get("title", ""),
                event.get("location", ""),
                event.get("notes", ""),
                event.get("url", ""),
                event.get("status", ""),
                1 if event.get("all_day") else 0,
                event.get("start_date"),
                event.get("end_date"),
                event.get("modified_at"),
                event.get("recurrence", ""),
                unsupported,
            ),
        )
        for attendee in event.get("attendees", []):
            conn.execute(
                INSERT_ATTENDEE_SQL,
                (
                    event["event_id"],
                    attendee.get("display_name"),
                    attendee.get("email"),
                    attendee.get("participation_status"),
                ),
            )
        attendee_text = _attendees_text(event.get("attendees", []))
        for occurrence in expansion.occurrences:
            conn.execute(
                INSERT_OCCURRENCE_SQL,
                (
                    event["event_id"],
                    event["calendar_id"],
                    occurrence.start,
                    occurrence.end,
                    0,
                ),
            )
            conn.execute(
                INSERT_SEARCH_SQL,
                (
                    event["event_id"],
                    occurrence.start,
                    event.get("title", ""),
                    event.get("location", ""),
                    event.get("notes", ""),
                    event.get("url", ""),
                    attendee_text,
                    event.get("calendar_name", ""),
                ),
            )
            added += 1
        if expansion.unsupported:
            errors += 1
    conn.commit()
    return SyncResult(added=added, errors=errors)
```

- [ ] **Step 5: Implement search**

Create `index/search.py`:

```python
from __future__ import annotations

from sqlite3 import Connection


def _escape_fts(query: str) -> str:
    return " ".join(part.replace('"', '""') for part in query.split())


def _field_query(query: str, fields: list[str] | None) -> str:
    escaped = _escape_fts(query)
    if not fields or "all" in fields:
        return escaped
    allowed = {
        "title": "title",
        "location": "location",
        "notes": "notes",
        "attendees": "attendees",
        "calendar": "calendar_name",
    }
    columns = [allowed[field] for field in fields if field in allowed]
    if not columns:
        return escaped
    return " OR ".join(f"{column}:({escaped})" for column in columns)


def search_events(
    conn: Connection,
    query: str,
    *,
    start: str | None = None,
    end: str | None = None,
    calendar_ids: list[str] | None = None,
    fields: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    sql = """
    SELECT
        e.event_id,
        e.title,
        e.location,
        e.notes,
        e.url,
        e.status,
        e.all_day,
        o.occurrence_start,
        o.occurrence_end,
        c.calendar_id,
        c.name AS calendar_name,
        bm25(events_fts) AS score
    FROM events_fts
    JOIN event_search s ON s.rowid = events_fts.rowid
    JOIN events e ON e.event_id = s.event_id
    JOIN occurrences o
      ON o.event_id = s.event_id
     AND o.occurrence_start = s.occurrence_start
    JOIN calendars c ON c.calendar_id = e.calendar_id
    WHERE events_fts MATCH ?
    """
    params: list[object] = [_field_query(query, fields)]
    if start:
        sql += " AND o.occurrence_end >= ?"
        params.append(start)
    if end:
        sql += " AND o.occurrence_start <= ?"
        params.append(end)
    if calendar_ids:
        placeholders = ",".join("?" for _ in calendar_ids)
        sql += f" AND c.calendar_id IN ({placeholders})"
        params.extend(calendar_ids)
    sql += " ORDER BY score, o.occurrence_start LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
```

- [ ] **Step 6: Verify sync/search tests pass**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_sync.py \
  packages/apple-calendar-mcp/tests/test_search.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp/index/sync.py \
  packages/apple-calendar-mcp/src/apple_calendar_mcp/index/search.py \
  packages/apple-calendar-mcp/tests/test_sync.py \
  packages/apple-calendar-mcp/tests/test_search.py
git commit -m "Add Calendar index sync and search"
```

## Task 7: IndexManager

**Files:**
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/index/manager.py`
- Modify: `packages/apple-calendar-mcp/src/apple_calendar_mcp/index/__init__.py`
- Create: `packages/apple-calendar-mcp/tests/test_manager.py`

- [ ] **Step 1: Write manager tests**

Create tests for database creation, stats, has_index, search delegation, and
JXA snapshot fetch mocking:

```python
from __future__ import annotations

from unittest.mock import patch

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
```

- [ ] **Step 2: Run failing manager tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_manager.py -v
```

Expected: FAIL because `manager.py` does not exist.

- [ ] **Step 3: Implement manager**

Create `manager.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apple_calendar_mcp.config import (
    get_index_future_years,
    get_index_max_occurrences_per_series,
    get_index_path,
)
from apple_calendar_mcp.executor import execute_with_core

from .schema import SCHEMA_VERSION, create_connection, get_schema_sql
from .search import search_events
from .sync import sync_from_snapshot


@dataclass(frozen=True)
class IndexStats:
    calendar_count: int
    event_count: int
    occurrence_count: int
    unsupported_recurrence_count: int
    failed_jobs_count: int
    db_size_mb: float
    last_sync: datetime | None = None


class IndexManager:
    _instance: "IndexManager | None" = None

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_index_path()
        self._conn = None

    @classmethod
    def get_instance(cls) -> "IndexManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _connection(self):
        if self._conn is None:
            self._conn = create_connection(self.db_path)
            self._conn.executescript(get_schema_sql())
            self._conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            self._conn.commit()
        return self._conn

    def has_index(self) -> bool:
        return self.db_path.exists()

    def fetch_snapshot(self) -> dict:
        script = """
const calendars = CalendarCore.listCalendars();
const now = new Date();
const start = new Date(1970, 0, 1).toISOString();
const end = new Date(
  now.getFullYear() + %d, now.getMonth(), now.getDate()
).toISOString();
const events = CalendarCore.eventsInRange(start, end, []);
JSON.stringify({calendars: calendars, events: events});
""" % get_index_future_years()
        return execute_with_core(script)

    def build_from_jxa(self, progress_callback=None) -> int:
        snapshot = self.fetch_snapshot()
        now = datetime.now(UTC)
        coverage_start = "1970-01-01T00:00:00Z"
        coverage_end = (
            now + timedelta(days=365 * get_index_future_years())
        ).isoformat().replace("+00:00", "Z")
        result = sync_from_snapshot(
            self._connection(),
            snapshot,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            max_occurrences_per_series=get_index_max_occurrences_per_series(),
        )
        return result.added

    def sync_updates(self) -> int:
        return self.build_from_jxa()

    def search(self, query: str, **kwargs) -> list[dict]:
        return search_events(self._connection(), query, **kwargs)

    def events(
        self,
        *,
        start: str,
        end: str,
        calendar_ids: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        sql = """
        SELECT
            e.event_id,
            e.title,
            e.location,
            e.notes,
            e.url,
            e.status,
            e.all_day,
            o.occurrence_start,
            o.occurrence_end,
            c.calendar_id,
            c.name AS calendar_name
        FROM occurrences o
        JOIN events e ON e.event_id = o.event_id
        JOIN calendars c ON c.calendar_id = e.calendar_id
        WHERE o.occurrence_end >= ?
          AND o.occurrence_start <= ?
        """
        params: list[object] = [start, end]
        if calendar_ids:
            placeholders = ",".join("?" for _ in calendar_ids)
            sql += f" AND c.calendar_id IN ({placeholders})"
            params.extend(calendar_ids)
        sql += " ORDER BY o.occurrence_start LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return [dict(row) for row in self._connection().execute(sql, params)]

    def get_event(
        self,
        event_id: str,
        *,
        occurrence_start: str | None = None,
    ) -> dict:
        sql = """
        SELECT
            e.*,
            c.name AS calendar_name,
            o.occurrence_start,
            o.occurrence_end
        FROM events e
        JOIN calendars c ON c.calendar_id = e.calendar_id
        LEFT JOIN occurrences o ON o.event_id = e.event_id
        WHERE e.event_id = ?
        """
        params: list[object] = [event_id]
        if occurrence_start is not None:
            sql += " AND o.occurrence_start = ?"
            params.append(occurrence_start)
        sql += " ORDER BY o.occurrence_start LIMIT 1"
        row = self._connection().execute(sql, params).fetchone()
        if row is None:
            raise ValueError(f"Calendar event {event_id} not found.")
        result = dict(row)
        attendee_rows = self._connection().execute(
            """
            SELECT display_name, email, participation_status
            FROM attendees
            WHERE event_id = ?
            ORDER BY display_name, email
            """,
            (event_id,),
        ).fetchall()
        result["attendees"] = [dict(attendee) for attendee in attendee_rows]
        return result

    def get_agenda(
        self,
        *,
        start: str | None = None,
        days: int = 1,
        calendar_ids: list[str] | None = None,
    ) -> list[dict]:
        start_dt = (
            datetime.fromisoformat(start.replace("Z", "+00:00"))
            if start
            else datetime.now(UTC).replace(hour=0, minute=0, second=0,
                                           microsecond=0)
        )
        end_dt = start_dt + timedelta(days=days)
        return self.events(
            start=start_dt.isoformat().replace("+00:00", "Z"),
            end=end_dt.isoformat().replace("+00:00", "Z"),
            calendar_ids=calendar_ids,
            limit=500,
            offset=0,
        )

    def is_stale(self) -> bool:
        # v1 has no persisted sync_state timestamp yet; if an index exists,
        # the CLI does not auto-refresh it at startup.
        return False

    def get_stats(self) -> IndexStats:
        conn = self._connection()
        db_size_mb = (
            self.db_path.stat().st_size / 1024 / 1024
            if self.db_path.exists()
            else 0.0
        )
        return IndexStats(
            calendar_count=conn.execute(
                "SELECT COUNT(*) FROM calendars"
            ).fetchone()[0],
            event_count=conn.execute(
                "SELECT COUNT(*) FROM events"
            ).fetchone()[0],
            occurrence_count=conn.execute(
                "SELECT COUNT(*) FROM occurrences"
            ).fetchone()[0],
            unsupported_recurrence_count=conn.execute(
                "SELECT COUNT(*) FROM events WHERE unsupported_recurrence = 1"
            ).fetchone()[0],
            failed_jobs_count=conn.execute(
                "SELECT COUNT(*) FROM failed_index_jobs"
            ).fetchone()[0],
            db_size_mb=db_size_mb,
        )
```

Then update `index/__init__.py`:

```python
"""Calendar index package."""

from .manager import IndexManager

__all__ = ["IndexManager"]
```

- [ ] **Step 4: Verify manager tests pass**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_manager.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp/index/manager.py \
  packages/apple-calendar-mcp/src/apple_calendar_mcp/index/__init__.py \
  packages/apple-calendar-mcp/tests/test_manager.py
git commit -m "Add Calendar index manager"
```

## Task 8: MCP Server Tools and Resource

**Files:**
- Create: `packages/apple-calendar-mcp/src/apple_calendar_mcp/server.py`
- Create: `packages/apple-calendar-mcp/tests/test_server.py`

- [ ] **Step 1: Write server tests**

Create tests using mocks only:

```python
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch("apple_calendar_mcp.server.execute_with_core_async", new_callable=AsyncMock)
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
async def test_search_events_requires_index(monkeypatch):
    manager = MagicMock()
    manager.has_index.return_value = False
    monkeypatch.setattr(
        "apple_calendar_mcp.server._get_index_manager", lambda: manager
    )

    from apple_calendar_mcp.server import search_events

    with pytest.raises(ValueError, match="No calendar index"):
        await search_events("budget")
```

- [ ] **Step 2: Run failing server tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_server.py -v
```

Expected: FAIL because `server.py` does not exist.

- [ ] **Step 3: Implement server**

Create `server.py`:

```python
from __future__ import annotations

import asyncio
from typing import Literal, TypedDict

from fastmcp import FastMCP

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
        raise ValueError("No calendar index. Run 'mac-calendar-mcp index'.")
    results = manager.events(
        start=start,
        end=end,
        calendar_ids=calendar_ids,
        limit=limit,
        offset=offset,
    )
    return results


@mcp.tool
async def get_event(
    event_id: str,
    occurrence_start: str | None = None,
) -> dict:
    manager = _get_index_manager()
    if not manager.has_index():
        raise ValueError("No calendar index. Run 'mac-calendar-mcp index'.")
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
    fields: list[Literal[
        "all", "title", "location", "notes", "attendees", "calendar"
    ]] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
    manager = _get_index_manager()
    if not manager.has_index():
        raise ValueError("No calendar index. Run 'mac-calendar-mcp index'.")
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
        raise ValueError("No calendar index. Run 'mac-calendar-mcp index'.")
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
```

Before making this pass, add `IndexManager.get_event()` and
`IndexManager.get_agenda()` methods. They should query `events`, `occurrences`,
`calendars`, and `attendees`; return dicts; and raise `ValueError` when an event
is not found.

- [ ] **Step 4: Verify server tests pass**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_server.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp/server.py \
  packages/apple-calendar-mcp/src/apple_calendar_mcp/index/manager.py \
  packages/apple-calendar-mcp/tests/test_server.py
git commit -m "Add Calendar MCP read tools"
```

## Task 9: Calendar CLI

**Files:**
- Modify: `packages/apple-calendar-mcp/src/apple_calendar_mcp/cli.py`
- Create: `packages/apple-calendar-mcp/tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

Use `cyclopts` invocation or direct command-function calls with monkeypatched
managers:

```python
from __future__ import annotations

from unittest.mock import MagicMock

from apple_calendar_mcp import cli


def test_format_size():
    assert cli._format_size(0.5) == "512.0 KB"
    assert cli._format_size(2.0) == "2.0 MB"


def test_status_no_index_exits(monkeypatch, capsys):
    manager = MagicMock()
    manager.has_index.return_value = False
    monkeypatch.setattr(cli, "IndexManager", lambda: manager)

    try:
        cli.status()
    except SystemExit as exc:
        assert exc.code == 1

    captured = capsys.readouterr()
    assert "No index found" in captured.out
```

- [ ] **Step 2: Run failing CLI tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_cli.py -v
```

Expected: FAIL because CLI commands are not implemented.

- [ ] **Step 3: Implement CLI commands**

Mirror Mail's CLI shape, without watch/read-only flags. Implement these
functions with complete bodies:

```python
from __future__ import annotations

import json
import sys
import time

import cyclopts

from .config import get_index_path
from .index import IndexManager

app = cyclopts.App(
    name="mac-calendar-mcp",
    help="Read-only MCP server for Apple Calendar with indexed search.",
)

def _format_size(size_mb: float) -> str:
    if size_mb < 1:
        return f"{size_mb * 1024:.1f} KB"
    return f"{size_mb:.1f} MB"


def _format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def _print_json(value) -> None:
    print(json.dumps(value, indent=2, default=str))


def _run_serve() -> None:
    from .server import mcp

    manager = IndexManager.get_instance()
    if manager.has_index() and manager.is_stale():
        manager.sync_updates()
    mcp.run()

@app.default
def default_handler() -> None:
    _run_serve()


@app.command
def serve() -> None:
    _run_serve()


@app.command
def index(verbose: bool = False) -> None:
    manager = IndexManager()
    start = time.time()
    count = manager.build_from_jxa()
    print(f"Indexed {count:,} occurrences in {_format_time(time.time() - start)}")


@app.command
def status(verbose: bool = False) -> None:
    manager = IndexManager()
    if not manager.has_index():
        print("No index found.")
        print(f"Expected location: {get_index_path()}")
        sys.exit(1)
    stats = manager.get_stats()
    print("Apple Calendar MCP Index Status")
    print("=" * 40)
    print(f"Location:     {get_index_path()}")
    print(f"Calendars:    {stats.calendar_count:,}")
    print(f"Events:       {stats.event_count:,}")
    print(f"Occurrences:  {stats.occurrence_count:,}")
    print(f"Unsupported:  {stats.unsupported_recurrence_count:,}")
    print(f"Failed jobs:  {stats.failed_jobs_count:,}")
    print(f"Database:     {_format_size(stats.db_size_mb)}")


@app.command
def rebuild(verbose: bool = False) -> None:
    index(verbose=verbose)


@app.command
def search(query: str, limit: int = 20, offset: int = 0) -> None:
    manager = IndexManager()
    if not manager.has_index():
        print("No index found. Run 'mac-calendar-mcp index'.", file=sys.stderr)
        sys.exit(1)
    _print_json(manager.search(query, limit=limit, offset=offset))


@app.command
def events(start: str, end: str, limit: int = 50, offset: int = 0) -> None:
    manager = IndexManager()
    _print_json(manager.events(start=start, end=end, limit=limit, offset=offset))


@app.command
def calendars() -> None:
    from .builders import CalendarQueryBuilder
    from .executor import execute_with_core

    _print_json(execute_with_core(CalendarQueryBuilder().list_calendars()))


@app.command
def agenda(start: str | None = None, days: int = 1) -> None:
    manager = IndexManager()
    _print_json(manager.get_agenda(start=start, days=days))


def main() -> None:
    app()
```

- [ ] **Step 4: Verify CLI tests pass**

Run:

```bash
uv run --package apple-calendar-mcp pytest \
  packages/apple-calendar-mcp/tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 5: Verify CLI help works**

Run:

```bash
uv run --package apple-calendar-mcp apple-calendar-mcp --help
```

Expected: command help lists `serve`, `index`, `status`, `rebuild`, `search`,
`events`, `calendars`, and `agenda`.

- [ ] **Step 6: Commit**

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp/cli.py \
  packages/apple-calendar-mcp/tests/test_cli.py
git commit -m "Add Calendar MCP CLI"
```

## Task 10: Documentation Alignment

**Files:**
- Modify: `CALENDAR.md`

- [ ] **Step 1: Update `CALENDAR.md` package layout**

Replace the planned root path:

```text
src/apple_calendar_mcp/
```

with:

```text
packages/apple-calendar-mcp/src/apple_calendar_mcp/
```

Keep the same section structure as `MAIL.md`.

- [ ] **Step 2: Add concrete test commands to `CALENDAR.md`**

Ensure the smoke section includes:

```bash
uv run --package apple-calendar-mcp pytest packages/apple-calendar-mcp/tests
uv run --package apple-calendar-mcp apple-calendar-mcp --help
uv run --package apple-calendar-mcp python -c "from apple_calendar_mcp import main; print(callable(main))"
```

- [ ] **Step 3: Run markdown/privacy checks**

Run:

```bash
git diff --check
awk '/[ \t]$/ { print FILENAME ":" FNR ": trailing whitespace" }' \
  AGENTS.md CALENDAR.md
rg -n '(/Users/|github.com-personal|token|secret|password|api[_-]?key)' \
  AGENTS.md CALENDAR.md
```

Expected:
- `git diff --check` exits 0.
- `awk` prints nothing.
- `rg` prints only generic policy text if any.

- [ ] **Step 4: Commit**

```bash
git add CALENDAR.md
git commit -m "Document Calendar MCP implementation layout"
```

## Task 11: Full Verification

**Files:**
- No source edits unless verification exposes defects.

- [ ] **Step 1: Run Calendar package tests**

Run:

```bash
uv run --package apple-calendar-mcp pytest packages/apple-calendar-mcp/tests -v
```

Expected: all Calendar tests pass.

- [ ] **Step 2: Run existing Mail tests**

Run:

```bash
uv run pytest tests -v
```

Expected: all existing Mail tests pass. If macOS/Mail-specific tests fail due to
local permissions, capture the exact failures and do not claim full pass.

- [ ] **Step 3: Run ruff checks**

Run:

```bash
uv run ruff check src packages/apple-calendar-mcp/src packages/apple-calendar-mcp/tests
uv run ruff format --check src packages/apple-calendar-mcp/src packages/apple-calendar-mcp/tests
```

Expected: both commands exit 0.

- [ ] **Step 4: Run build checks**

Run:

```bash
uv build --package mac-mail-mcp
uv build --package mac-calendar-mcp
```

Expected: both builds complete and produce artifacts under `dist/`.

- [ ] **Step 5: Smoke both CLIs**

Run:

```bash
uv run --package mac-mail-mcp mac-mail-mcp --help
uv run --package mac-calendar-mcp mac-calendar-mcp --help
```

Expected: both commands print help and exit 0.

- [ ] **Step 6: Review final diff**

Run:

```bash
git status --short
git log --oneline --decorate -8
```

Expected: only intentional files are modified or committed. No unrelated files
are present.

- [ ] **Step 7: Request code review**

Use the available review workflow from `AGENTS.md`. If subagents are not
authorized, perform a local cross-reference review against:
- user request
- `AGENTS.md`
- `CALENDAR.md`
- this implementation plan
- final diff
- verification output

- [ ] **Step 8: Final stabilization commit**

If verification fixes were required, stage the Calendar package files and
commit them:

```bash
git add packages/apple-calendar-mcp/src/apple_calendar_mcp \
  packages/apple-calendar-mcp/tests
git commit -m "Stabilize Calendar MCP implementation"
```

Do not push unless the user explicitly chooses `Commit and push`.

## Assumptions and Defaults

- The repo will become a `uv` workspace. Existing Mail packaging remains intact.
- Calendar is a separate distribution named `apple-calendar-mcp`, not just a
  second module inside the `apple-mail-mcp` distribution.
- Calendar v1 is read-only: no create/update/delete/RSVP/UI-opening tools.
- Calendar v1 is JXA-only. No PyObjC/EventKit dependency is added.
- No new runtime dependency is required for recurrence; common recurrence rules
  are implemented in `recurrence.py`.
- Existing dev/test packages are sufficient: pytest, pytest-asyncio, ruff.
- Notes are indexed and returned by default.
- Recurring events are expanded into occurrences through the configured future
  window, defaulting to one year.
- Unsupported recurrence rules are reported in metadata/status rather than
  silently expanded incorrectly.
