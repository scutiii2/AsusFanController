import sys

from asusfancontrol.elevation import _self_command


class TestSelfCommand:
    def test_frozen_exe_relaunches_itself_with_no_args(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        exe, args = _self_command()
        assert exe == sys.executable
        assert args == []

    def test_unfrozen_script_relaunches_via_interpreter_with_script_path(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        monkeypatch.setattr(sys, "argv", ["run.py"])
        exe, args = _self_command()
        assert exe == sys.executable
        assert len(args) == 1
        assert args[0].endswith("run.py")
