"""Model/controller layer: wires config + curve + the background fan worker
together. Independent of any specific widget. All actual AsusFanControl.exe
calls happen on a worker thread (see worker.py) so a slow/AV-scanned CLI
call never freezes the UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from .config import AppConfig, Preset, load_config, save_config
from .curve import CurveController, FanCurve
from .presets import builtin_presets
from .worker import FanWorker

CONFIG_PATH = Path.home() / "AppData" / "Roaming" / "AsusFanControlUI" / "config.json"

MODE_AUTOMATIC = "automatic"
MODE_CUSTOM = "custom"
MODE_MANUAL = "manual"


class AppController(QObject):
    readings_updated = Signal(int, list, dict)  # cpu_temp, fan_speeds (RPM), commanded pct by fan_id
    error_occurred = Signal(str)
    mode_changed = Signal(str)
    fans_ready = Signal(int)  # fan_count

    # -- requests to the worker thread (queued automatically: cross-thread) --
    _request_start = Signal(int)
    _request_set_interval = Signal(int)
    _request_set_fan_speed = Signal(int, int)
    _request_set_auto = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config: AppConfig = load_config(CONFIG_PATH)
        self.fan_count = 0
        self.mode = self.config.last_mode
        self.active_preset_name: str | None = None
        self._curve_controller: CurveController | None = None
        self._rebuild_curve_controller()
        # The CLI has no "get current %" reading, only RPM — so the only
        # authoritative percent we can show is one we commanded ourselves.
        # Empty/missing entries mean "unknown" (e.g. Automatic (Default),
        # where the EC controls fans and we never send a %).
        self.commanded_speeds: dict[int, int] = {}

        self._thread = QThread(self)
        self._worker = FanWorker()
        self._worker.moveToThread(self._thread)

        self._worker.readings_ready.connect(self._on_worker_readings)
        self._worker.fan_count_ready.connect(self._on_worker_fan_count)
        self._worker.error.connect(self.error_occurred)

        self._request_start.connect(self._worker.start)
        self._request_set_interval.connect(self._worker.set_interval)
        self._request_set_fan_speed.connect(self._worker.set_fan_speed)
        self._request_set_auto.connect(self._worker.set_auto)

        self._thread.start()

    def start(self) -> None:
        self._request_start.emit(self.config.poll_interval_ms)

    def shutdown(self) -> None:
        self._thread.quit()
        self._thread.wait(3000)

    def all_presets(self) -> list[Preset]:
        return builtin_presets(self.fan_count) + [p for p in self.config.presets if not p.builtin]

    def set_poll_interval(self, ms: int) -> None:
        self.config.poll_interval_ms = ms
        self._request_set_interval.emit(ms)
        self._save()

    def set_manual_speed(self, fan_id: int, pct: int) -> None:
        self.mode = MODE_MANUAL
        self.active_preset_name = None
        self._command_fan_speed(fan_id, pct)
        self.mode_changed.emit(self.mode)
        self._save()

    def apply_preset(self, preset: Preset) -> None:
        self.mode = MODE_MANUAL
        self.active_preset_name = preset.name
        for fan_id, pct in preset.speeds.items():
            self._command_fan_speed(fan_id, pct)
        self.mode_changed.emit(self.mode)
        self._save()

    def save_current_as_preset(self, name: str, speeds: dict[int, int]) -> None:
        self.config.presets = [p for p in self.config.presets if p.name != name]
        self.config.presets.append(Preset(name=name, speeds=speeds, builtin=False))
        self._save()

    def delete_preset(self, name: str) -> None:
        self.config.presets = [p for p in self.config.presets if p.name != name]
        self._save()

    def set_automatic(self) -> None:
        self.mode = MODE_AUTOMATIC
        self.active_preset_name = None
        self.commanded_speeds = {}  # EC takes over; we no longer know the %
        self._request_set_auto.emit()
        self.mode_changed.emit(self.mode)
        self._save()

    def set_custom_curve_mode(self) -> None:
        self.mode = MODE_CUSTOM
        self.active_preset_name = None
        self._rebuild_curve_controller()
        self.mode_changed.emit(self.mode)
        self._save()

    def set_curve_points(self, points: list[tuple[float, int]]) -> None:
        self.config.curve_points = points
        self._rebuild_curve_controller()
        self._save()

    def set_start_with_windows(self, enabled: bool) -> None:
        self.config.start_with_windows = enabled
        self._save()

    def _rebuild_curve_controller(self) -> None:
        curve = FanCurve(list(self.config.curve_points))
        self._curve_controller = CurveController(curve)

    def _on_worker_fan_count(self, fan_count: int) -> None:
        self.fan_count = fan_count
        self.fans_ready.emit(fan_count)

    def _on_worker_readings(self, temp: int, speeds: list[int]) -> None:
        if self.mode == MODE_CUSTOM and self._curve_controller is not None:
            target = self._curve_controller.next_speed(temp)
            if target is not None:
                for fan_id in range(self.fan_count):
                    self._command_fan_speed(fan_id, target)

        self.readings_updated.emit(temp, speeds, dict(self.commanded_speeds))

    def _command_fan_speed(self, fan_id: int, pct: int) -> None:
        self.commanded_speeds[fan_id] = pct
        self._request_set_fan_speed.emit(fan_id, pct)

    def _save(self) -> None:
        self.config.last_mode = self.mode
        save_config(CONFIG_PATH, self.config)
