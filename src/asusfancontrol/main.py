from __future__ import annotations

import os
import sys

from . import elevation


def _driver_check() -> int:
    """Write a driver-diagnostics log (no GUI) and exit. Runs as SYSTEM after
    the elevation chain, so it reports what the real app sees."""
    import glob

    from . import fan_control
    from .paths import assets_dir, config_path

    lines = [
        f"whoami env USERNAME: {os.environ.get('USERNAME')}",
        f"frozen: {getattr(sys, 'frozen', False)}",
        f"assets_dir: {assets_dir()}",
        f"driver store glob: {fan_control._DRIVER_STORE_GLOB}",
        f"glob matches: {glob.glob(fan_control._DRIVER_STORE_GLOB)}",
    ]
    try:
        fan_control.ensure_driver_library()
        lines.append(f"ensure_driver_library: OK, dll at {assets_dir() / fan_control._DRIVER_DLL_NAME}")
        lines.append(f"get_fan_count: {fan_control.get_fan_count()}")
    except Exception as exc:  # noqa: BLE001 - diagnostic, report everything
        lines.append(f"ERROR: {type(exc).__name__}: {exc}")

    log = config_path().parent / "driver_check.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass
    return 0


def main() -> int:
    # ASUSFANCONTROL_SKIP_ELEVATION is for local dev/UI smoke-testing only —
    # fan control calls will fail without SYSTEM privilege either way.
    skip_elevation = os.environ.get("ASUSFANCONTROL_SKIP_ELEVATION") == "1"
    if not skip_elevation and not elevation.ensure_system_elevated():
        return 0  # this process relaunched itself; exit quietly

    if "--driver-check" in sys.argv:
        return _driver_check()

    import time

    from PySide6.QtCore import QSharedMemory
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .app_controller import CONFIG_PATH, AppController
    from .config import migrate_legacy_config
    from .paths import assets_dir, legacy_config_path
    from .ui.main_window import MainWindow
    from .ui.splash import SplashScreen

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(assets_dir() / "fan.png")))

    # Single-instance guard: closing the window minimizes to tray rather
    # than quitting, so it's easy to end up with a stray background
    # instance. A second launch would then issue its own, possibly
    # conflicting, fan-speed commands alongside it. Kept alive for the
    # whole process lifetime as a local (main() doesn't return until
    # app.exec() finishes) — its OS-level segment is released automatically
    # when this process exits.
    single_instance_lock = QSharedMemory("AsusFanControlUI-single-instance-9f3a2b1c")
    if not single_instance_lock.create(1):
        QMessageBox.information(
            None,
            "ASUS FAN CONTROLLER",
            "ASUS Fan Controller is already running — check your system tray.",
        )
        return 0

    splash = SplashScreen()
    splash.show()

    # Keep the splash's spin animation visible for a moment even if window
    # construction below is fast enough that it would otherwise flash by.
    deadline = time.monotonic() + 0.9
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    try:
        migrate_legacy_config(CONFIG_PATH, legacy_config_path())
    except OSError:
        pass  # a failed copy just means starting from defaults, as before

    # Put AsusWinIO64.dll beside the CLI before the worker makes its first
    # call. A missing driver library is a clear, actionable message rather
    # than an opaque CLI failure on every poll.
    from . import fan_control

    try:
        fan_control.ensure_driver_library()
    except fan_control.FanControlError as exc:
        QMessageBox.warning(None, "ASUS FAN CONTROLLER", str(exc))

    controller = AppController()
    window = MainWindow(controller)
    controller.start()
    app.aboutToQuit.connect(controller.shutdown)

    splash.finish(window)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
