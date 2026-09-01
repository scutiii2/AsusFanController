"""Entry point for both `python run.py` (dev) and the PyInstaller build."""

import sys

from asusfancontrol.main import main

if __name__ == "__main__":
    sys.exit(main())
