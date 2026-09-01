"""JSON-backed persistence for presets, curve, and app settings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Preset:
    name: str
    speeds: dict[int, int]
    builtin: bool = False


@dataclass
class AppConfig:
    presets: list[Preset] = field(default_factory=list)
    curve_points: list[tuple[float, int]] = field(default_factory=lambda: [(40, 20), (60, 50), (80, 100)])
    last_mode: str = "automatic"
    poll_interval_ms: int = 2000
    start_with_windows: bool = False

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
        "last_mode": config.last_mode,
        "poll_interval_ms": config.poll_interval_ms,
        "start_with_windows": config.start_with_windows,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
        last_mode=data.get("last_mode", defaults.last_mode),
        poll_interval_ms=data.get("poll_interval_ms", defaults.poll_interval_ms),
        start_with_windows=data.get("start_with_windows", defaults.start_with_windows),
    )
