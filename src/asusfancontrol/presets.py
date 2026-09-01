"""Built-in fixed-speed presets."""

from __future__ import annotations

from .config import Preset

_BUILTIN_LEVELS = [
    ("Silent", 30),
    ("Balanced", 50),
    ("Performance", 75),
    ("Turbo", 100),
]


def builtin_presets(fan_count: int) -> list[Preset]:
    fan_ids = range(fan_count)
    return [
        Preset(name=name, speeds={fan_id: pct for fan_id in fan_ids}, builtin=True)
        for name, pct in _BUILTIN_LEVELS
    ]
