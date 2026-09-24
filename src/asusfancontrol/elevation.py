"""Self-elevation: plain user -> Administrator (UAC) -> SYSTEM.

A UAC prompt reaches Administrator, then the app relaunches itself as SYSTEM,
since the EC driver needs SYSTEM and Administrator alone is not enough: run
from an elevated Administrator shell, the CLI still returns fan count -1 /
temp 0, the same as unelevated.

SYSTEM is reached by duplicating a SYSTEM process token (system_launch), the
same mechanism as PsExec -s -i but without shipping a third-party binary.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def is_system() -> bool:
    result = subprocess.run(
        ["whoami"],
        capture_output=True,
        text=True,
        timeout=5,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result.stdout.strip().lower() == "nt authority\\system"


def _self_command() -> tuple[str, list[str]]:
    """Returns (executable, args) to relaunch this program identically,
    preserving any command-line arguments across the elevation relaunches."""
    if getattr(sys, "frozen", False):
        return sys.executable, list(sys.argv[1:])
    return sys.executable, [str(Path(sys.argv[0]).resolve()), *sys.argv[1:]]


def relaunch_as_admin() -> None:
    exe, args = _self_command()
    params = " ".join(f'"{a}"' for a in args)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)


def _command_line() -> str:
    exe, args = _self_command()
    return " ".join(f'"{part}"' for part in (exe, *args))


def relaunch_as_system() -> None:
    """Relaunch this program as SYSTEM. Raises SystemLaunchError on failure."""
    from . import system_launch

    system_launch.launch_as_system(_command_line())


def ensure_system_elevated() -> bool:
    """Returns True if already SYSTEM. Otherwise relaunches and returns False
    so the caller can exit the current (non-SYSTEM) process."""
    from . import system_launch

    if is_system():
        return True
    if not is_admin():
        relaunch_as_admin()
        return False
    try:
        relaunch_as_system()
    except system_launch.SystemLaunchError as exc:
        # No QApplication exists yet, so use a native dialog.
        ctypes.windll.user32.MessageBoxW(
            None,
            f"Could not relaunch with SYSTEM privileges, which the fan driver requires:\n\n{exc}",
            "ASUS FAN CONTROLLER",
            0x10,  # MB_ICONERROR
        )
    return False
