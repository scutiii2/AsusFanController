"""Self-elevation: plain user -> Administrator (UAC) -> SYSTEM (PsExec).

Mirrors the existing FanController.bat: a UAC prompt to reach Administrator,
then PsExec -s to reach SYSTEM, since the EC driver needs SYSTEM and
Administrator alone is not enough (confirmed by running the CLI
non-elevated: it returns fan count -1 / temp 0).
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
    """Returns (executable, args) to relaunch this program identically."""
    if getattr(sys, "frozen", False):
        return sys.executable, []
    return sys.executable, [str(Path(sys.argv[0]).resolve())]


def relaunch_as_admin() -> None:
    exe, args = _self_command()
    params = " ".join(f'"{a}"' for a in args)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)


def relaunch_as_system() -> None:
    from .paths import assets_dir

    psexec = assets_dir() / "PsExec.exe"
    exe, args = _self_command()
    subprocess.Popen(
        [str(psexec), "-accepteula", "-i", "-s", "-d", exe, *args],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def ensure_system_elevated() -> bool:
    """Returns True if already SYSTEM. Otherwise relaunches and returns False
    so the caller can exit the current (non-SYSTEM) process."""
    if is_system():
        return True
    if not is_admin():
        relaunch_as_admin()
    else:
        relaunch_as_system()
    return False
