"""Temp-to-fan-speed curve interpolation and hunting-safe application."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FanCurve:
    """A set of (temp_celsius, speed_pct) breakpoints, linearly interpolated."""

    points: list[tuple[float, int]]

    def __post_init__(self) -> None:
        self.points = sorted(self.points, key=lambda p: p[0])

    def interpolate(self, temp: float) -> int:
        points = self.points
        if temp <= points[0][0]:
            return points[0][1]
        if temp >= points[-1][0]:
            return points[-1][1]

        for (t1, s1), (t2, s2) in zip(points, points[1:]):
            if t1 <= temp <= t2:
                if t1 == t2:
                    return s2
                ratio = (temp - t1) / (t2 - t1)
                return round(s1 + ratio * (s2 - s1))

        return points[-1][1]


class CurveController:
    """Applies a FanCurve with a minimum floor and anti-hunting hysteresis.

    Upward changes (more cooling needed) beyond the hysteresis threshold
    apply immediately, since responding fast to rising temps matters more
    than a quiet ramp. Downward changes are more conservative in two ways:
    they must be requested on `sustain_ticks` consecutive calls before being
    accepted at all (so a temp hovering near a breakpoint doesn't cause
    audible oscillation), and once accepted they glide down by at most
    `max_step_down` per call rather than jumping straight to the target, so
    a sudden temp drop eases the fans down instead of snapping them from
    loud to quiet in one step. A genuine rise during that glide still
    interrupts it and responds immediately.
    """

    def __init__(
        self,
        curve: FanCurve,
        min_floor: int = 20,
        hysteresis: int = 5,
        sustain_ticks: int = 2,
        max_step_down: int = 10,
    ) -> None:
        self.curve = curve
        self.min_floor = min_floor
        self.hysteresis = hysteresis
        self.sustain_ticks = sustain_ticks
        self.max_step_down = max_step_down
        self._last_applied: int | None = None
        self._pending_down_target: int | None = None
        self._pending_down_count = 0
        self._easing_down = False

    def next_speed(self, temp: float) -> int | None:
        target = max(self.curve.interpolate(temp), self.min_floor)

        if self._last_applied is None:
            return self._commit(target)

        if target >= self._last_applied:
            self._reset_pending()
            if target == self._last_applied:
                return None
            if target - self._last_applied >= self.hysteresis:
                return self._commit(target)
            return None

        # target < self._last_applied: a decrease is on the table.
        if self._last_applied - target < self.hysteresis:
            self._reset_pending()
            return None

        if not self._easing_down:
            if self._pending_down_target != target:
                self._pending_down_target = target
                self._pending_down_count = 1
            else:
                self._pending_down_count += 1

            if self._pending_down_count < self.sustain_ticks:
                return None
            self._easing_down = True

        # Actively easing toward `target` (track it in case the temp keeps
        # falling further mid-glide); step down by at most max_step_down
        # instead of jumping there in one move.
        self._pending_down_target = target
        stepped = max(target, self._last_applied - self.max_step_down)
        self._last_applied = stepped
        if stepped == target:
            self._reset_pending()
        return stepped

    def _reset_pending(self) -> None:
        self._pending_down_target = None
        self._pending_down_count = 0
        self._easing_down = False

    def _commit(self, target: int) -> int:
        self._last_applied = target
        self._reset_pending()
        return target
