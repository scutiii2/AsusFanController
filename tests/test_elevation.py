import sys

import pytest

from asusfancontrol import elevation, system_launch
from asusfancontrol.elevation import _command_line, _self_command


class TestSelfCommand:
    def test_frozen_exe_relaunches_itself_with_no_args(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "argv", ["AsusFanControlUI.exe"])
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

    def test_frozen_exe_preserves_extra_arguments(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "argv", ["AsusFanControlUI.exe", "--driver-check"])
        _exe, args = _self_command()
        assert args == ["--driver-check"]

    def test_unfrozen_script_preserves_extra_arguments(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        monkeypatch.setattr(sys, "argv", ["run.py", "--driver-check"])
        _exe, args = _self_command()
        assert args[-1] == "--driver-check"


class TestCommandLine:
    def test_quotes_every_part(self, monkeypatch):
        monkeypatch.setattr(elevation, "_self_command", lambda: (r"C:\a b\py.exe", [r"C:\c d\run.py"]))
        assert _command_line() == '"C:\\a b\\py.exe" "C:\\c d\\run.py"'


class TestRelaunchAsSystem:
    def test_passes_the_quoted_command_line_to_the_token_launcher(self, monkeypatch):
        calls = []
        monkeypatch.setattr(system_launch, "launch_as_system", lambda cmd: calls.append(cmd))
        elevation.relaunch_as_system()
        assert calls == [elevation._command_line()]

    def test_propagates_launch_failure(self, monkeypatch):
        def boom(_cmd):
            raise system_launch.SystemLaunchError("nope")

        monkeypatch.setattr(system_launch, "launch_as_system", boom)
        with pytest.raises(system_launch.SystemLaunchError):
            elevation.relaunch_as_system()
