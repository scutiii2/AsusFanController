"""Runs all fan-driver calls on a background thread.

Reads and writes go through the EC driver, which can stall (driver load,
antivirus scanning, a busy EC). Doing that on the Qt GUI thread would freeze the
whole UI for the duration of each call. This worker is moved to its own QThread
by AppController so reads and writes never block the UI, however slow the
driver turns out to be.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Callable, TypeVar

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from . import fan_control
from .fan_control import FanControlError

T = TypeVar("T")

log = logging.getLogger(__name__)


class FanWorker(QObject):
    readings_ready = Signal(int, list)
    fan_count_ready = Signal(int)
    error = Signal(str)
    poll_failed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._interval_ms = 2000
        # Latest requested % per fan, not yet sent. A slider drag queues one
        # request per tick; each is a driver write, so writing them all would
        # back up behind a slow driver. Only the newest value per fan matters.
        self._pending_speeds: dict[int, int] = {}
        # Owned timers (children of this worker, so they live and die on its
        # thread) rather than QTimer.singleShot with no context object.
        self._poll_timer = QTimer(self)
        self._poll_timer.setSingleShot(True)
        self._poll_timer.timeout.connect(self._poll_and_reschedule)
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_pending_speeds)

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
        # (each poll calls into a driver that can be slow — driver overhead,
        # a busy EC), building an ever-growing backlog of queued,
        # increasingly stale invocations on this thread's event loop —
        # including any set_fan_speed request queued behind that backlog,
        # so a user's slider change could take a long time to even reach
        # the hardware. This guarantees at most one poll's worth of lag.
        self._poll()
        self._poll_timer.start(self._interval_ms)

    def _run_safely(self, action: str, fn: Callable[[], T]) -> T | None:
        """Run fn, reporting any failure through `error` instead of raising,
        so one bad driver call never kills this thread's event loop."""
        try:
            return fn()
        except FanControlError as exc:
            log.error("%s", exc)
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - keep the worker loop alive
            log.exception("Unexpected error while %s", action)
            self.error.emit(f"Unexpected error while {action}: {exc}")
        return None

    def _poll(self) -> None:
        readings = self._run_safely(
            "polling", lambda: (fan_control.get_cpu_temp(), fan_control.get_fan_speeds())
        )
        if readings is None:
            log.warning("Poll failed")
            self.poll_failed.emit()
        else:
            self.readings_ready.emit(*readings)

    @Slot(int, int)
    def set_fan_speed(self, fan_id: int, pct: int) -> None:
        """Queue a speed; the send happens once the event loop has drained
        every request already waiting, so bursts collapse to the latest."""
        self._pending_speeds[fan_id] = pct
        if not self._flush_timer.isActive():
            self._flush_timer.start(0)

    def _flush_pending_speeds(self) -> None:
        pending, self._pending_speeds = self._pending_speeds, {}
        for fan_id, pct in pending.items():
            if self._run_safely("setting fan speed", partial(self._send_speed, fan_id, pct)):
                log.info("Fan %d set to %d%%", fan_id, pct)

    @staticmethod
    def _send_speed(fan_id: int, pct: int) -> bool:
        fan_control.set_fan_speed(fan_id, pct)
        return True

    @Slot()
    def set_auto(self) -> None:
        # Anything still queued was requested before this and must not
        # override it.
        self._pending_speeds.clear()
        self._run_safely("setting automatic mode", fan_control.set_auto)
        log.info("Automatic mode set")
