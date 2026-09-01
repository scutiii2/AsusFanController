from __future__ import annotations

import os
import sys

from . import elevation


def main() -> int:
    # ASUSFANCONTROL_SKIP_ELEVATION is for local dev/UI smoke-testing only —
    # fan control calls will fail without SYSTEM privilege either way.
    skip_elevation = os.environ.get("ASUSFANCONTROL_SKIP_ELEVATION") == "1"
    if not skip_elevation and not elevation.ensure_system_elevated():
        return 0  # this process relaunched itself; exit quietly

    import time

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .app_controller import AppController
    from .paths import assets_dir
    from .ui.main_window import MainWindow
    from .ui.splash import SplashScreen

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(assets_dir() / "fan.png")))

    splash = SplashScreen()
    splash.show()

    # Keep the splash's spin animation visible for a moment even if window
    # construction below is fast enough that it would otherwise flash by.
    deadline = time.monotonic() + 0.9
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    controller = AppController()
    window = MainWindow(controller)
    controller.start()
    app.aboutToQuit.connect(controller.shutdown)

    splash.finish(window)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
