import pytest

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
