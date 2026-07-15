from __future__ import annotations

import json
import plistlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apple_calendar_mcp.eventkit_helper import (
    CODESIGN_PATH,
    HELPER_BUNDLE_ID,
    HELPER_VERSION,
    OPEN_PATH,
    OSACOMPILE_PATH,
    OSASCRIPT_PATH,
    EventKitHelperError,
    authorize_eventkit_helper,
    execute_eventkit_helper,
    install_eventkit_helper,
)


def _fake_compile(command, **kwargs):
    if command[0] == OSACOMPILE_PATH:
        app_path = Path(command[command.index("-o") + 1])
        info_path = app_path / "Contents" / "Info.plist"
        script_path = app_path / "Contents" / "Resources" / "Scripts"
        info_path.parent.mkdir(parents=True)
        script_path.mkdir(parents=True)
        with info_path.open("wb") as handle:
            plistlib.dump({"CFBundleExecutable": "applet"}, handle)
        (script_path / "main.scpt").write_bytes(b"compiled")
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_install_eventkit_helper_builds_stable_app_identity(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ) as run:
        script_path = install_eventkit_helper(helper_path=helper_path)

    assert script_path == (
        helper_path / "Contents" / "Resources" / "Scripts" / "main.scpt"
    )
    with (helper_path / "Contents" / "Info.plist").open("rb") as handle:
        info = plistlib.load(handle)
    assert info["CFBundleIdentifier"] == HELPER_BUNDLE_ID
    assert info["CFBundleShortVersionString"] == HELPER_VERSION
    assert info["LSUIElement"] is True
    assert info["NSCalendarsFullAccessUsageDescription"]
    assert info["NSCalendarsUsageDescription"]
    commands = [call.args[0] for call in run.call_args_list]
    assert commands[0][0] == OSACOMPILE_PATH
    assert commands[-1][:4] == [
        CODESIGN_PATH,
        "--force",
        "--deep",
        "--sign",
    ]


def test_install_eventkit_helper_reuses_current_bundle(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    info_path = helper_path / "Contents" / "Info.plist"
    script_path = helper_path / "Contents" / "Resources" / "Scripts"
    info_path.parent.mkdir(parents=True)
    script_path.mkdir(parents=True)
    with info_path.open("wb") as handle:
        plistlib.dump(
            {
                "CFBundleIdentifier": HELPER_BUNDLE_ID,
                "CFBundleShortVersionString": HELPER_VERSION,
            },
            handle,
        )
    (script_path / "main.scpt").write_bytes(b"compiled")

    with patch("apple_calendar_mcp.eventkit_helper.subprocess.run") as run:
        result = install_eventkit_helper(helper_path=helper_path)

    assert result == script_path / "main.scpt"
    run.assert_not_called()


def test_execute_eventkit_helper_passes_values_as_arguments(tmp_path):
    script_path = tmp_path / "main.scpt"
    script_path.write_bytes(b"compiled")
    calendar_name = 'Work "); throw new Error("injected") //'
    expected = {
        "source": "eventkit",
        "calendars": [],
        "events": [],
        "failed_jobs": [],
    }

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        return_value=SimpleNamespace(
            returncode=0,
            stdout=json.dumps(expected),
            stderr="",
        ),
    ) as run:
        result = execute_eventkit_helper(
            script_path=script_path,
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
            calendar_names_or_ids=[calendar_name],
        )

    assert result == expected
    command = run.call_args.args[0]
    assert command[:4] == [
        OSASCRIPT_PATH,
        "-l",
        "JavaScript",
        str(script_path),
    ]
    assert command[-1] == json.dumps([calendar_name])


def test_execute_eventkit_helper_reports_process_failure(tmp_path):
    script_path = tmp_path / "main.scpt"
    script_path.write_bytes(b"compiled")

    with (
        patch(
            "apple_calendar_mcp.eventkit_helper.subprocess.run",
            return_value=SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="Calendar access denied",
            ),
        ),
        pytest.raises(EventKitHelperError, match="Calendar access denied"),
    ):
        execute_eventkit_helper(
            script_path=script_path,
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
            calendar_names_or_ids=None,
        )


def test_authorize_installs_opens_and_verifies_helper(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    script_path = helper_path / "Contents" / "Resources" / "Scripts"
    script_path.mkdir(parents=True)
    compiled_script = script_path / "main.scpt"
    compiled_script.write_bytes(b"compiled")

    with (
        patch(
            "apple_calendar_mcp.eventkit_helper.install_eventkit_helper",
            return_value=compiled_script,
        ) as install,
        patch(
            "apple_calendar_mcp.eventkit_helper.subprocess.run",
            return_value=SimpleNamespace(
                returncode=0,
                stdout="",
                stderr="",
            ),
        ) as run,
        patch(
            "apple_calendar_mcp.eventkit_helper.execute_eventkit_helper",
            return_value={"status": 3, "calendars": 12},
        ) as execute,
    ):
        result = authorize_eventkit_helper(helper_path=helper_path)

    assert result == {"status": 3, "calendars": 12}
    install.assert_called_once_with(helper_path=helper_path, force=False)
    run.assert_called_once()
    assert run.call_args.args[0] == [OPEN_PATH, "-W", "-n", str(helper_path)]
    execute.assert_called_once_with(script_path=compiled_script)
