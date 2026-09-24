"""JSON-backed persistence for presets, curve, and app settings."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Mode(StrEnum):
    AUTOMATIC = "automatic"
    CUSTOM = "custom"
    MANUAL = "manual"


def _parse_mode(value: object, default: Mode) -> Mode:
    if not isinstance(value, str):
        return default
    try:
        return Mode(value)
    except ValueError:
        return default


def _positive_int(value: object, default: int) -> int:
    # bool is an int subclass; true/false in the file is not a valid RPM.
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return default


@dataclass
class Preset:
    name: str
    speeds: dict[int, int]
    builtin: bool = False


@dataclass
class AppConfig:
    presets: list[Preset] = field(default_factory=list)
    curve_points: list[tuple[float, int]] = field(default_factory=lambda: [(40, 20), (60, 50), (80, 100)])
    last_mode: Mode = Mode.AUTOMATIC
    poll_interval_ms: int = 2000
    start_with_windows: bool = False
    # Full-speed RPM, used to show a % in Automatic (Default) mode, where the
    # CLI reports only RPM. 6300 is the confirmed max of the original laptop.
    max_fan_rpm: int = 6300

    @staticmethod
    def default() -> AppConfig:
        return AppConfig()


def save_config(path: Path, config: AppConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "presets": [
            {"name": p.name, "speeds": {str(k): v for k, v in p.speeds.items()}, "builtin": p.builtin}
            for p in config.presets
        ],
        "curve_points": [[t, s] for t, s in config.curve_points],
        "last_mode": config.last_mode.value,
        "poll_interval_ms": config.poll_interval_ms,
        "start_with_windows": config.start_with_windows,
        "max_fan_rpm": config.max_fan_rpm,
    }
    # Write beside the target, then swap it in: a crash mid-write leaves only
    # a stray temp file, never a truncated config.json that load_config would
    # discard (taking the user's presets with it).
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def migrate_legacy_config(path: Path, legacy: Path) -> None:
    """Copy a config from the old location once, leaving the old file as a backup."""
    if path == legacy or path.exists() or not legacy.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy, path)


def load_config(path: Path) -> AppConfig:
    defaults = AppConfig.default()
    if not path.exists():
        return defaults

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return defaults

    if not isinstance(data, dict):
        return defaults

    try:
        presets = [
            Preset(
                name=p["name"],
                speeds={int(k): v for k, v in p["speeds"].items()},
                builtin=p.get("builtin", False),
            )
            for p in data.get("presets", [])
        ]
        curve_points = [(t, s) for t, s in data.get("curve_points", defaults.curve_points)]

        return AppConfig(
            presets=presets,
            curve_points=curve_points,
            last_mode=_parse_mode(data.get("last_mode"), defaults.last_mode),
            poll_interval_ms=data.get("poll_interval_ms", defaults.poll_interval_ms),
            start_with_windows=data.get("start_with_windows", defaults.start_with_windows),
            max_fan_rpm=_positive_int(data.get("max_fan_rpm"), defaults.max_fan_rpm),
        )
    except (KeyError, TypeError, ValueError):
        return defaults
