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
