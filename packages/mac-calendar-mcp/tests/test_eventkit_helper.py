from __future__ import annotations

import json
import os
import plistlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apple_calendar_mcp import eventkit_helper as eventkit_helper_module
from apple_calendar_mcp.eventkit_helper import (
    CODESIGN_PATH,
    HELPER_BUNDLE_ID,
    HELPER_VERSION,
    OPEN_PATH,
    OSACOMPILE_PATH,
    EventKitHelperError,
    authorize_eventkit_helper,
    execute_eventkit_helper,
    get_eventkit_helper,
    install_eventkit_helper,
)


def _fake_compile(command, **kwargs):
    if command[0] == OSACOMPILE_PATH:
        app_path = Path(command[command.index("-o") + 1])
        info_path = app_path / "Contents" / "Info.plist"
        script_path = app_path / "Contents" / "Resources" / "Scripts"
        executable_path = app_path / "Contents" / "MacOS"
        info_path.parent.mkdir(parents=True)
        script_path.mkdir(parents=True)
        executable_path.mkdir(parents=True)
        with info_path.open("wb") as handle:
            plistlib.dump({"CFBundleExecutable": "applet"}, handle)
        (script_path / "main.scpt").write_bytes(b"compiled")
        (executable_path / "applet").write_bytes(b"applet")
    if command[0] == eventkit_helper_module.OSADECOMPILE_PATH:
        return SimpleNamespace(
            returncode=0,
            stdout=eventkit_helper_module._helper_source(),
            stderr="",
        )
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_install_eventkit_helper_builds_stable_app_identity(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ) as run:
        installed_helper = install_eventkit_helper(helper_path=helper_path)

    assert installed_helper == helper_path
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
    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        install_eventkit_helper(helper_path=helper_path)

    eventkit_helper_module._expected_helper_identity.cache_clear()
    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ) as run:
        result = install_eventkit_helper(helper_path=helper_path)

    assert result == helper_path
    assert run.call_count == 4
    assert run.call_args_list[0].args[0][:4] == [
        CODESIGN_PATH,
        "--verify",
        "--deep",
        "--strict",
    ]
    assert run.call_args_list[1].args[0][0] == (
        eventkit_helper_module.OSADECOMPILE_PATH
    )
    assert run.call_args_list[2].args[0][0] == OSACOMPILE_PATH
    assert run.call_args_list[3].args[0][:4] == [
        CODESIGN_PATH,
        "--force",
        "--deep",
        "--sign",
    ]


def test_get_eventkit_helper_rejects_invalid_signature(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        install_eventkit_helper(helper_path=helper_path)

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        return_value=SimpleNamespace(returncode=1, stdout="", stderr="bad"),
    ):
        assert get_eventkit_helper(helper_path) is None


def test_get_eventkit_helper_rejects_stale_source(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        install_eventkit_helper(helper_path=helper_path)

    info_path = helper_path / "Contents" / "Info.plist"
    with info_path.open("rb") as handle:
        info = plistlib.load(handle)
    info["MacCalendarMCPSourceSHA256"] = "stale"
    with info_path.open("wb") as handle:
        plistlib.dump(info, handle)

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
    ):
        assert get_eventkit_helper(helper_path) is None


