import struct

import pytest

from asusfancontrol import fan_control
from asusfancontrol.fan_control import FanController, FanControlError, pct_to_duty


class FakeLibrary:
    """Records driver calls in order; fan RPMs and count are scripted."""

    def __init__(self, fan_count=2, rpms=None, temp=55):
        self.calls = []
        self._fan_count = fan_count
        self._rpms = rpms or {0: 2000, 1: 2100}
        self._temp = temp
        self._selected = None

    def initialize(self):
        self.calls.append(("initialize",))

    def shutdown(self):
        self.calls.append(("shutdown",))

    def fan_count(self):
        return self._fan_count

    def select_fan(self, index):
        self._selected = index
        self.calls.append(("select", index))

    def fan_rpm(self):
        return self._rpms[self._selected]

    def set_test_mode(self, enabled):
        self.calls.append(("test_mode", enabled))

    def set_pwm_duty(self, duty):
        self.calls.append(("duty", duty))

    def cpu_temp(self):
        return self._temp


def _controller(library=None, loader=None):
    library = library or FakeLibrary()
    return FanController(loader or (lambda: library), inter_fan_delay_s=0), library


class TestPctToDuty:
    @pytest.mark.parametrize("pct", range(101))
    def test_matches_the_clis_float32_conversion(self, pct):
        # The CLI computes (byte)(pct / 100f * 255f) in single precision.
        def f32(x):
            return struct.unpack("f", struct.pack("f", x))[0]

        expected = int(f32(f32(pct) / f32(100.0)) * f32(255.0)) if pct else 0
        assert pct_to_duty(pct) == expected

    def test_endpoints(self):
        assert pct_to_duty(0) == 0
        assert pct_to_duty(100) == 255


class TestReads:
    def test_temp(self):
        controller, _ = _controller(FakeLibrary(temp=61))
        assert controller.get_cpu_temp() == 61

    @pytest.mark.parametrize("temp", [0, -3])
    def test_unreadable_temp_raises(self, temp):
        controller, _ = _controller(FakeLibrary(temp=temp))
        with pytest.raises(FanControlError, match="temperature"):
            controller.get_cpu_temp()

    def test_fan_speeds_select_each_fan_then_read(self):
        controller, library = _controller()
        assert controller.get_fan_speeds() == [2000, 2100]
        assert [c for c in library.calls if c[0] == "select"] == [("select", 0), ("select", 1)]

    def test_negative_fan_count_raises_actionable_error(self):
        controller, _ = _controller(FakeLibrary(fan_count=-1))
        with pytest.raises(FanControlError, match="SYSTEM"):
            controller.get_fan_count()

    def test_fan_speeds_fail_when_driver_unavailable(self):
        controller, _ = _controller(FakeLibrary(fan_count=-1))
        with pytest.raises(FanControlError):
            controller.get_fan_speeds()

    def test_zero_fans_gives_empty_speeds(self):
        controller, _ = _controller(FakeLibrary(fan_count=0))
        assert controller.get_fan_speeds() == []


class TestWrites:
    def test_set_fan_speed_selects_enables_test_mode_then_writes_duty(self):
        controller, library = _controller()
        controller.set_fan_speed(1, 100)
        assert library.calls[1:] == [("select", 1), ("test_mode", True), ("duty", 255)]

    def test_zero_percent_turns_test_mode_off(self):
        controller, library = _controller()
        controller.set_fan_speed(0, 0)
        assert library.calls[1:] == [("select", 0), ("test_mode", False), ("duty", 0)]

    @pytest.mark.parametrize("pct", [-1, 101])
    def test_out_of_range_pct_rejected_before_touching_driver(self, pct):
        controller, library = _controller()
        with pytest.raises(ValueError):
            controller.set_fan_speed(0, pct)
        assert library.calls == []

    @pytest.mark.parametrize("fan_id", [-1, 256])
    def test_out_of_range_fan_id_rejected(self, fan_id):
        controller, library = _controller()
        with pytest.raises(ValueError):
            controller.set_fan_speed(fan_id, 50)
        assert library.calls == []

    def test_set_auto_zeroes_every_fan_with_test_mode_off(self):
        controller, library = _controller()
        controller.set_auto()
        assert library.calls[1:] == [
            ("select", 0),
            ("test_mode", False),
            ("duty", 0),
            ("select", 1),
            ("test_mode", False),
            ("duty", 0),
        ]

    def test_set_auto_raises_when_driver_unavailable(self):
        controller, library = _controller(FakeLibrary(fan_count=-1))
        with pytest.raises(FanControlError):
            controller.set_auto()
        assert ("duty", 0) not in library.calls


class TestLifecycle:
    def test_library_is_loaded_and_initialised_once_lazily(self):
        loads = []
        library = FakeLibrary()

        def loader():
            loads.append(1)
            return library

        controller, _ = _controller(library, loader)
        assert loads == []
        controller.get_cpu_temp()
        controller.get_cpu_temp()
        assert loads == [1]
        assert library.calls.count(("initialize",)) == 1

    def test_load_failure_becomes_fan_control_error(self):
        def loader():
            raise OSError("bad image")

        controller, _ = _controller(loader=loader)
        with pytest.raises(FanControlError, match="bad image"):
            controller.get_cpu_temp()

    def test_shutdown_releases_driver_and_allows_reinit(self):
        controller, library = _controller()
        controller.get_cpu_temp()
        controller.shutdown()
        controller.shutdown()  # second call is a no-op
        controller.get_cpu_temp()
        assert library.calls.count(("shutdown",)) == 1
        assert library.calls.count(("initialize",)) == 2

    def test_shutdown_before_first_use_does_nothing(self):
        controller, library = _controller()
        controller.shutdown()
        assert library.calls == []


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
