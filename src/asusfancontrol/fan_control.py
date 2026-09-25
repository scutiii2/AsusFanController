"""Fan and temperature access through ASUS's AsusWinIO64.dll.

The DLL talks to the embedded controller through ASUS's kernel driver, which
only answers a SYSTEM-level process (see system_launch.py). The call sequences
here mirror what the AsusFanControl CLI does, without spawning it: selecting a
fan, enabling test mode, then writing a PWM duty for it.

Layering: `WinIoLibrary` is the small interface the rest needs, implemented for
real by `CtypesWinIoLibrary`; `FanController` holds the logic and takes the
library as a dependency, so it is unit-tested with a fake. The module-level
functions are the API the rest of the app calls.
"""

from __future__ import annotations

import atexit
import ctypes
import glob
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, Protocol

from .paths import assets_dir

# AsusWinIO64.dll is (c) ASUSTeK and not ours to redistribute, so it is not
# bundled. MyASUS (the ASUS System Control Interface) installs it in the driver
# store; it is loaded from the assets folder, so copy it in on first use.
_DRIVER_DLL_NAME = "AsusWinIO64.dll"
_DRIVER_STORE_GLOB = (
    r"C:\Windows\System32\DriverStore\FileRepository"
    r"\asussci2.inf_amd64_*\ASUSSystemAnalysis\AsusWinIO64.dll"
)

# The CLI pauses this long between fans when writing them all, giving the EC
# time to settle before the next fan index is selected.
_INTER_FAN_DELAY_S = 0.02


class FanControlError(Exception):
    """Raised when the driver library can't be loaded or reports a failure."""


