"""ทดสอบการปิดและควบคุม MuMu Emulator"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core import emulator_scanner
from src.core.config import Config
from src.emulator.emulator_controller import EmulatorController
from src.core.logger import get_logger, setup_logging

log = get_logger(__name__)


def main():
    setup_logging()
    config = Config.load()

    print("กำลังสแกน MuMu instances...")
    instances = emulator_scanner.scan(config)

    if not instances:
        print("ไม่พบ MuMuPlayer ที่เปิดอยู่")
        return

    print(f"พบ {len(instances)} instance:")
    for i, inst in enumerate(instances):
        print(f"  [{i}] {inst.name} -> {inst.adb_address}")

    try:
        idx = int(input("\nเลือกหมายเลข instance ที่ต้องการปิด (0-" + str(len(instances)-1) + "): "))
        if idx < 0 or idx >= len(instances):
            print("เลือกไม่ถูกต้อง")
            return
    except:
        print("กรุณากรอกตัวเลข")
        return

    inst = instances[idx]
    print(f"\nเลือก: {inst.name} ({inst.adb_address})")

    controller = EmulatorController(config.get("emulator.mumu_manager_path"))

    print(f"กำลังปิด instance {idx}...")
    success = controller.close_instance(idx)

    if success:
        print("ปิด Emulator สำเร็จ")
    else:
        print("ปิด Emulator ล้มเหลว")

    print("\nทดสอบเสร็จสิ้น")


if __name__ == "__main__":
    main()