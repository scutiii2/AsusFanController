"""Wrapper around the bundled AsusFanControl.exe CLI.

This is the only module that shells out to the CLI. Parsing is split into
plain functions (unit-tested against known output formats) from the
subprocess-calling wrapper (only exercisable on real hardware).
"""

from __future__ import annotations

import re
import subprocess

from .paths import assets_dir


class FanControlError(Exception):
    """Raised when the CLI output can't be parsed or the CLI call fails."""


def _exe_path():
    return assets_dir() / "AsusFanControl.exe"


def parse_fan_count(output: str) -> int:
    match = re.search(r"Fan count:\s*(-?\d+)", output)
    if not match:
        raise FanControlError(f"Could not parse fan count from: {output!r}")
    count = int(match.group(1))
    if count < 0:
        raise FanControlError(f"Fan control unavailable (fan count {count}) — is the app running as SYSTEM?")
    return count


def parse_cpu_temp(output: str) -> int:
    match = re.search(r"Current CPU temp:\s*(-?\d+)", output)
    if not match:
        raise FanControlError(f"Could not parse CPU temp from: {output!r}")
    return int(match.group(1))


def parse_fan_speeds(output: str) -> list[int]:
    match = re.search(r"Current fan speeds:\s*([\d,\s]*)RPM", output)
    if not match:
        raise FanControlError(f"Could not parse fan speeds from: {output!r}")
    numbers = match.group(1).strip()
    if not numbers:
        return []
    try:
        return [int(n) for n in re.split(r"[,\s]+", numbers)]
    except ValueError as exc:
        raise FanControlError(f"Could not parse fan speeds from: {output!r}") from exc


def _run(*args: str) -> str:
    exe = _exe_path()
    try:
        result = subprocess.run(
            [str(exe), *args],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FanControlError(f"Failed to run {exe.name} {' '.join(args)}: {exc}") from exc
    if result.returncode != 0:
        raise FanControlError(
            f"{exe.name} {' '.join(args)} exited {result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout


def get_fan_count() -> int:
    return parse_fan_count(_run("--get-fan-count"))


def get_cpu_temp() -> int:
    return parse_cpu_temp(_run("--get-cpu-temp"))


def get_fan_speeds() -> list[int]:
    return parse_fan_speeds(_run("--get-fan-speeds"))


def set_fan_speed(fan_id: int, pct: int) -> None:
    if not 0 <= pct <= 100:
        raise ValueError(f"pct must be 0-100, got {pct}")
    _run(f"--set-fan-speed={fan_id}:{pct}")


def set_auto() -> None:
    _run("--set-fan-speeds=0")
