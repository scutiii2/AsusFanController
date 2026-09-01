"""System tray icon: left-click restores, right-click has quick mode switch + Quit."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMainWindow, QSystemTrayIcon

from ..paths import assets_dir


def _fallback_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor("#15181f"))
    painter = QPainter(pixmap)
    painter.setBrush(QColor("#4fd1c5"))
    painter.setPen(QColor("#4fd1c5"))
    painter.drawEllipse(6, 6, 20, 20)
    painter.end()
    return QIcon(pixmap)


def _tray_icon() -> QIcon:
    icon_path = assets_dir() / "fan.png"
    icon = QIcon(str(icon_path))
    return icon if not icon.isNull() else _fallback_icon()


class TrayIcon(QSystemTrayIcon):
    mode_requested = Signal(str)

    def __init__(self, window: QMainWindow, mode_ids: list[tuple[str, str]]) -> None:
        super().__init__(_tray_icon(), window)
        self._window = window
        self.setToolTip("ASUS FAN CONTROLLER")

        menu = QMenu()
        show_action = menu.addAction("Show")
        show_action.triggered.connect(self._show_window)

        menu.addSeparator()
        self.mode_actions = {}
        for mode_id, label in mode_ids:
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked, m=mode_id: self.mode_requested.emit(m))
            self.mode_actions[mode_id] = action

        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.instance().quit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self) -> None:
        self._window.showNormal()
        self._window.activateWindow()
