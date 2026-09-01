"""Start-with-Windows via a Task Scheduler entry (run at logon, highest
privileges) instead of a registry Run key, so the app launches already
elevated with no UAC prompt at login."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TASK_NAME = "AsusFanControlUI"


def _target_exe() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(Path(sys.argv[0]).resolve())


def is_registered() -> bool:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True, text=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result.returncode == 0


def register() -> None:
    exe = _target_exe()
    subprocess.run(
        [
            "schtasks", "/Create", "/TN", TASK_NAME,
            "/TR", f'"{exe}"',
            "/SC", "ONLOGON",
            "/RL", "HIGHEST",
            "/F",
        ],
        check=True, capture_output=True, text=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def unregister() -> None:
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
