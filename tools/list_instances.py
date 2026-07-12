"""CLI: scan for open MuMuPlayer windows / running instances and print their
resolved ADB address, so you can confirm detection works before running the
full automation.

Usage (from the CookieRun/ root directory):
    python tools/list_instances.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core import emulator_scanner
from src.core.config import Config
from src.core.logger import get_logger, setup_logging

log = get_logger(__name__)


def main() -> None:
    setup_logging()
    config = Config.load()
    instances = emulator_scanner.scan(config)

    if not instances:
        print("ไม่พบ MuMuPlayer ที่เปิดอยู่")
        return

    print("\nพบ MuMuPlayer instance ทั้งหมด:")
    for inst in instances:
        print(f"  {inst.display_name}")


if __name__ == "__main__":
    main()
