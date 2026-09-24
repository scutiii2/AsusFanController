import json
from pathlib import Path

import pytest

from asusfancontrol.config import AppConfig, Mode, Preset, load_config, migrate_legacy_config, save_config


class TestAppConfigDefaults:
    def test_defaults_have_no_user_presets(self):
        config = AppConfig.default()
        assert config.presets == []

    def test_defaults_have_sane_poll_interval(self):
        config = AppConfig.default()
        assert config.poll_interval_ms > 0

    def test_defaults_last_mode_is_automatic(self):
        config = AppConfig.default()
        assert config.last_mode == "automatic"


class TestConfigRoundTrip:
    def test_save_then_load_preserves_presets(self, tmp_path):
        path = tmp_path / "config.json"
        config = AppConfig.default()
        config.presets.append(Preset(name="Desk", speeds={0: 40, 1: 40}))
        save_config(path, config)

        loaded = load_config(path)

        assert loaded.presets == [Preset(name="Desk", speeds={0: 40, 1: 40})]

    def test_save_then_load_preserves_curve_points(self, tmp_path):
        path = tmp_path / "config.json"
        config = AppConfig.default()
        config.curve_points = [(30, 20), (70, 100)]
        save_config(path, config)

        loaded = load_config(path)

        assert loaded.curve_points == [(30, 20), (70, 100)]

    def test_save_then_load_preserves_settings(self, tmp_path):
        path = tmp_path / "config.json"
        config = AppConfig.default()
        config.poll_interval_ms = 5000
        config.start_with_windows = True
        config.last_mode = Mode.CUSTOM
        save_config(path, config)

        loaded = load_config(path)

        assert loaded.poll_interval_ms == 5000
        assert loaded.start_with_windows is True
        assert loaded.last_mode == "custom"


class TestConfigSaveIsAtomic:
    def test_crash_mid_write_keeps_the_previous_config(self, tmp_path, monkeypatch):
        path = tmp_path / "config.json"
        original = AppConfig.default()
        original.presets.append(Preset(name="Desk", speeds={0: 40}))
        save_config(path, original)

        real_write_text = Path.write_text

        def write_half_then_crash(self, data, *args, **kwargs):
            real_write_text(self, data[: len(data) // 2], *args, **kwargs)
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", write_half_then_crash)
        changed = AppConfig.default()
        changed.poll_interval_ms = 9000
        with pytest.raises(OSError):
            save_config(path, changed)
        monkeypatch.undo()

        assert load_config(path).presets == [Preset(name="Desk", speeds={0: 40})]

    def test_save_leaves_no_temp_file_behind(self, tmp_path):
        save_config(tmp_path / "config.json", AppConfig.default())
        assert [p.name for p in tmp_path.iterdir()] == ["config.json"]


class TestMigrateLegacyConfig:
    def _write_legacy(self, tmp_path):
        legacy = tmp_path / "old" / "config.json"
        config = AppConfig.default()
        config.presets.append(Preset(name="Desk", speeds={0: 40}))
        save_config(legacy, config)
        return legacy

    def test_copies_legacy_config_when_new_one_is_missing(self, tmp_path):
        legacy = self._write_legacy(tmp_path)
        new = tmp_path / "new" / "config.json"
        migrate_legacy_config(new, legacy)
        assert load_config(new).presets == [Preset(name="Desk", speeds={0: 40})]
        assert legacy.exists()

    def test_never_overwrites_an_existing_new_config(self, tmp_path):
        legacy = self._write_legacy(tmp_path)
        new = tmp_path / "new" / "config.json"
        save_config(new, AppConfig.default())
        migrate_legacy_config(new, legacy)
        assert load_config(new).presets == []

    def test_does_nothing_without_a_legacy_config(self, tmp_path):
        new = tmp_path / "new" / "config.json"
        migrate_legacy_config(new, tmp_path / "missing.json")
        assert not new.exists()

    def test_same_path_is_a_no_op(self, tmp_path):
        legacy = self._write_legacy(tmp_path)
        migrate_legacy_config(legacy, legacy)
        assert load_config(legacy).presets == [Preset(name="Desk", speeds={0: 40})]


class TestConfigLoadFallback:
    def test_missing_file_returns_defaults(self, tmp_path):
        path = tmp_path / "does_not_exist.json"
        loaded = load_config(path)
        assert loaded == AppConfig.default()

    def test_corrupt_json_returns_defaults(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("{ not valid json", encoding="utf-8")
        loaded = load_config(path)
        assert loaded == AppConfig.default()

    def test_valid_json_missing_fields_falls_back_to_defaults_for_those_fields(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"poll_interval_ms": 9000}), encoding="utf-8")
        loaded = load_config(path)
        assert loaded.poll_interval_ms == 9000
        assert loaded.presets == []

    def test_unknown_last_mode_falls_back_to_automatic_and_keeps_other_settings(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"last_mode": "turbo", "poll_interval_ms": 9000}), encoding="utf-8")
        loaded = load_config(path)
        assert loaded.last_mode is Mode.AUTOMATIC
        assert loaded.poll_interval_ms == 9000

    def test_non_string_last_mode_falls_back_to_automatic(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"last_mode": 3}), encoding="utf-8")
        assert load_config(path).last_mode is Mode.AUTOMATIC

    def test_loaded_last_mode_is_a_mode_not_a_plain_string(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"last_mode": "custom"}), encoding="utf-8")
        assert load_config(path).last_mode is Mode.CUSTOM

    def test_max_fan_rpm_round_trips(self, tmp_path):
        path = tmp_path / "config.json"
        config = AppConfig.default()
        config.max_fan_rpm = 4800
        save_config(path, config)
        assert load_config(path).max_fan_rpm == 4800

    def test_config_without_max_fan_rpm_gets_the_default(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"poll_interval_ms": 9000}), encoding="utf-8")
        assert load_config(path).max_fan_rpm == 6300

    def test_invalid_max_fan_rpm_falls_back_and_keeps_other_settings(self, tmp_path):
        path = tmp_path / "config.json"
        for bad in [0, -5, "fast", True, None, 4500.5]:
            path.write_text(json.dumps({"max_fan_rpm": bad, "poll_interval_ms": 9000}), encoding="utf-8")
            loaded = load_config(path)
            assert loaded.max_fan_rpm == 6300, bad
            assert loaded.poll_interval_ms == 9000

    def test_malformed_preset_entry_falls_back_to_defaults(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"presets": [{"name": "Broken"}]}), encoding="utf-8")
        loaded = load_config(path)
        assert loaded == AppConfig.default()
