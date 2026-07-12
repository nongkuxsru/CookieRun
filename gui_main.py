"""Entry point for the "PD Bot Game - Cookie run" desktop GUI.

Run directly with:
    python gui_main.py

Or build a standalone .exe with PyInstaller - see build_exe.bat / README.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

# When frozen by PyInstaller, make sure relative paths (config/, templates/,
# logs/, data_output/) resolve next to the .exe instead of a temp extraction dir.
if getattr(sys, "frozen", False):
    _base_dir = Path(sys.executable).resolve().parent
else:
    _base_dir = Path(__file__).resolve().parent

sys.path.insert(0, str(_base_dir))
import os

os.chdir(_base_dir)

from src.gui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