def ensure_driver_library() -> None:
    """Copy AsusWinIO64.dll into the assets folder if it isn't there yet.

    Raises FanControlError if MyASUS isn't installed, so it can't be found.
    """
    target = assets_dir() / _DRIVER_DLL_NAME
    if target.exists():
        return
    matches = sorted(glob.glob(_DRIVER_STORE_GLOB))
    if not matches:
        raise FanControlError(
            f"{_DRIVER_DLL_NAME} not found in the driver store. Install MyASUS "
            "(the ASUS System Control Interface) so the fan driver is available."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(matches[0], target)


class WinIoLibrary(Protocol):
    """The subset of AsusWinIO64.dll this app uses."""

    def initialize(self) -> None: ...

    def shutdown(self) -> None: ...

    def fan_count(self) -> int: ...

    def select_fan(self, index: int) -> None: ...

    def fan_rpm(self) -> int:
        """RPM of the fan chosen with select_fan."""
        ...

    def set_test_mode(self, enabled: bool) -> None: ...

    def set_pwm_duty(self, duty: int) -> None:
        """PWM duty 0-255 for the fan chosen with select_fan."""
        ...

    def cpu_temp(self) -> int: ...


class CtypesWinIoLibrary:
    """`WinIoLibrary` backed by the real DLL, loaded with ctypes."""

    def __init__(self, path: Path) -> None:
        if not path.exists():
            raise FanControlError(
                f"{path.name} not found in {path.parent}. Install MyASUS "
                "(the ASUS System Control Interface) so the fan driver is available."
            )
        # Signatures come from the CLI's own P/Invoke declarations.
        self._dll = dll = ctypes.WinDLL(str(path))
        dll.InitializeWinIo.restype = ctypes.c_int
        dll.InitializeWinIo.argtypes = []
        dll.ShutdownWinIo.restype = ctypes.c_int
        dll.ShutdownWinIo.argtypes = []
        dll.HealthyTable_FanCounts.restype = ctypes.c_int
        dll.HealthyTable_FanCounts.argtypes = []
        dll.HealthyTable_SetFanIndex.restype = None
        dll.HealthyTable_SetFanIndex.argtypes = [ctypes.c_ubyte]
        dll.HealthyTable_FanRPM.restype = ctypes.c_int
        dll.HealthyTable_FanRPM.argtypes = []
        dll.HealthyTable_SetFanTestMode.restype = None
        dll.HealthyTable_SetFanTestMode.argtypes = [ctypes.c_ubyte]
        dll.HealthyTable_SetFanPwmDuty.restype = None
        dll.HealthyTable_SetFanPwmDuty.argtypes = [ctypes.c_int16]
        dll.Thermal_Read_Cpu_Temperature.restype = ctypes.c_uint64
        dll.Thermal_Read_Cpu_Temperature.argtypes = []

    def initialize(self) -> None:
        self._dll.InitializeWinIo()

    def shutdown(self) -> None:
        self._dll.ShutdownWinIo()

    def fan_count(self) -> int:
        return int(self._dll.HealthyTable_FanCounts())

    def select_fan(self, index: int) -> None:
        self._dll.HealthyTable_SetFanIndex(index)

    def fan_rpm(self) -> int:
        return int(self._dll.HealthyTable_FanRPM())

    def set_test_mode(self, enabled: bool) -> None:
        self._dll.HealthyTable_SetFanTestMode(1 if enabled else 0)

    def set_pwm_duty(self, duty: int) -> None:
        self._dll.HealthyTable_SetFanPwmDuty(duty)

    def cpu_temp(self) -> int:
        return int(self._dll.Thermal_Read_Cpu_Temperature())


def pct_to_duty(pct: int) -> int:
    """0-100 % to the 0-255 PWM duty the EC takes (the CLI truncates)."""
    return pct * 255 // 100


class FanController:
    """Reads and writes fans through a `WinIoLibrary`.

    The library is loaded and initialised on first use. Selecting a fan and
    writing to it are separate calls on shared driver state, so every public
    method holds one lock: the worker thread and the shutdown path may both
    call in.
    """

    def __init__(self, load_library: Callable[[], WinIoLibrary], inter_fan_delay_s: float = _INTER_FAN_DELAY_S) -> None:
        self._load_library = load_library
        self._inter_fan_delay_s = inter_fan_delay_s
        self._library: WinIoLibrary | None = None
        self._lock = threading.RLock()

    def _lib(self) -> WinIoLibrary:
        # Caller holds the lock.
        if self._library is None:
            try:
                library = self._load_library()
            except OSError as exc:
                raise FanControlError(f"Could not load {_DRIVER_DLL_NAME}: {exc}") from exc
            library.initialize()
            self._library = library
        return self._library

    def get_fan_count(self) -> int:
        with self._lock:
            count = self._lib().fan_count()
        if count < 0:
            raise FanControlError(f"Fan control unavailable (fan count {count}) — is the app running as SYSTEM?")
        return count

    def get_cpu_temp(self) -> int:
        with self._lock:
            temp = self._lib().cpu_temp()
        # The driver answers 0 when it can't read the sensor (e.g. not SYSTEM).
        # No real CPU sits at 0 C, and a fake 0 would drive a fan curve to its
        # quietest speed, so report it as a failure instead.
        if temp <= 0:
            raise FanControlError("CPU temperature unavailable — is the app running as SYSTEM?")
        return temp

    def get_fan_speeds(self) -> list[int]:
        with self._lock:
            count = self.get_fan_count()
            library = self._lib()
            speeds = []
            for fan_id in range(count):
                library.select_fan(fan_id)
                speeds.append(library.fan_rpm())
            return speeds

    def set_fan_speed(self, fan_id: int, pct: int) -> None:
        if not 0 <= pct <= 100:
            raise ValueError(f"pct must be 0-100, got {pct}")
        if not 0 <= fan_id <= 255:
            raise ValueError(f"fan_id must be 0-255, got {fan_id}")
        with self._lock:
            self._write_duty(self._lib(), fan_id, pct_to_duty(pct))

    def set_auto(self) -> None:
        """Hand every fan back to the EC (duty 0, test mode off)."""
        with self._lock:
            count = self.get_fan_count()
            library = self._lib()
            for fan_id in range(count):
                if fan_id:
                    time.sleep(self._inter_fan_delay_s)
                self._write_duty(library, fan_id, 0)

    def shutdown(self) -> None:
        with self._lock:
            if self._library is not None:
                self._library.shutdown()
                self._library = None

    @staticmethod
    def _write_duty(library: WinIoLibrary, fan_id: int, duty: int) -> None:
        library.select_fan(fan_id)
        library.set_test_mode(duty > 0)
        library.set_pwm_duty(duty)


def _load_default_library() -> WinIoLibrary:
    return CtypesWinIoLibrary(assets_dir() / _DRIVER_DLL_NAME)


_default = FanController(_load_default_library)
atexit.register(_default.shutdown)


def get_fan_count() -> int:
    return _default.get_fan_count()


def get_cpu_temp() -> int:
    return _default.get_cpu_temp()


def get_fan_speeds() -> list[int]:
    return _default.get_fan_speeds()


def set_fan_speed(fan_id: int, pct: int) -> None:
    _default.set_fan_speed(fan_id, pct)


def set_auto() -> None:
    _default.set_auto()
