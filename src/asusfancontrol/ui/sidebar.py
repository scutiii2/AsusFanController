"""Unified sidebar: mode/preset selection list + save-current-as-preset.

Replaces the old static sidebar, the pill-style mode selector, and the
separate preset manager card with one control surface, ordered as passed
in (Automatic (Default), Automatic (Override), built-ins, then user
presets).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..paths import assets_dir


class Sidebar(QWidget):
    mode_selected = Signal(str)
    save_preset_requested = Signal(str)
    delete_preset_requested = Signal(str)

    def __init__(self, settings_widget: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(230)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())
        outer.addWidget(self._build_settings_section(settings_widget))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        list_container = QWidget()
        self._list_layout = QVBoxLayout(list_container)
        self._list_layout.setContentsMargins(10, 6, 10, 6)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch(1)
        scroll.setWidget(list_container)
        outer.addWidget(scroll, stretch=1)

        outer.addWidget(self._build_save_area())

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 18, 16, 14)
        icon_label = QLabel()
        icon_label.setPixmap(QIcon(str(assets_dir() / "fan.png")).pixmap(26, 26))
        layout.addWidget(icon_label)
        title = QLabel("ASUS FAN\nCONTROLLER")
        title.setObjectName("SidebarTitle")
        layout.addWidget(title)
        layout.addStretch(1)
        return header

    def _build_settings_section(self, settings_widget: QWidget) -> QWidget:
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(12, 0, 12, 8)
        section_layout.setSpacing(4)

        toggle = QPushButton("Settings  ▾")
        toggle.setObjectName("FlatButton")
        toggle.setCheckable(True)
        toggle.setChecked(True)
        toggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.addWidget(settings_widget)

        def on_toggle(checked: bool) -> None:
            content.setVisible(checked)
            toggle.setText("Settings  ▾" if checked else "Settings  ▸")

        toggle.toggled.connect(on_toggle)

        section_layout.addWidget(toggle)
        section_layout.addWidget(content)
        return section

    def _build_save_area(self) -> QWidget:
        area = QWidget()
        layout = QVBoxLayout(area)
        layout.setContentsMargins(12, 8, 12, 14)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Preset name")
        save_button = QPushButton("Save current as preset")
        save_button.setObjectName("FlatButton")
        save_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        save_button.clicked.connect(self._on_save_clicked)
        layout.addWidget(self._name_input)
        layout.addWidget(save_button)
        return area

    # -- public API ------------------------------------------------------

    def set_options(self, entries: list[tuple[str, str, bool]]) -> None:
        """entries: (opt_id, label, deletable)."""
        active = self.active_id()

        for btn in list(self._buttons.values()):
            self._group.removeButton(btn)
        while self._list_layout.count() > 1:  # keep the trailing stretch
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons.clear()

        for opt_id, label, deletable in entries:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            btn = QPushButton(label)
            btn.setObjectName("SidebarItem")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, i=opt_id: self.mode_selected.emit(i))
            self._group.addButton(btn)
            row_layout.addWidget(btn, stretch=1)

            if deletable:
                delete_btn = QPushButton("×")
                delete_btn.setObjectName("FlatButton")
                delete_btn.setFixedWidth(28)
                delete_btn.clicked.connect(lambda _checked, name=opt_id: self.delete_preset_requested.emit(name))
                row_layout.addWidget(delete_btn)

            self._list_layout.insertWidget(self._list_layout.count() - 1, row)
            self._buttons[opt_id] = btn

        if active is not None and active in self._buttons:
            self.set_active(active)

    def active_id(self) -> str | None:
        for opt_id, btn in self._buttons.items():
            if btn.isChecked():
                return opt_id
        return None

    def set_active(self, opt_id: str) -> None:
        btn = self._buttons.get(opt_id)
        if btn is not None:
            btn.setChecked(True)

    def _on_save_clicked(self) -> None:
        name = self._name_input.text().strip()
        if name:
            self.save_preset_requested.emit(name)
            self._name_input.clear()
