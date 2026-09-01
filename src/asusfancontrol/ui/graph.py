"""Rolling real-time line graph of CPU temp and fan speed history."""

from __future__ import annotations

from collections import deque

import pyqtgraph as pg
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from .theme import ACCENT, PANEL, TEXT_DIM

HISTORY_SECONDS = 120
MIN_GRAPH_HEIGHT = 220  # tall enough that axis labels never get clipped


class HistoryGraph(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(MIN_GRAPH_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        pg.setConfigOption("background", PANEL)
        pg.setConfigOption("foreground", TEXT_DIM)

        self._plot = pg.PlotWidget()
        self._plot.showGrid(x=True, y=True, alpha=0.15)
        self._plot.setLabel("left", "Temp (C) / Speed (%)")
        self._plot.setYRange(0, 100)
        self._plot.addLegend()

        self._temp_curve = self._plot.plot(pen=pg.mkPen(ACCENT, width=2), name="CPU Temp")
        self._speed_curve = self._plot.plot(pen=pg.mkPen("#f2a65a", width=2), name="Fan Speed %")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)

        self._times: deque[float] = deque(maxlen=HISTORY_SECONDS)
        self._temps: deque[float] = deque(maxlen=HISTORY_SECONDS)
        self._speed_pcts: deque[float] = deque(maxlen=HISTORY_SECONDS)
        self._tick = 0

    def add_sample(self, temp: float, speed_pct: float) -> None:
        self._tick += 1
        self._times.append(self._tick)
        self._temps.append(temp)
        self._speed_pcts.append(speed_pct)
        self._temp_curve.setData(list(self._times), list(self._temps))
        self._speed_curve.setData(list(self._times), list(self._speed_pcts))
