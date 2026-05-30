"""JXA script execution utilities for Apple Calendar."""

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
    """Execute a raw JXA script and return stripped stdout."""
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
    """Execute a CalendarCore JXA snippet and parse JSON output."""
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
    """Execute a raw JXA script asynchronously."""
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
    """Execute a CalendarCore JXA snippet asynchronously."""
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
