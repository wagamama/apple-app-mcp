from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from apple_calendar_mcp.executor import (
    JXAError,
    execute_with_core,
    execute_with_core_async,
    run_jxa,
    run_jxa_async,
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


@patch("subprocess.run")
def test_run_jxa_nonzero_exit_raises_jxa_error(mock_run):
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = "execution error"

    with pytest.raises(JXAError, match="JXA script failed") as exc:
        run_jxa("bad script")

    assert exc.value.stderr == "execution error"


class _FakeAsyncProcess:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.kill = AsyncMock()
        self.wait = AsyncMock()

    async def communicate(self):
        return self._stdout, self._stderr


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_run_jxa_async_nonzero_exit_raises_jxa_error(mock_exec):
    mock_exec.return_value = _FakeAsyncProcess(
        returncode=1,
        stdout=b"",
        stderr=b"async execution error",
    )

    with pytest.raises(JXAError, match="JXA script failed") as exc:
        await run_jxa_async("bad script")

    assert exc.value.stderr == "async execution error"


@pytest.mark.asyncio
@patch("apple_calendar_mcp.executor.run_jxa_async")
async def test_execute_with_core_async_invalid_json_raises(mock_run):
    mock_run.return_value = "debug output"

    with pytest.raises(JXAError, match="Failed to parse JXA output"):
        await execute_with_core_async("script")
