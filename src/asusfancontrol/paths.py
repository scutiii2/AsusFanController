"""Shared path to the bundled assets folder (CLI exe, driver DLL, PsExec, icon)."""

from __future__ import annotations

from pathlib import Path


def assets_dir() -> Path:
    return Path(__file__).parent / "assets"
