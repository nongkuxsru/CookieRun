"""CLI: interactive helper to build template images from a live screenshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from src.core import emulator_scanner
from src.core.adb_client import AdbClient
from src.core.config import Config
from src.core.logger import get_logger, setup_logging

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="ตัดรูป template จากภาพหน้าจอ MuMuPlayer")
    parser.add_argument("--category", required=True, help="โฟลเดอร์ย่อยใน templates/ เช่น login, pet_reroll, treasure_reroll")
    parser.add_argument("--name", required=True, help="ชื่อไฟล์ template (ไม่ต้องมี .png)")
    args = parser.parse_args()

    setup_logging()
    config = Config.load()

    print("กำลังสแกนหา MuMuPlayer instances...")
    instances = emulator_scanner.scan(config)

    if not instances:
        print("❌ ไม่พบ MuMuPlayer ที่เปิดอยู่ กรุณาเปิดโปรแกรมจำลองก่อน")
        return

    print(f"\nพบ {len(instances)} instance:")
    for i, inst in enumerate(instances):
        window = inst.window.title if inst.window else "ไม่พบหน้าต่าง"
        print(f"  [{i}] {inst.name} → {inst.adb_address} | {window}")

    # ให้ผู้ใช้เลือก
    while True:
        try:
            choice = input("\nเลือกหมายเลข instance ที่ต้องการ (0-" + str(len(instances)-1) + "): ")
            idx = int(choice)
            if 0 <= idx < len(instances):
                break
            print("กรุณาเลือกตัวเลขที่ถูกต้อง")
        except ValueError:
            print("กรุณากรอกตัวเลข")

    inst = instances[idx]
    print(f"\n✅ เลือก: {inst.name} ({inst.adb_address})")

    adb_path = emulator_scanner.resolve_adb_path(config)
    adb = AdbClient(adb_path=adb_path, address=inst.adb_address)
    
    try:
        adb.connect()
    except Exception as e:
        print(f"❌ เชื่อมต่อ ADB ไม่สำเร็จ: {e}")
        return

    print("📸 กำลังถ่ายภาพหน้าจอปัจจุบัน...")
    screenshot = adb.screenshot()

    print("\nลากกรอบรอบปุ่ม/หน้าจอที่ต้องการ แล้วกด ENTER หรือ SPACE เพื่อยืนยัน (กด c เพื่อยกเลิก)")
    x, y, w, h = cv2.selectROI(
        f"เลือกพื้นที่ template - {inst.name}", screenshot, showCrosshair=True
    )
    cv2.destroyAllWindows()

    if w == 0 or h == 0:
        print("❌ ยกเลิกการเลือกพื้นที่")
        return

    cropped = screenshot[y:y+h, x:x+w]

    templates_root = Path(config.get("templates.root_dir", "templates"))
    out_dir = templates_root / args.category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.png"

    cv2.imwrite(str(out_path), cropped)

    print(f"\n✅ บันทึก template สำเร็จ!")
    print(f"   ที่: {out_path}")
    print(f"   ขนาด: {w}x{h} pixels")


if __name__ == "__main__":
    main()