import pytest

from asusfancontrol import fan_control
from asusfancontrol.fan_control import FanControlError
from asusfancontrol.worker import FanWorker


def _raise(exc):
    def fn(*_args):
        raise exc

    return fn


@pytest.fixture
def worker(qtbot):
    return FanWorker()


def _collect(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


class TestPoll:
    def test_success_emits_readings(self, worker, monkeypatch):
        monkeypatch.setattr(fan_control, "get_cpu_temp", lambda: 55)
        monkeypatch.setattr(fan_control, "get_fan_speeds", lambda: [2000, 2100])
        readings = _collect(worker.readings_ready)
        errors = _collect(worker.error)

        worker._poll()

        assert readings == [(55, [2000, 2100])]
        assert errors == []

    def test_fan_control_error_emits_its_message_and_no_readings(self, worker, monkeypatch):
        monkeypatch.setattr(fan_control, "get_cpu_temp", _raise(FanControlError("no driver")))
        readings = _collect(worker.readings_ready)
        errors = _collect(worker.error)

        worker._poll()

        assert readings == []
        assert errors == [("no driver",)]

    def test_unexpected_error_is_labelled_with_the_action(self, worker, monkeypatch):
        monkeypatch.setattr(fan_control, "get_cpu_temp", lambda: 55)
        monkeypatch.setattr(fan_control, "get_fan_speeds", _raise(RuntimeError("boom")))
        errors = _collect(worker.error)

        worker._poll()

        assert errors == [("Unexpected error while polling: boom",)]


class TestSetFanSpeed:
    def test_passes_arguments_through(self, worker, monkeypatch):
        calls = []
        monkeypatch.setattr(fan_control, "set_fan_speed", lambda fan_id, pct: calls.append((fan_id, pct)))

        worker.set_fan_speed(1, 70)

        assert calls == [(1, 70)]

    def test_fan_control_error_emits_its_message(self, worker, monkeypatch):
        monkeypatch.setattr(fan_control, "set_fan_speed", _raise(FanControlError("exit 1")))
        errors = _collect(worker.error)

        worker.set_fan_speed(0, 50)

        assert errors == [("exit 1",)]

    def test_unexpected_error_is_labelled_with_the_action(self, worker, monkeypatch):
        monkeypatch.setattr(fan_control, "set_fan_speed", _raise(OSError("denied")))
        errors = _collect(worker.error)

        worker.set_fan_speed(0, 50)

        assert errors == [("Unexpected error while setting fan speed: denied",)]


class TestSetAuto:
    def test_unexpected_error_is_labelled_with_the_action(self, worker, monkeypatch):
        monkeypatch.setattr(fan_control, "set_auto", _raise(RuntimeError("boom")))
        errors = _collect(worker.error)

        worker.set_auto()

        assert errors == [("Unexpected error while setting automatic mode: boom",)]
