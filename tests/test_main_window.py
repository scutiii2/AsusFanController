import pytest
from PySide6.QtWidgets import QMessageBox

from asusfancontrol import app_controller as app_controller_module
from asusfancontrol import autostart, fan_control
from asusfancontrol.app_controller import AppController
from asusfancontrol.config import Mode
from asusfancontrol.ui.main_window import MODE_AUTO_ID, MODE_CUSTOM_ID, SELECTABLE_MODES, MainWindow


@pytest.fixture
def make_window(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(fan_control, "get_fan_count", lambda: 2)
    monkeypatch.setattr(fan_control, "get_cpu_temp", lambda: 40)
    monkeypatch.setattr(fan_control, "get_fan_speeds", lambda: [1000, 1000])
    monkeypatch.setattr(fan_control, "set_fan_speed", lambda fan_id, pct: None)
    monkeypatch.setattr(fan_control, "set_auto", lambda: None)
    monkeypatch.setattr(autostart, "is_registered", lambda: False)
    monkeypatch.setattr(app_controller_module, "CONFIG_PATH", tmp_path / "config.json")

    controllers = []

    def build(mode: Mode = Mode.AUTOMATIC) -> MainWindow:
        controller = AppController()
        controller.mode = mode
        controllers.append(controller)
        window = MainWindow(controller)
        qtbot.addWidget(window)
        window.tray.hide()
        # Same path as a real startup: sets controller.fan_count, then emits
        # fans_ready, which the window builds its gauges and sidebar from.
        controller._on_worker_fan_count(2)
        return window

    yield build
    for controller in controllers:
        controller.shutdown()


class TestSelectableModes:
    def test_sidebar_lists_selectable_modes_first_in_order(self, make_window):
        window = make_window()
        ids = list(window.sidebar._buttons)
        assert ids[: len(SELECTABLE_MODES)] == [opt_id for opt_id, _ in SELECTABLE_MODES]

    def test_sidebar_and_tray_show_the_same_labels(self, make_window):
        window = make_window()
        sidebar_labels = [window.sidebar._buttons[opt_id].text() for opt_id, _ in SELECTABLE_MODES]
        tray_labels = [window.tray.mode_actions[opt_id].text() for opt_id, _ in SELECTABLE_MODES]
        assert sidebar_labels == tray_labels == [label for _, label in SELECTABLE_MODES]

    def test_builtin_presets_follow_the_mode_entries(self, make_window):
        window = make_window()
        ids = list(window.sidebar._buttons)
        assert "Silent" in ids[len(SELECTABLE_MODES) :]


class TestStartupPanel:
    @pytest.mark.parametrize(
        ("mode", "panel_attr"),
        [
            (Mode.AUTOMATIC, "automatic_panel"),
            (Mode.CUSTOM, "curve_editor"),
            (Mode.MANUAL, "manual_panel"),
        ],
    )
    def test_saved_mode_shows_its_panel(self, make_window, mode, panel_attr):
        window = make_window(mode)
        assert window.stack.currentWidget() is getattr(window, panel_attr)


class TestErrorPopup:
    def test_repeated_errors_reuse_one_box(self, make_window):
        window = make_window()
        for message in ["driver missing", "driver missing", "exit 1"]:
            window._on_error(message)
        boxes = window.findChildren(QMessageBox)
        assert len(boxes) == 1
        assert boxes[0].text() == "exit 1"
        assert boxes[0].isVisible()

    def test_same_error_does_not_reopen_after_user_closes_it(self, make_window):
        window = make_window()
        window._on_error("driver missing")
        window._error_box.close()
        window._on_error("driver missing")
        assert not window._error_box.isVisible()

    def test_same_error_shows_again_after_a_successful_reading(self, make_window):
        window = make_window()
        window._on_error("driver missing")
        window._error_box.close()
        window._on_readings_updated(40, [1000, 1000], {})
        window._on_error("driver missing")
        assert window._error_box.isVisible()

    def test_error_box_does_not_block(self, make_window):
        window = make_window()
        window._on_error("driver missing")
        assert not window._error_box.isModal()


class TestModeSelection:
    def test_selecting_override_shows_curve_editor_and_highlights_it(self, make_window):
        window = make_window()
        window._on_mode_selected(MODE_CUSTOM_ID)
        assert window.controller.mode is Mode.CUSTOM
        assert window.stack.currentWidget() is window.curve_editor
        assert window.sidebar.active_id() == MODE_CUSTOM_ID

    def test_selecting_default_shows_automatic_panel(self, make_window):
        window = make_window(Mode.CUSTOM)
        window._on_mode_selected(MODE_AUTO_ID)
        assert window.controller.mode is Mode.AUTOMATIC
        assert window.stack.currentWidget() is window.automatic_panel

    def test_selecting_preset_shows_manual_panel_with_its_speeds(self, make_window):
        window = make_window()
        window._on_mode_selected("Turbo")
        assert window.controller.mode is Mode.MANUAL
        assert window.stack.currentWidget() is window.manual_panel
        assert window.manual_panel.current_speeds() == {0: 100, 1: 100}
        assert window.sidebar.active_id() == "Turbo"
