"""Placeholder shown while Automatic (Default) is active — nothing for the
user to configure, so avoid leaving stale manual/curve controls on screen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class AutomaticPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("Fans are controlled automatically by the system.")
        label.setObjectName("MetricLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(label)
        layout.addStretch(1)
