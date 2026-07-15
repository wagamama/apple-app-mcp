"""Stable macOS app identity for scheduled EventKit access."""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from .jxa import EVENTKIT_CORE_JS

HELPER_BUNDLE_ID = "io.github.wagamama.mac-calendar-mcp.eventkit-helper"
HELPER_VERSION = "2"
HELPER_SOURCE_HASH_KEY = "MacCalendarMCPSourceSHA256"
DEFAULT_HELPER_APP_PATH = (
    Path.home() / "Applications" / "Mac Calendar MCP EventKit Helper.app"
)
HELPER_TIMEOUT_SECONDS = 35
OSACOMPILE_PATH = "/usr/bin/osacompile"
OSADECOMPILE_PATH = "/usr/bin/osadecompile"
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
  if (
    initial === EventKitCore.restrictedStatus ||
    initial === EventKitCore.deniedStatus
  ) {
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

function EventKitHelperWriteOutput(path, value) {
  const data = $(JSON.stringify(value)).dataUsingEncoding(
    $.NSUTF8StringEncoding
  );
  if (!data.writeToFileAtomically($(path), true)) {
    throw new Error("EventKit helper could not write its response");
  }
}

function EventKitHelperArguments() {
  return EventKitCore.array($.NSProcessInfo.processInfo.arguments)
    .map(EventKitCore.string)
    .slice(1);
}

function run() {
  const argv = EventKitHelperArguments();
  if (argv.length === 0) return;
  const outputPath = argv.shift();
  try {
    const command = argv[0];
    const isAuthorize = command === "authorize" && argv.length === 1;
    const isSnapshot = command === "snapshot" && argv.length === 4;
    if (!isAuthorize && !isSnapshot) {
      throw new Error("EventKit helper received an invalid command");
    }
    let calendars = [];
    if (isSnapshot) {
      calendars = JSON.parse(argv[3]);
      if (!Array.isArray(calendars)) {
        throw new Error("EventKit helper calendars must be a JSON array");
      }
    }

    const store = EventKitHelperEnsureAccess();
    let result;
    if (isAuthorize) {
      const availableCalendars = EventKitCore.array(
        store.calendarsForEntityType(EventKitCore.entityTypeEvent)
      );
      result = {
        status: EventKitCore.authorizedStatus,
        calendars: availableCalendars.length
      };
    } else {
      result = EventKitCore.snapshot(argv[1], argv[2], calendars);
    }
    EventKitHelperWriteOutput(outputPath, {ok: true, result: result});
  } catch (error) {
    const message = error && error.message ? error.message : String(error);
    EventKitHelperWriteOutput(outputPath, {
      ok: false,
      error: String(message)
    });
  }
}
"""


class EventKitHelperError(RuntimeError):
    """Raised when the compiled EventKit helper cannot run safely."""


def _helper_source_sha256() -> str:
    return hashlib.sha256(_helper_source().encode()).hexdigest()


def _helper_source() -> str:
    return f"{EVENTKIT_CORE_JS}\n\n{_HELPER_RUNNER_JS}"


def _helper_script_path(helper_path: Path) -> Path:
    return helper_path / "Contents" / "Resources" / "Scripts" / "main.scpt"


def _helper_executable_path(helper_path: Path) -> Path:
    return helper_path / "Contents" / "MacOS" / "applet"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plist_sha256(info: dict[str, Any]) -> str:
    serialized = plistlib.dumps(
        info,
        fmt=plistlib.FMT_BINARY,
        sort_keys=True,
    )
    return hashlib.sha256(serialized).hexdigest()


def _helper_is_current(helper_path: Path) -> bool:
    info_path = helper_path / "Contents" / "Info.plist"
    if (
        not _helper_script_path(helper_path).is_file()
        or not _helper_executable_path(helper_path).is_file()
        or not info_path.is_file()
    ):
        return False
    try:
        with info_path.open("rb") as handle:
            info = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return False
    metadata_is_current = (
        info.get("CFBundleIdentifier") == HELPER_BUNDLE_ID
        and info.get("CFBundleShortVersionString") == HELPER_VERSION
        and info.get(HELPER_SOURCE_HASH_KEY) == _helper_source_sha256()
    )
    if not metadata_is_current:
        return False
    try:
        result = subprocess.run(
            [
                CODESIGN_PATH,
                "--verify",
                "--deep",
                "--strict",
                str(helper_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    try:
        result = subprocess.run(
            [OSADECOMPILE_PATH, str(_helper_script_path(helper_path))],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if (
        result.returncode != 0
        or result.stdout.strip() != _helper_source().strip()
    ):
        return False
    try:
        expected_executable, expected_metadata = _expected_helper_identity()
        return (
            _file_sha256(_helper_executable_path(helper_path))
            == expected_executable
            and _plist_sha256(info) == expected_metadata
        )
    except (OSError, EventKitHelperError):
        return False


def get_eventkit_helper(
    helper_path: Path = DEFAULT_HELPER_APP_PATH,
) -> Path | None:
    """Return the installed helper app when its identity is current."""
    if not _helper_is_current(helper_path):
        return None
    return helper_path


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


def _build_helper_app(staging_root: Path, app_name: str) -> Path:
    source_path = staging_root / "eventkit_helper.js"
    staged_app = staging_root / app_name
    source_path.write_text(
        _helper_source(),
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
                HELPER_SOURCE_HASH_KEY: _helper_source_sha256(),
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
    return staged_app


@lru_cache(maxsize=1)
def _expected_helper_identity() -> tuple[str, str]:
    with tempfile.TemporaryDirectory(
        prefix=".mac-calendar-mcp-reference-"
    ) as temp_dir:
        reference_app = _build_helper_app(
            Path(temp_dir),
            DEFAULT_HELPER_APP_PATH.name,
        )
        info_path = reference_app / "Contents" / "Info.plist"
        try:
            with info_path.open("rb") as handle:
                info = plistlib.load(handle)
        except (OSError, plistlib.InvalidFileException) as exc:
            raise EventKitHelperError(
                f"EventKit helper reference metadata failed: {exc}"
            ) from exc
        return (
            _file_sha256(_helper_executable_path(reference_app)),
            _plist_sha256(info),
        )


def install_eventkit_helper(
    *,
    helper_path: Path = DEFAULT_HELPER_APP_PATH,
    force: bool = False,
) -> Path:
    """Compile and sign the stable EventKit helper app bundle."""
    if not force and _helper_is_current(helper_path):
        return helper_path

    helper_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".mac-calendar-mcp-helper-",
        dir=helper_path.parent,
    ) as temp_dir:
        staging_root = Path(temp_dir)
        staged_app = _build_helper_app(
            staging_root,
            helper_path.name,
        )
        backup_path = staging_root / "previous-helper.app"
        try:
            if helper_path.exists():
                os.replace(helper_path, backup_path)
            os.replace(staged_app, helper_path)
        except OSError as exc:
            restore_error: OSError | None = None
            if backup_path.exists():
                try:
                    os.replace(backup_path, helper_path)
                except OSError as restore_exc:
                    restore_error = restore_exc
            suffix = (
                f"; previous helper restore failed: {restore_error}"
                if restore_error is not None
                else ""
            )
            raise EventKitHelperError(
                f"EventKit helper installation failed: {exc}{suffix}"
            ) from exc
        if backup_path.exists():
            shutil.rmtree(backup_path, ignore_errors=True)

    return helper_path


def execute_eventkit_helper(
    *,
    helper_path: Path,
    start: str | None = None,
    end: str | None = None,
    calendar_names_or_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Execute EventKit inside the authorized app and parse its response."""
    if not _helper_executable_path(helper_path).is_file():
        raise EventKitHelperError(
            f"EventKit helper executable not found: {helper_path}"
        )
    helper_arguments = ["authorize"]
    if start is not None or end is not None:
        if start is None or end is None:
            raise EventKitHelperError(
                "EventKit helper requires both start and end dates"
            )
        helper_arguments = [
            "snapshot",
            start,
            end,
            json.dumps(calendar_names_or_ids or []),
        ]

    with tempfile.TemporaryDirectory(
        prefix=".mac-calendar-mcp-result-"
    ) as temp_dir:
        output_path = Path(temp_dir) / "response.json"
        output_path.touch(mode=0o600)
        command = [
            OPEN_PATH,
            "-W",
            "-n",
            "-g",
            "-a",
            str(helper_path),
            "--args",
            str(output_path),
            *helper_arguments,
        ]
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
        output = output_path.read_text(encoding="utf-8")
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise EventKitHelperError(
                f"EventKit helper execution failed: {detail}"
            )

    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise EventKitHelperError(
            "EventKit helper returned invalid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise EventKitHelperError(
            "EventKit helper returned an invalid response"
        )
    if payload.get("ok") is not True:
        detail = payload.get("error") or "unknown helper failure"
        raise EventKitHelperError(f"EventKit helper failed: {detail}")
    helper_result = payload.get("result")
    if not isinstance(helper_result, dict):
        raise EventKitHelperError("EventKit helper returned an invalid result")
    return helper_result


def authorize_eventkit_helper(
    *,
    helper_path: Path = DEFAULT_HELPER_APP_PATH,
    force: bool = False,
) -> dict[str, Any]:
    """Install the helper, request Calendar access, and verify it."""
    install_eventkit_helper(
        helper_path=helper_path,
        force=force,
    )
    return execute_eventkit_helper(helper_path=helper_path)
