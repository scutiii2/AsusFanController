from pathlib import Path

from asusfancontrol.paths import config_path, legacy_config_path


class TestConfigPath:
    def test_elevated_app_uses_programdata(self, monkeypatch):
        monkeypatch.delenv("ASUSFANCONTROL_SKIP_ELEVATION", raising=False)
        monkeypatch.setenv("PROGRAMDATA", r"D:\PD")
        assert config_path() == Path(r"D:\PD") / "AsusFanControlUI" / "config.json"

    def test_same_path_regardless_of_running_account(self, monkeypatch):
        monkeypatch.delenv("ASUSFANCONTROL_SKIP_ELEVATION", raising=False)
        monkeypatch.setenv("PROGRAMDATA", r"D:\PD")
        monkeypatch.setattr(Path, "home", lambda: Path(r"C:\Windows\System32\config\systemprofile"))
        as_system = config_path()
        monkeypatch.setattr(Path, "home", lambda: Path(r"C:\Users\someone"))
        assert config_path() == as_system

    def test_dev_mode_uses_the_account_profile(self, monkeypatch):
        monkeypatch.setenv("ASUSFANCONTROL_SKIP_ELEVATION", "1")
        monkeypatch.setattr(Path, "home", lambda: Path(r"C:\Users\someone"))
        assert config_path() == legacy_config_path()
        assert config_path() == Path(r"C:\Users\someone\AppData\Roaming\AsusFanControlUI\config.json")
