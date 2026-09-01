"""A radial gauge widget: an arc plus a main reading and an optional
secondary reading (e.g. "72%" main, "2978 RPM" sub)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget

from .theme import ACCENT, TEXT, TEXT_DIM


class Gauge(QWidget):
    def __init__(self, label: str, max_value: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = label
        self._max_value = max_value
        self._fraction = 0.0
        self._main_text = "--"
        self._sub_text = ""
        self.setMinimumSize(120, 130)

    def set_reading(self, arc_value: float, main_text: str, sub_text: str = "") -> None:
        self._fraction = 0.0 if not self._max_value else max(0.0, min(arc_value / self._max_value, 1.0))
        self._main_text = main_text
        self._sub_text = sub_text
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height() - 14) - 16
        rect = QRectF((self.width() - side) / 2, 4, side, side)

        track_pen = QPen(QColor("#2a2f3a"), 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 90 * 16, -270 * 16)

        value_pen = QPen(QColor(ACCENT), 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(value_pen)
        painter.drawArc(rect, 90 * 16, int(-270 * 16 * self._fraction))

        painter.setPen(QColor(TEXT))
        painter.setFont(QFont("Segoe UI", 15, QFont.DemiBold))
        main_rect = QRectF(rect.x(), rect.center().y() - 16, rect.width(), 20)
        painter.drawText(main_rect, Qt.AlignCenter, self._main_text)

        if self._sub_text:
            painter.setPen(QColor(TEXT_DIM))
            painter.setFont(QFont("Segoe UI", 9))
            sub_rect = QRectF(rect.x(), rect.center().y() + 6, rect.width(), 16)
            painter.drawText(sub_rect, Qt.AlignCenter, self._sub_text)

        painter.setPen(QColor(TEXT_DIM))
        painter.setFont(QFont("Segoe UI", 9))
        label_rect = QRectF(rect.x(), rect.bottom() + 2, rect.width(), 18)
        painter.drawText(label_rect, Qt.AlignCenter, self._label)
