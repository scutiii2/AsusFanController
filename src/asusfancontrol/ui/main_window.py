from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import autostart
from ..app_controller import AppController, MODE_AUTOMATIC, MODE_CUSTOM, MODE_MANUAL
from ..paths import assets_dir
from .automatic_panel import AutomaticPanel
from .curve_editor import CurveEditor
from .gauge import Gauge
from .graph import HistoryGraph
from .manual_panel import ManualPanel
from .settings_panel import SettingsPanel
from .sidebar import Sidebar
from .theme import STYLESHEET
from .tray import TrayIcon

MODE_AUTO_ID = "__automatic__"
MODE_CUSTOM_ID = "__custom__"

# The CLI has no "get current %" reading — only RPM. In Automatic (Default),
# where nothing is commanded by us, this is the only way to estimate a
# percentage for display, calibrated to this hardware's confirmed max RPM.
MAX_FAN_RPM = 6300

APP_ICON_PATH = assets_dir() / "fan.png"


def app_icon() -> QIcon:
    return QIcon(str(APP_ICON_PATH))


def _card(widget: QWidget) -> QFrame:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.addWidget(widget)
    return frame


def _fan_label(fan_id: int, fan_count: int) -> str:
    if fan_count == 2:
        return "FAN 1 (CPU)" if fan_id == 0 else "FAN 2 (GPU)"
    return f"FAN {fan_id + 1}"


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("ASUS FAN CONTROLLER")
        self.setWindowIcon(app_icon())
        self.resize(980, 680)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._wire_controller()

        self.tray = TrayIcon(
            self, [(MODE_AUTO_ID, "Automatic (Default)"), (MODE_CUSTOM_ID, "Automatic (Override)")]
        )
        self.tray.mode_requested.connect(self._on_mode_selected)
        self.tray.show()

    # -- layout -------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.settings_panel = SettingsPanel()
        self.sidebar = Sidebar(settings_widget=self.settings_panel)
        root.addWidget(self.sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        gauges_row = QHBoxLayout()
        self.temp_gauge = Gauge("CPU TEMP", 100)
        self.fan_gauges: list[Gauge] = []
        gauges_row.addWidget(_card(self.temp_gauge))
        content_layout.addLayout(gauges_row)
        self._gauges_row = gauges_row

        self.graph = HistoryGraph()
        content_layout.addWidget(_card(self.graph), stretch=1)

        self.stack = QStackedWidget()
        self.manual_panel = ManualPanel()
        self.curve_editor = CurveEditor()
        self.automatic_panel = AutomaticPanel()

        self.stack.addWidget(self.manual_panel)
        self.stack.addWidget(self.curve_editor)
        self.stack.addWidget(self.automatic_panel)

        content_layout.addWidget(_card(self.stack), stretch=1)

        root.addWidget(content, stretch=1)
        self.setCentralWidget(central)

    def _rebuild_fan_gauges(self, fan_count: int) -> None:
        for gauge in self.fan_gauges:
            self._gauges_row.removeWidget(gauge.parent())
            gauge.parent().deleteLater()
        self.fan_gauges = []
        for i in range(fan_count):
            gauge = Gauge(_fan_label(i, fan_count), 100)
            self.fan_gauges.append(gauge)
            self._gauges_row.addWidget(_card(gauge))

    def _refresh_sidebar_options(self) -> None:
        entries = [
            (MODE_AUTO_ID, "Automatic (Default)", False),
            (MODE_CUSTOM_ID, "Automatic (Override)", False),
        ]
        for preset in self.controller.all_presets():
            entries.append((preset.name, preset.name, not preset.builtin))
        self.sidebar.set_options(entries)

    # -- controller wiring ---------------------------------------------

    def _wire_controller(self) -> None:
        c = self.controller
        c.fans_ready.connect(self._on_fans_ready)
        c.readings_updated.connect(self._on_readings_updated)
        c.error_occurred.connect(self._on_error)
        c.mode_changed.connect(self._on_mode_changed)

        self.sidebar.mode_selected.connect(self._on_mode_selected)
        self.sidebar.save_preset_requested.connect(self._on_save_preset)
        self.sidebar.delete_preset_requested.connect(self._on_delete_preset)
        self.manual_panel.speed_changed.connect(c.set_manual_speed)
        self.curve_editor.curve_changed.connect(c.set_curve_points)
        self.settings_panel.start_with_windows_toggled.connect(self._on_start_with_windows_toggled)
        self.settings_panel.poll_interval_changed.connect(c.set_poll_interval)

        self._sync_start_with_windows_checkbox()
        self.curve_editor.set_points(c.config.curve_points)

    def _sync_start_with_windows_checkbox(self) -> None:
        # config.json only records what we last asked for, not reality — the
        # task could since have been removed (or added) outside the app, via
        # remove_startup_task.bat/add_startup_task.bat or the Task Scheduler
        # GUI directly. Reconcile against the actual registration on launch.
        try:
            actually_registered = autostart.is_registered()
        except Exception:  # noqa: BLE001 - a failed check shouldn't block startup
            actually_registered = self.controller.config.start_with_windows

        if actually_registered != self.controller.config.start_with_windows:
            self.controller.set_start_with_windows(actually_registered)

        self.settings_panel.set_values(actually_registered, self.controller.config.poll_interval_ms)

    def _on_fans_ready(self, fan_count: int) -> None:
        self._rebuild_fan_gauges(fan_count)
        self.manual_panel.set_fan_count(fan_count)
        self._refresh_sidebar_options()
        self._sync_stack_and_sidebar_to_mode()

    def _sync_stack_and_sidebar_to_mode(self) -> None:
        mode = self.controller.mode
        if mode == MODE_CUSTOM:
            self.stack.setCurrentWidget(self.curve_editor)
            self.sidebar.set_active(MODE_CUSTOM_ID)
        elif mode == MODE_AUTOMATIC:
            self.stack.setCurrentWidget(self.automatic_panel)
            self.sidebar.set_active(MODE_AUTO_ID)
        else:
            self.stack.setCurrentWidget(self.manual_panel)
            if self.controller.active_preset_name:
                self.sidebar.set_active(self.controller.active_preset_name)

    def _on_readings_updated(self, temp: int, speeds: list[int], commanded: dict[int, int]) -> None:
        self.temp_gauge.set_reading(temp, f"{temp}°C")
        # In Manual mode, trust the sliders directly — they're what's on
        # screen, and it means a drag shows the right % immediately instead
        # of waiting for a poll round-trip through the controller.
        if self.controller.mode == MODE_MANUAL:
            commanded = self.manual_panel.current_speeds()
        graph_pcts = []
        for fan_id, (gauge, rpm) in enumerate(zip(self.fan_gauges, speeds)):
            pct = commanded.get(fan_id)
            if pct is None:
                # Automatic (Default): the EC controls fans and the CLI has
                # no "get current %" reading, so estimate from RPM instead.
                pct = min(rpm / MAX_FAN_RPM * 100, 100)
            gauge.set_reading(pct, f"{pct:.0f}%", f"{rpm} RPM")
            graph_pcts.append(pct)
        avg_pct = sum(graph_pcts) / len(graph_pcts) if graph_pcts else 0
        self.graph.add_sample(temp, avg_pct)

    def _on_error(self, message: str) -> None:
        QMessageBox.warning(self, "ASUS FAN CONTROLLER", message)

    def _on_mode_changed(self, mode: str) -> None:
        if mode == MODE_CUSTOM:
            self.stack.setCurrentWidget(self.curve_editor)
        elif mode == MODE_AUTOMATIC:
            self.stack.setCurrentWidget(self.automatic_panel)
        elif mode == MODE_MANUAL:
            self.stack.setCurrentWidget(self.manual_panel)

    def _on_mode_selected(self, opt_id: str) -> None:
        if opt_id == MODE_AUTO_ID:
            self.controller.set_automatic()
            self.stack.setCurrentWidget(self.automatic_panel)
            self.sidebar.set_active(MODE_AUTO_ID)
            return
        if opt_id == MODE_CUSTOM_ID:
            self.controller.set_custom_curve_mode()
            self.stack.setCurrentWidget(self.curve_editor)
            self.sidebar.set_active(MODE_CUSTOM_ID)
            return
        preset = next((p for p in self.controller.all_presets() if p.name == opt_id), None)
        if preset is not None:
            self.controller.apply_preset(preset)
            self.manual_panel.set_speeds(preset.speeds)
            self.stack.setCurrentWidget(self.manual_panel)
            self.sidebar.set_active(opt_id)

    def _on_save_preset(self, name: str) -> None:
        self.controller.save_current_as_preset(name, self.manual_panel.current_speeds())
        self._refresh_sidebar_options()

    def _on_delete_preset(self, name: str) -> None:
        self.controller.delete_preset(name)
        self._refresh_sidebar_options()

    def _on_start_with_windows_toggled(self, enabled: bool) -> None:
        try:
            if enabled:
                autostart.register()
            else:
                autostart.unregister()
        except Exception as exc:  # noqa: BLE001 - surface any schtasks failure
            QMessageBox.warning(self, "Start with Windows", f"Could not update startup task: {exc}")
            enabled = not enabled
        self.controller.set_start_with_windows(enabled)

    # -- window behavior -------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        event.ignore()
        self.hide()
