"""Tests for the parts of system_launch that don't spawn a SYSTEM process.

The actual launch needs an elevated Administrator and real hardware, so it's
verified by hand, not here. These cover the ctypes bindings loading and the
error mapping.
"""

import ctypes

import pytest

system_launch = pytest.importorskip(
    "asusfancontrol.system_launch",
    reason="Windows-only (ctypes.WinDLL)",
)


class TestBindings:
    def test_import_binds_handle_returning_functions_to_handle(self):
        # If _bind() didn't run, restype would still be the default c_int,
        # which truncates 64-bit handles.
        from ctypes import wintypes

        assert system_launch.kernel32.OpenProcess.restype is wintypes.HANDLE
        assert system_launch.advapi32.CreateProcessWithTokenW.restype is wintypes.BOOL


class TestErrorMapping:
    def test_win_error_includes_call_name_and_code(self, monkeypatch):
        monkeypatch.setattr(ctypes, "get_last_error", lambda: 5)
        err = system_launch._win_error("OpenProcess")
        assert isinstance(err, system_launch.SystemLaunchError)
        assert "OpenProcess" in str(err)
        assert "5" in str(err)
