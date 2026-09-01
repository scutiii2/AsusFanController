"""Boot splash: the fan icon spinning, with a title styled like the sidebar."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from ..paths import assets_dir
from .theme import ACCENT, BG

ICON_SIZE = 160
WINDOW_SIZE = 320
DEGREES_PER_TICK = 4
TICK_MS = 20


class SplashScreen(QWidget):
    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_SIZE, WINDOW_SIZE)

        icon_path = assets_dir() / "fan.png"
        raw = QPixmap(str(icon_path))
        self._icon = (
            raw.scaled(
                ICON_SIZE, ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            if not raw.isNull()
            else raw
        )

        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._spin)
        self._timer.start(TICK_MS)

        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = self.screen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def _spin(self) -> None:
        self._angle = (self._angle + DEGREES_PER_TICK) % 360
        self.update()

    def finish(self, window: QWidget) -> None:  # mirrors QSplashScreen's API
        self._timer.stop()
        self.close()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_rect = QRectF(0, 0, self.width(), self.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(BG))
        painter.drawRoundedRect(bg_rect, 20, 20)

        if not self._icon.isNull():
            painter.save()
            painter.translate(self.width() / 2, self.height() / 2 - 24)
            painter.rotate(self._angle)
            painter.drawPixmap(
                -self._icon.width() // 2, -self._icon.height() // 2, self._icon
            )
            painter.restore()

        painter.setPen(QColor(ACCENT))
        painter.setFont(QFont("Segoe UI", 17, QFont.Weight.DemiBold))
        title_rect = QRectF(0, self.height() - 78, self.width(), 40)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "ASUS FAN")

        title_rect2 = QRectF(0, self.height() - 46, self.width(), 40)
        painter.drawText(title_rect2, Qt.AlignmentFlag.AlignCenter, "CONTROLLER")
