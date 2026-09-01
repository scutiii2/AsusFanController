"""Start-with-Windows via a Task Scheduler entry (run at logon, highest
privileges) instead of a registry Run key, so the app launches already
elevated with no UAC prompt at login.

Uses PowerShell's ScheduledTasks module rather than schtasks.exe, since the
classic schtasks /Create has no way to set a task description."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TASK_NAME = "_ZAsusFanController"
TASK_DESCRIPTION = "Launches ASUS Fan Controller, already elevated, at logon."


def _target_exe() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(Path(sys.argv[0]).resolve())


def _ps_literal(value: str) -> str:
    """Safely embed a value as a single-quoted PowerShell string literal."""
    return "'" + value.replace("'", "''") + "'"


def _run_powershell(script: str, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def is_registered() -> bool:
    result = _run_powershell(
        f"Get-ScheduledTask -TaskName {_ps_literal(TASK_NAME)} -ErrorAction SilentlyContinue"
    )
    return bool(result.stdout.strip())


def register() -> None:
    exe = _target_exe()
    script = (
        f"$Action = New-ScheduledTaskAction -Execute {_ps_literal(exe)}; "
        "$Trigger = New-ScheduledTaskTrigger -AtLogOn; "
        "$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest; "
        f"Register-ScheduledTask -TaskName {_ps_literal(TASK_NAME)} -Action $Action "
        f"-Trigger $Trigger -Principal $Principal -Description {_ps_literal(TASK_DESCRIPTION)} "
        "-Force | Out-Null"
    )
    result = _run_powershell(script)
    if result.returncode != 0:
        raise RuntimeError(f"Could not register startup task: {result.stderr.strip()}")


def unregister() -> None:
    _run_powershell(
        f"Unregister-ScheduledTask -TaskName {_ps_literal(TASK_NAME)} -Confirm:$false -ErrorAction SilentlyContinue"
    )
