"""Per-fan manual speed sliders."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QSlider, QWidget


class ManualPanel(QWidget):
    speed_changed = Signal(int, int)  # fan_id, pct

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QFormLayout(self)
        self._sliders: dict[int, QSlider] = {}
        self._value_labels: dict[int, QLabel] = {}

    def set_fan_count(self, fan_count: int) -> None:
        while self._layout.rowCount():
            self._layout.removeRow(0)
        self._sliders.clear()
        self._value_labels.clear()

        for fan_id in range(fan_count):
            row = QWidget()
            from PySide6.QtWidgets import QHBoxLayout
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            value_label = QLabel("0%")
            value_label.setFixedWidth(40)

            slider.valueChanged.connect(lambda v, fid=fan_id, lbl=value_label: self._on_slider_changed(fid, v, lbl))

            row_layout.addWidget(slider)
            row_layout.addWidget(value_label)

            self._sliders[fan_id] = slider
            self._value_labels[fan_id] = value_label
            self._layout.addRow(f"Fan {fan_id + 1}", row)

    def _on_slider_changed(self, fan_id: int, value: int, label: QLabel) -> None:
        label.setText(f"{value}%")
        self.speed_changed.emit(fan_id, value)

    def current_speeds(self) -> dict[int, int]:
        return {fan_id: slider.value() for fan_id, slider in self._sliders.items()}

    def set_speeds(self, speeds: dict[int, int]) -> None:
        for fan_id, pct in speeds.items():
            slider = self._sliders.get(fan_id)
            if slider is not None:
                slider.blockSignals(True)
                slider.setValue(pct)
                slider.blockSignals(False)
                self._value_labels[fan_id].setText(f"{pct}%")
