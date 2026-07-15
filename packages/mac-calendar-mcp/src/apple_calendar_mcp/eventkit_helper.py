"""Stable macOS app identity for scheduled EventKit access."""

from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .jxa import EVENTKIT_CORE_JS

HELPER_BUNDLE_ID = "io.github.wagamama.mac-calendar-mcp.eventkit-helper"
HELPER_VERSION = "1"
DEFAULT_HELPER_APP_PATH = (
    Path.home() / "Applications" / "Mac Calendar MCP EventKit Helper.app"
)
HELPER_TIMEOUT_SECONDS = 35
OSASCRIPT_PATH = "/usr/bin/osascript"
OSACOMPILE_PATH = "/usr/bin/osacompile"
CODESIGN_PATH = "/usr/bin/codesign"
OPEN_PATH = "/usr/bin/open"

_HELPER_RUNNER_JS = r"""
function EventKitHelperEnsureAccess() {
  const eventType = EventKitCore.entityTypeEvent;
  const fullAccess = EventKitCore.authorizedStatus;
  const store = $.EKEventStore.alloc.init;
  const initial = Number(
    $.EKEventStore.authorizationStatusForEntityType(eventType)
  );
  if (initial === fullAccess) return store;
  if (initial === 1 || initial === 2) {
    throw new Error(
      `Calendar full access denied or restricted: status=${initial}`
    );
  }

  let completed = false;
  let granted = false;
  let errorMessage = "";
  const completion = (allowed, error) => {
    granted = Boolean(allowed);
    if (error) errorMessage = EventKitCore.string(error.localizedDescription);
    completed = true;
  };
  if (store.requestFullAccessToEventsWithCompletion) {
    store.requestFullAccessToEventsWithCompletion(completion);
  } else {
    store.requestAccessToEntityTypeCompletion(eventType, completion);
  }

  const deadline = Date.now() + 30000;
  while (!completed && Date.now() < deadline) {
    $.NSRunLoop.currentRunLoop.runUntilDate(
      $.NSDate.dateWithTimeIntervalSinceNow(0.05)
    );
  }
  const finalStatus = Number(
    $.EKEventStore.authorizationStatusForEntityType(eventType)
  );
  if (!completed) {
    throw new Error("Calendar full-access request timed out");
  }
  if (!granted || finalStatus !== fullAccess) {
    const suffix = errorMessage ? `: ${errorMessage}` : "";
    throw new Error(
      `Calendar full access was not granted: status=${finalStatus}${suffix}`
    );
  }
  return store;
}

function run(argv) {
  const store = EventKitHelperEnsureAccess();
  if (argv.length === 0) {
    const calendars = EventKitCore.array(
      store.calendarsForEntityType(EventKitCore.entityTypeEvent)
    );
    return JSON.stringify({status: 3, calendars: calendars.length});
  }
  if (argv.length !== 3) {
    throw new Error("EventKit helper requires start, end, and calendars JSON");
  }
  return JSON.stringify(
    EventKitCore.snapshot(argv[0], argv[1], JSON.parse(argv[2]))
  );
}
"""


class EventKitHelperError(RuntimeError):
    """Raised when the compiled EventKit helper cannot run safely."""


def _helper_script_path(helper_path: Path) -> Path:
    return helper_path / "Contents" / "Resources" / "Scripts" / "main.scpt"


def _helper_is_current(helper_path: Path) -> bool:
    info_path = helper_path / "Contents" / "Info.plist"
    if (
        not _helper_script_path(helper_path).is_file()
        or not info_path.is_file()
    ):
        return False
    try:
        with info_path.open("rb") as handle:
            info = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return False
    return (
        info.get("CFBundleIdentifier") == HELPER_BUNDLE_ID
        and info.get("CFBundleShortVersionString") == HELPER_VERSION
    )


def get_eventkit_helper_script(
    helper_path: Path = DEFAULT_HELPER_APP_PATH,
) -> Path | None:
    """Return the installed helper script when its identity is current."""
    if not _helper_is_current(helper_path):
        return None
    return _helper_script_path(helper_path)