def test_get_eventkit_helper_rejects_modified_compiled_script(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        install_eventkit_helper(helper_path=helper_path)

    def verify_modified_helper(command, **kwargs):
        if command[0] == CODESIGN_PATH:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if command[0] == "/usr/bin/osadecompile":
            return SimpleNamespace(
                returncode=0,
                stdout="function run() { malicious(); }",
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=verify_modified_helper,
    ):
        assert get_eventkit_helper(helper_path) is None


def test_get_eventkit_helper_rejects_modified_executable(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        install_eventkit_helper(helper_path=helper_path)

    executable = helper_path / "Contents" / "MacOS" / "applet"
    executable.write_bytes(b"modified executable")

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        assert get_eventkit_helper(helper_path) is None


def test_get_eventkit_helper_rejects_redirected_executable(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        install_eventkit_helper(helper_path=helper_path)

    executable = helper_path / "Contents" / "MacOS" / "malicious"
    executable.write_bytes(b"malicious executable")
    info_path = helper_path / "Contents" / "Info.plist"
    with info_path.open("rb") as handle:
        info = plistlib.load(handle)
    info["CFBundleExecutable"] = "malicious"
    with info_path.open("wb") as handle:
        plistlib.dump(info, handle)

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        assert get_eventkit_helper(helper_path) is None


def test_install_eventkit_helper_restores_previous_bundle_on_failure(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=_fake_compile,
    ):
        install_eventkit_helper(helper_path=helper_path)
    marker = helper_path / "previous-install"
    marker.write_text("healthy", encoding="utf-8")

    real_replace = os.replace
    replace_calls = 0

    def fail_promotion(source, destination):
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("simulated promotion failure")
        return real_replace(source, destination)

    with (
        patch(
            "apple_calendar_mcp.eventkit_helper.subprocess.run",
            side_effect=_fake_compile,
        ),
        patch(
            "apple_calendar_mcp.eventkit_helper.os.replace",
            side_effect=fail_promotion,
        ),
        pytest.raises(EventKitHelperError, match="installation failed"),
    ):
        install_eventkit_helper(helper_path=helper_path, force=True)

    assert marker.read_text(encoding="utf-8") == "healthy"


def test_execute_eventkit_helper_runs_authorized_app_identity(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    executable = helper_path / "Contents" / "MacOS" / "applet"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"applet")
    calendar_name = 'Work "); throw new Error("injected") //'
    expected = {
        "source": "eventkit",
        "calendars": [],
        "events": [],
        "failed_jobs": [],
    }

    def run_helper(command, **kwargs):
        assert command[:4] == [OPEN_PATH, "-W", "-n", "-g"]
        output_path = Path(command[command.index("--args") + 1])
        assert output_path.stat().st_mode & 0o777 == 0o600
        assert output_path.parent.stat().st_mode & 0o777 == 0o700
        output_path.write_text(
            json.dumps({"ok": True, "result": expected}),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=run_helper,
    ) as run:
        result = execute_eventkit_helper(
            helper_path=helper_path,
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
            calendar_names_or_ids=[calendar_name],
        )

    assert result == expected
    command = run.call_args.args[0]
    assert command[command.index("-a") + 1] == str(helper_path)
    assert Path(command[command.index("--args") + 1]).name == "response.json"
    assert command[-4:] == [
        "snapshot",
        "2026-01-01T00:00:00Z",
        "2027-01-01T00:00:00Z",
        json.dumps([calendar_name]),
    ]


def test_execute_eventkit_helper_uses_dedicated_authorize_command(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    executable = helper_path / "Contents" / "MacOS" / "applet"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"applet")

    def run_helper(command, **kwargs):
        output_index = command.index("--args") + 1
        assert command[output_index + 1 :] == ["authorize"]
        output_path = Path(command[output_index])
        output_path.write_text(
            json.dumps(
                {
                    "ok": True,
                    "result": {"status": 3, "calendars": 2},
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch(
        "apple_calendar_mcp.eventkit_helper.subprocess.run",
        side_effect=run_helper,
    ):
        result = execute_eventkit_helper(helper_path=helper_path)

    assert result == {"status": 3, "calendars": 2}


def test_execute_eventkit_helper_reports_process_failure(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    executable = helper_path / "Contents" / "MacOS" / "applet"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"applet")

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
            helper_path=helper_path,
            start="2026-01-01T00:00:00Z",
            end="2027-01-01T00:00:00Z",
            calendar_names_or_ids=None,
        )


def test_execute_eventkit_helper_reports_authorization_failure(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"
    executable = helper_path / "Contents" / "MacOS" / "applet"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"applet")

    def deny_access(command, **kwargs):
        output_path = Path(command[command.index("--args") + 1])
        output_path.write_text(
            json.dumps({"ok": False, "error": "Calendar full access denied"}),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with (
        patch(
            "apple_calendar_mcp.eventkit_helper.subprocess.run",
            side_effect=deny_access,
        ),
        pytest.raises(
            EventKitHelperError,
            match="Calendar full access denied",
        ),
    ):
        execute_eventkit_helper(helper_path=helper_path)


def test_authorize_installs_opens_and_verifies_helper(tmp_path):
    helper_path = tmp_path / "Mac Calendar MCP EventKit Helper.app"

    with (
        patch(
            "apple_calendar_mcp.eventkit_helper.install_eventkit_helper",
            return_value=helper_path,
        ) as install,
        patch(
            "apple_calendar_mcp.eventkit_helper.execute_eventkit_helper",
            return_value={"status": 3, "calendars": 12},
        ) as execute,
    ):
        result = authorize_eventkit_helper(helper_path=helper_path)

    assert result == {"status": 3, "calendars": 12}
    install.assert_called_once_with(helper_path=helper_path, force=False)
    execute.assert_called_once_with(helper_path=helper_path)
