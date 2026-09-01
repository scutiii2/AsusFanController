"""Runs all AsusFanControl.exe subprocess calls on a background thread.

Every call to the CLI is a fresh process spawn that touches the EC driver,
which can be slow (driver load overhead, antivirus scanning the exe). Doing
this on the Qt GUI thread freezes the whole UI for the duration of each
call. This worker is moved to its own QThread by AppController so reads and
writes never block the UI, however slow the CLI turns out to be.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from . import fan_control
from .fan_control import FanControlError


class FanWorker(QObject):
    readings_ready = Signal(int, list)
    fan_count_ready = Signal(int)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._interval_ms = 2000

    @Slot(int)
    def start(self, interval_ms: int) -> None:
        self._interval_ms = interval_ms
        try:
            count = fan_control.get_fan_count()
        except FanControlError as exc:
            self.error.emit(str(exc))
            count = 0
        self.fan_count_ready.emit(count)

        self._poll_and_reschedule()

    @Slot(int)
    def set_interval(self, ms: int) -> None:
        self._interval_ms = ms

    def _poll_and_reschedule(self) -> None:
        # Self-rescheduling instead of a repeating QTimer: each poll only
        # queues the NEXT one after it finishes. A repeating QTimer would
        # keep firing every interval_ms regardless of how long a poll takes
        # (each poll shells out to a CLI that can be slow — driver overhead,
        # antivirus scanning), building an ever-growing backlog of queued,
        # increasingly stale invocations on this thread's event loop —
        # including any set_fan_speed request queued behind that backlog,
        # so a user's slider change could take a long time to even reach
        # the hardware. This guarantees at most one poll's worth of lag.
        self._poll()
        QTimer.singleShot(self._interval_ms, self._poll_and_reschedule)

    def _poll(self) -> None:
        try:
            temp = fan_control.get_cpu_temp()
            speeds = fan_control.get_fan_speeds()
        except FanControlError as exc:
            self.error.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - keep the worker loop alive
            self.error.emit(f"Unexpected error while polling: {exc}")
            return
        self.readings_ready.emit(temp, speeds)

    @Slot(int, int)
    def set_fan_speed(self, fan_id: int, pct: int) -> None:
        try:
            fan_control.set_fan_speed(fan_id, pct)
        except FanControlError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error while setting fan speed: {exc}")

    @Slot()
    def set_auto(self) -> None:
        try:
            fan_control.set_auto()
        except FanControlError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error while setting automatic mode: {exc}")
