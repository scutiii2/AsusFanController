import json

import pytest

from asusfancontrol import app_controller as app_controller_module
from asusfancontrol import fan_control
from asusfancontrol.app_controller import AppController
from asusfancontrol.config import Mode, Preset


@pytest.fixture
def controller(qtbot, monkeypatch, tmp_path):
    # Never let the worker thread reach the real CLI, regardless of when its
    # event loop happens to deliver a queued cross-thread signal.
    monkeypatch.setattr(fan_control, "get_fan_count", lambda: 2)
    monkeypatch.setattr(fan_control, "get_cpu_temp", lambda: 40)
    monkeypatch.setattr(fan_control, "get_fan_speeds", lambda: [1000, 1000])
    monkeypatch.setattr(fan_control, "set_fan_speed", lambda fan_id, pct: None)
    monkeypatch.setattr(fan_control, "set_auto", lambda: None)

    monkeypatch.setattr(app_controller_module, "CONFIG_PATH", tmp_path / "config.json")

    ctrl = AppController()
    ctrl.fan_count = 2
    yield ctrl
    ctrl.shutdown()


class TestManualMode:
    def test_set_manual_speed_switches_mode_and_records_commanded_speed(self, controller):
        controller.set_manual_speed(0, 75)
        assert controller.mode == Mode.MANUAL
        assert controller.commanded_speeds[0] == 75

    def test_set_manual_speed_clears_active_preset_name(self, controller):
        controller.active_preset_name = "Silent"
        controller.set_manual_speed(0, 75)
        assert controller.active_preset_name is None


class TestPresets:
    def test_apply_preset_commands_every_fan_in_it_and_sets_active_name(self, controller):
        preset = Preset(name="Desk", speeds={0: 40, 1: 60}, builtin=False)
        controller.apply_preset(preset)
        assert controller.mode == Mode.MANUAL
        assert controller.active_preset_name == "Desk"
        assert controller.commanded_speeds == {0: 40, 1: 60}

    def test_save_current_as_preset_then_all_presets_includes_it(self, controller):
        controller.save_current_as_preset("Desk", {0: 40, 1: 60})
        names = [p.name for p in controller.all_presets()]
        assert "Desk" in names

    def test_save_current_as_preset_overwrites_same_name(self, controller):
        controller.save_current_as_preset("Desk", {0: 40, 1: 60})
        controller.save_current_as_preset("Desk", {0: 99, 1: 99})
        matching = [p for p in controller.config.presets if p.name == "Desk"]
        assert len(matching) == 1
        assert matching[0].speeds == {0: 99, 1: 99}

    def test_delete_preset_removes_it(self, controller):
        controller.save_current_as_preset("Desk", {0: 40, 1: 60})
        controller.delete_preset("Desk")
        names = [p.name for p in controller.config.presets]
        assert "Desk" not in names

    def test_all_presets_always_includes_builtins(self, controller):
        names = [p.name for p in controller.all_presets()]
        assert {"Silent", "Balanced", "Performance", "Turbo"} <= set(names)


class TestAutomaticMode:
    def test_set_automatic_switches_mode(self, controller):
        controller.set_manual_speed(0, 50)
        controller.set_automatic()
        assert controller.mode == Mode.AUTOMATIC

    def test_set_automatic_clears_commanded_speeds(self, controller):
        controller.set_manual_speed(0, 50)
        controller.set_automatic()
        assert controller.commanded_speeds == {}

    def test_set_automatic_clears_active_preset_name(self, controller):
        controller.apply_preset(Preset(name="Desk", speeds={0: 40}, builtin=False))
        controller.set_automatic()
        assert controller.active_preset_name is None


class TestCustomCurveMode:
    def test_set_custom_curve_mode_switches_mode(self, controller):
        controller.set_custom_curve_mode()
        assert controller.mode == Mode.CUSTOM

    def test_readings_in_custom_mode_command_fans_from_curve(self, controller):
        controller.set_custom_curve_mode()
        controller.set_curve_points([(30, 20), (80, 100)])
        controller._on_worker_readings(temp=80, speeds=[0, 0])
        assert controller.commanded_speeds == {0: 100, 1: 100}

    def test_readings_in_manual_mode_do_not_invoke_curve(self, controller):
        controller.set_manual_speed(0, 50)
        controller._on_worker_readings(temp=80, speeds=[0, 0])
        # only fan 0 was ever commanded (by set_manual_speed) — the curve
        # never ran, so fan 1 was never touched
        assert 1 not in controller.commanded_speeds


class TestModeChangedSignal:
    @pytest.mark.parametrize(
        ("switch", "expected_mode"),
        [
            (lambda c: c.set_manual_speed(0, 50), Mode.MANUAL),
            (lambda c: c.apply_preset(Preset(name="Desk", speeds={0: 40})), Mode.MANUAL),
            (lambda c: c.set_automatic(), Mode.AUTOMATIC),
            (lambda c: c.set_custom_curve_mode(), Mode.CUSTOM),
        ],
    )
    def test_every_mode_switch_emits_mode_changed_once(self, controller, switch, expected_mode):
        received = []
        controller.mode_changed.connect(received.append)
        switch(controller)
        assert received == [expected_mode]


class TestPersistence:
    def test_state_changes_are_persisted_to_config_path(self, controller, tmp_path):
        controller.set_manual_speed(0, 50)
        saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert saved["last_mode"] == Mode.MANUAL

    def test_set_start_with_windows_persists(self, controller, tmp_path):
        controller.set_start_with_windows(True)
        saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert saved["start_with_windows"] is True
