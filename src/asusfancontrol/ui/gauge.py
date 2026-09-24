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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height() - 14) - 16
        rect = QRectF((self.width() - side) / 2, 4, side, side)

        self._draw_arc(painter, rect, "#2a2f3a", 1.0)
        self._draw_arc(painter, rect, ACCENT, self._fraction)

        main_font = QFont("Segoe UI", 15, QFont.Weight.DemiBold)
        small_font = QFont("Segoe UI", 9)
        self._draw_text(painter, rect, rect.center().y() - 16, 20, TEXT, main_font, self._main_text)
        if self._sub_text:
            self._draw_text(painter, rect, rect.center().y() + 6, 16, TEXT_DIM, small_font, self._sub_text)
        self._draw_text(painter, rect, rect.bottom() + 2, 18, TEXT_DIM, small_font, self._label)

    @staticmethod
    def _draw_arc(painter: QPainter, rect: QRectF, color: str, fraction: float) -> None:
        painter.setPen(QPen(QColor(color), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(rect, 90 * 16, int(-270 * 16 * fraction))

    @staticmethod
    def _draw_text(
        painter: QPainter, rect: QRectF, top: float, height: float, color: str, font: QFont, text: str
    ) -> None:
        painter.setPen(QColor(color))
        painter.setFont(font)
        painter.drawText(QRectF(rect.x(), top, rect.width(), height), Qt.AlignmentFlag.AlignCenter, text)
