"""Draggable temp -> fan speed curve editor.

Left-drag an existing point to move it. Double-click empty space to add a
point. Right-click a point to remove it (at least 2 points are kept).
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ..curve import FanCurve
from .theme import ACCENT, PANEL, TEXT_DIM

TEMP_MIN, TEMP_MAX = 0, 100
SPEED_MIN, SPEED_MAX = 0, 100
PICK_RADIUS = 6  # data units
MIN_GRAPH_HEIGHT = 220  # tall enough that axis labels never get clipped


class _CurvePlot(pg.PlotWidget):
    def __init__(self, editor: "CurveEditor") -> None:
        super().__init__()
        self._editor = editor
        self.setMouseEnabled(x=False, y=False)

    def _to_data(self, ev):
        scene_pos = self.mapToScene(ev.position().toPoint())
        point = self.getPlotItem().vb.mapSceneToView(scene_pos)
        return point.x(), point.y()

    def mousePressEvent(self, ev) -> None:
        x, y = self._to_data(ev)
        if ev.button() == Qt.MouseButton.RightButton:
            self._editor.remove_near(x, y)
            ev.accept()
            return
        self._editor.begin_drag(x, y)
        ev.accept()

    def mouseMoveEvent(self, ev) -> None:
        if self._editor.is_dragging():
            x, y = self._to_data(ev)
            self._editor.drag_to(x, y)
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev) -> None:
        if self._editor.is_dragging():
            self._editor.end_drag()
            ev.accept()
            return
        super().mouseReleaseEvent(ev)

    def mouseDoubleClickEvent(self, ev) -> None:
        x, y = self._to_data(ev)
        self._editor.add_point(x, y)
        ev.accept()


class CurveEditor(QWidget):
    curve_changed = Signal(list)  # list[tuple[float, int]]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(MIN_GRAPH_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        pg.setConfigOption("background", PANEL)
        pg.setConfigOption("foreground", TEXT_DIM)

        self._points: list[tuple[float, int]] = [(40, 20), (60, 50), (80, 100)]
        self._dragging_index: int | None = None

        self._plot = _CurvePlot(self)
        self._plot.setLabel("bottom", "CPU Temp (C)")
        self._plot.setLabel("left", "Fan Speed (%)")
        self._plot.setXRange(TEMP_MIN, TEMP_MAX)
        self._plot.setYRange(SPEED_MIN, SPEED_MAX)

        self._line = self._plot.plot(pen=pg.mkPen(ACCENT, width=2))
        self._scatter = pg.ScatterPlotItem(size=14, brush=pg.mkBrush(ACCENT), pen=pg.mkPen("#0b1210"))
        self._plot.addItem(self._scatter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)

        self._redraw()

    def set_points(self, points: list[tuple[float, int]]) -> None:
        self._points = sorted(points, key=lambda p: p[0])
        self._redraw()

    def points(self) -> list[tuple[float, int]]:
        return list(self._points)

    def is_dragging(self) -> bool:
        return self._dragging_index is not None

    def begin_drag(self, x: float, y: float) -> None:
        idx = self._nearest_index(x, y)
        if idx is not None:
            self._dragging_index = idx

    def drag_to(self, x: float, y: float) -> None:
        if self._dragging_index is None:
            return
        idx = self._dragging_index
        lo = self._points[idx - 1][0] + 0.1 if idx > 0 else TEMP_MIN
        hi = self._points[idx + 1][0] - 0.1 if idx < len(self._points) - 1 else TEMP_MAX
        clamped_x = min(max(x, lo), hi)
        clamped_y = int(min(max(y, SPEED_MIN), SPEED_MAX))
        self._points[idx] = (clamped_x, clamped_y)
        self._redraw()

    def end_drag(self) -> None:
        self._dragging_index = None
        self.curve_changed.emit(self.points())

    def add_point(self, x: float, y: float) -> None:
        x = min(max(x, TEMP_MIN), TEMP_MAX)
        y = int(min(max(y, SPEED_MIN), SPEED_MAX))
        self._points.append((x, y))
        self._points.sort(key=lambda p: p[0])
        self._redraw()
        self.curve_changed.emit(self.points())

    def remove_near(self, x: float, y: float) -> None:
        if len(self._points) <= 2:
            return
        idx = self._nearest_index(x, y)
        if idx is not None:
            del self._points[idx]
            self._redraw()
            self.curve_changed.emit(self.points())

    def _nearest_index(self, x: float, y: float) -> int | None:
        best_idx, best_dist = None, PICK_RADIUS
        for i, (px, py) in enumerate(self._points):
            dist = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
            if dist < best_dist:
                best_idx, best_dist = i, dist
        return best_idx

    def _redraw(self) -> None:
        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]
        self._line.setData(xs, ys)
        self._scatter.setData(xs, ys)

    def preview_curve(self) -> FanCurve:
        return FanCurve(list(self._points))
