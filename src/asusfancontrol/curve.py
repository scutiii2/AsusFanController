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

    Upward changes beyond the hysteresis threshold apply immediately.
    Downward changes must be requested on `sustain_ticks` consecutive calls
    before being applied, and the sustain count resets whenever the target
    moves back up, so a temp hovering near a breakpoint doesn't cause
    audible fan speed oscillation.
    """

    def __init__(
        self,
        curve: FanCurve,
        min_floor: int = 20,
        hysteresis: int = 5,
        sustain_ticks: int = 2,
    ) -> None:
        self.curve = curve
        self.min_floor = min_floor
        self.hysteresis = hysteresis
        self.sustain_ticks = sustain_ticks
        self._last_applied: int | None = None
        self._pending_down: int | None = None
        self._pending_down_count = 0

    def next_speed(self, temp: float) -> int | None:
        target = max(self.curve.interpolate(temp), self.min_floor)

        if self._last_applied is None:
            return self._apply(target)

        if target >= self._last_applied:
            self._pending_down = None
            self._pending_down_count = 0
            if target - self._last_applied >= self.hysteresis or target == self._last_applied:
                if target == self._last_applied:
                    return None
                return self._apply(target)
            return None

        if self._last_applied - target < self.hysteresis:
            self._pending_down = None
            self._pending_down_count = 0
            return None

        if self._pending_down == target:
            self._pending_down_count += 1
        else:
            self._pending_down = target
            self._pending_down_count = 1

        if self._pending_down_count >= self.sustain_ticks:
            return self._apply(target)
        return None

    def _apply(self, target: int) -> int:
        self._last_applied = target
        self._pending_down = None
        self._pending_down_count = 0
        return target
