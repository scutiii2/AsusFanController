"""Shared filesystem locations: bundled assets and the config file."""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "AsusFanControlUI"


def assets_dir() -> Path:
    return Path(__file__).parent / "assets"


def config_path() -> Path:
    # The elevated app runs as SYSTEM, whose home folder is the systemprofile,
    # not the signed-in user's. ProgramData is the same for every account, so
    # all launches share one config. Dev mode runs unelevated and can't write
    # to a ProgramData folder SYSTEM created, so it keeps its own copy.
    if os.environ.get("ASUSFANCONTROL_SKIP_ELEVATION") == "1":
        return legacy_config_path()
    base = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    return base / APP_DIR_NAME / "config.json"


def legacy_config_path() -> Path:
    """Where older versions saved config: under the running account's home."""
    return Path.home() / "AppData" / "Roaming" / APP_DIR_NAME / "config.json"
