"""File logging for the app: commanded fan speeds, mode changes, fail-safes."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(path: Path) -> None:
    """Log to a small rotating file. Never raises: a read-only or missing
    folder must not stop the fan controller from starting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=256 * 1024, backupCount=2, encoding="utf-8")
    except OSError:
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("asusfancontrol")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.info("Started")