def _run_command(command: list[str], *, timeout: int = 60) -> None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EventKitHelperError(
            f"EventKit helper command failed: {command[0]}: {exc}"
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise EventKitHelperError(
            f"EventKit helper command failed: {command[0]}: {detail}"
        )


def install_eventkit_helper(
    *,
    helper_path: Path = DEFAULT_HELPER_APP_PATH,
    force: bool = False,
) -> Path:
    """Compile and sign the stable EventKit helper app bundle."""
    if not force and _helper_is_current(helper_path):
        return _helper_script_path(helper_path)

    helper_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".mac-calendar-mcp-helper-",
        dir=helper_path.parent,
    ) as temp_dir:
        staging_root = Path(temp_dir)
        source_path = staging_root / "eventkit_helper.js"
        staged_app = staging_root / helper_path.name
        source_path.write_text(
            f"{EVENTKIT_CORE_JS}\n\n{_HELPER_RUNNER_JS}",
            encoding="utf-8",
        )
        _run_command(
            [
                OSACOMPILE_PATH,
                "-l",
                "JavaScript",
                "-o",
                str(staged_app),
                str(source_path),
            ]
        )

        info_path = staged_app / "Contents" / "Info.plist"
        try:
            with info_path.open("rb") as handle:
                info = plistlib.load(handle)
            info.update(
                {
                    "CFBundleIdentifier": HELPER_BUNDLE_ID,
                    "CFBundleName": "Mac Calendar MCP EventKit Helper",
                    "CFBundleShortVersionString": HELPER_VERSION,
                    "CFBundleVersion": HELPER_VERSION,
                    "LSUIElement": True,
                    "NSCalendarsFullAccessUsageDescription": (
                        "Read Apple Calendar events for the local Calendar "
                        "MCP index."
                    ),
                    "NSCalendarsUsageDescription": (
                        "Read Apple Calendar events for the local Calendar "
                        "MCP index."
                    ),
                }
            )
            with info_path.open("wb") as handle:
                plistlib.dump(info, handle)
        except (OSError, plistlib.InvalidFileException) as exc:
            raise EventKitHelperError(
                f"EventKit helper metadata update failed: {exc}"
            ) from exc

        _run_command(
            [
                CODESIGN_PATH,
                "--force",
                "--deep",
                "--sign",
                "-",
                str(staged_app),
            ]
        )
        if helper_path.exists():
            shutil.rmtree(helper_path)
        shutil.move(str(staged_app), str(helper_path))

    return _helper_script_path(helper_path)


def execute_eventkit_helper(
    *,
    script_path: Path,
    start: str | None = None,
    end: str | None = None,
    calendar_names_or_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Execute the compiled helper and parse its JSON response."""
    if not script_path.is_file():
        raise EventKitHelperError(
            f"EventKit helper script not found: {script_path}"
        )
    command = [OSASCRIPT_PATH, "-l", "JavaScript", str(script_path)]
    if start is not None or end is not None:
        if start is None or end is None:
            raise EventKitHelperError(
                "EventKit helper requires both start and end dates"
            )
        command.extend([start, end, json.dumps(calendar_names_or_ids or [])])
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=HELPER_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EventKitHelperError(
            f"EventKit helper execution failed: {exc}"
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise EventKitHelperError(f"EventKit helper execution failed: {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise EventKitHelperError(
            "EventKit helper returned invalid JSON"
        ) from exc


def authorize_eventkit_helper(
    *,
    helper_path: Path = DEFAULT_HELPER_APP_PATH,
    force: bool = False,
) -> dict[str, Any]:
    """Install the helper, request Calendar access, and verify it."""
    script_path = install_eventkit_helper(
        helper_path=helper_path,
        force=force,
    )
    _run_command([OPEN_PATH, "-W", "-n", str(helper_path)], timeout=90)
    return execute_eventkit_helper(script_path=script_path)
