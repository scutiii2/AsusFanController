import json

from asusfancontrol.config import AppConfig, Preset, load_config, save_config


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
        config.last_mode = "custom"
        save_config(path, config)

        loaded = load_config(path)

        assert loaded.poll_interval_ms == 5000
        assert loaded.start_with_windows is True
        assert loaded.last_mode == "custom"


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
