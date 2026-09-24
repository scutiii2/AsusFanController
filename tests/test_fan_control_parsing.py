import pytest

from asusfancontrol import fan_control
from asusfancontrol.fan_control import (
    FanControlError,
    parse_cpu_temp,
    parse_fan_count,
    parse_fan_speeds,
)


class TestParseFanCount:
    def test_parses_positive_count(self):
        assert parse_fan_count("Fan count: 2") == 2

    def test_negative_count_raises(self):
        with pytest.raises(FanControlError):
            parse_fan_count("Fan count: -1")

    def test_unrecognized_output_raises(self):
        with pytest.raises(FanControlError):
            parse_fan_count("garbage")


class TestParseCpuTemp:
    def test_parses_temp(self):
        assert parse_cpu_temp("Current CPU temp: 45") == 45

    def test_unrecognized_output_raises(self):
        with pytest.raises(FanControlError):
            parse_cpu_temp("garbage")


class TestParseFanSpeeds:
    def test_parses_multiple_comma_separated_speeds(self):
        assert parse_fan_speeds("Current fan speeds: 1200,3400 RPM") == [1200, 3400]

    def test_parses_multiple_space_separated_speeds(self):
        assert parse_fan_speeds("Current fan speeds: 2978 2898 RPM") == [2978, 2898]

    def test_parses_single_speed(self):
        assert parse_fan_speeds("Current fan speeds: 2500 RPM") == [2500]

    def test_empty_speeds_returns_empty_list(self):
        assert parse_fan_speeds("Current fan speeds:  RPM") == []

    def test_unrecognized_output_raises(self):
        with pytest.raises(FanControlError):
            parse_fan_speeds("garbage")

    def test_trailing_separator_raises_fan_control_error_not_value_error(self):
        with pytest.raises(FanControlError):
            parse_fan_speeds("Current fan speeds: 12,34, RPM")


class TestEnsureDriverLibrary:
    def test_no_copy_when_dll_already_present(self, tmp_path, monkeypatch):
        (tmp_path / "AsusWinIO64.dll").write_bytes(b"existing")
        monkeypatch.setattr(fan_control, "assets_dir", lambda: tmp_path)
        copied = []
        monkeypatch.setattr(fan_control.shutil, "copy2", lambda s, d: copied.append((s, d)))
        fan_control.ensure_driver_library()
        assert copied == []
        assert (tmp_path / "AsusWinIO64.dll").read_bytes() == b"existing"

    def test_copies_from_driver_store_when_missing(self, tmp_path, monkeypatch):
        assets = tmp_path / "assets"
        assets.mkdir()
        store = tmp_path / "store" / "AsusWinIO64.dll"
        store.parent.mkdir()
        store.write_bytes(b"driverstore-dll")
        monkeypatch.setattr(fan_control, "assets_dir", lambda: assets)
        monkeypatch.setattr(fan_control.glob, "glob", lambda pat: [str(store)])
        fan_control.ensure_driver_library()
        assert (assets / "AsusWinIO64.dll").read_bytes() == b"driverstore-dll"

    def test_raises_actionable_error_when_not_in_driver_store(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fan_control, "assets_dir", lambda: tmp_path)
        monkeypatch.setattr(fan_control.glob, "glob", lambda pat: [])
        with pytest.raises(FanControlError, match="MyASUS"):
            fan_control.ensure_driver_library()
