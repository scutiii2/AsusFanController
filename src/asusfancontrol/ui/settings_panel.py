"""Settings: start-with-Windows toggle, poll interval, and max fan RPM."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QSpinBox, QWidget

from .qt_utils import block_signals


class SettingsPanel(QWidget):
    start_with_windows_toggled = Signal(bool)
    poll_interval_changed = Signal(int)
    max_fan_rpm_changed = Signal(int)

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

        self._max_fan_rpm = QSpinBox()
        self._max_fan_rpm.setRange(1000, 20000)
        self._max_fan_rpm.setSingleStep(100)
        self._max_fan_rpm.setSuffix(" RPM")
        self._max_fan_rpm.setToolTip("Your fans' full speed. Sets the % shown in Automatic (Default).")
        self._max_fan_rpm.valueChanged.connect(self.max_fan_rpm_changed)
        layout.addRow("Max fan RPM", self._max_fan_rpm)

    def set_values(self, start_with_windows: bool, poll_interval_ms: int, max_fan_rpm: int) -> None:
        with block_signals(self._start_with_windows):
            self._start_with_windows.setChecked(start_with_windows)

        with block_signals(self._poll_interval):
            self._poll_interval.setValue(poll_interval_ms)

        with block_signals(self._max_fan_rpm):
            self._max_fan_rpm.setValue(max_fan_rpm)
