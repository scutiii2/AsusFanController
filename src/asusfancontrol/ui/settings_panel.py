"""Settings: start-with-Windows toggle and poll interval."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QSpinBox, QWidget


class SettingsPanel(QWidget):
    start_with_windows_toggled = Signal(bool)
    poll_interval_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)

        self._start_with_windows = QCheckBox("Start with Windows")
        self._start_with_windows.toggled.connect(self.start_with_windows_toggled)
        layout.addRow(self._start_with_windows)

        self._poll_interval = QSpinBox()
        self._poll_interval.setRange(500, 10000)
        self._poll_interval.setSingleStep(500)
        self._poll_interval.setSuffix(" ms")
        self._poll_interval.valueChanged.connect(self.poll_interval_changed)
        layout.addRow("Poll interval", self._poll_interval)

    def set_values(self, start_with_windows: bool, poll_interval_ms: int) -> None:
        self._start_with_windows.blockSignals(True)
        self._start_with_windows.setChecked(start_with_windows)
        self._start_with_windows.blockSignals(False)

        self._poll_interval.blockSignals(True)
        self._poll_interval.setValue(poll_interval_ms)
        self._poll_interval.blockSignals(False)
