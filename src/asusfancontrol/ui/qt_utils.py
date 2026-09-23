"""Small shared Qt helpers used across widget panels."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from PySide6.QtCore import QObject


@contextmanager
def block_signals(widget: QObject) -> Iterator[None]:
    """Set a value on `widget` without re-triggering its own change signal."""
    widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(False)
