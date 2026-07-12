"""CLI: interactive helper to build template images from a live screenshot.

This addresses requirement #4 ("กำหนดรูปตามลำดับ") - it lets you take a
screenshot from a connected instance, then drag a rectangle around any
button/screen element and save it straight into templates/<category>/name.png
so game_flow.py / pet_reroll.py can reference it.

Usage (from the CookieRun/ root directory):
    python tools/calibrate.py --instance 0 --category login --name dev_mode_button
"""

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
    parser = argparse.ArgumentParser(
        description="ตัดรูป template จากภาพหน้าจอจริงของ MuMuPlayer"
    )
    parser.add_argument(
        "--instance",
        type=int,
        default=0,
        help="ลำดับ instance ที่ต้องการเชื่อมต่อ (ดูจาก tools/list_instances.py)",
    )
    parser.add_argument(
        "--category",
        required=True,
        help="โฟลเดอร์ย่อยใน templates/ เช่น login, pet_reroll",
    )
    parser.add_argument("--name", required=True, help="ชื่อไฟล์ (ไม่ต้องมี .png)")
    args = parser.parse_args()

    setup_logging()
    config = Config.load()

    instances = emulator_scanner.scan(config)
    if not instances:
        print("ไม่พบ MuMuPlayer ที่เปิดอยู่ กรุณาเปิดโปรแกรมจำลองก่อน")
        return
    if args.instance >= len(instances):
        print(f"ไม่พบ instance ลำดับที่ {args.instance} (พบทั้งหมด {len(instances)} ตัว)")
        return

    inst = instances[args.instance]
    adb_path = emulator_scanner.resolve_adb_path(config)
    adb = AdbClient(adb_path=adb_path, address=inst.adb_address)
    adb.connect()

    print("กำลังถ่ายภาพหน้าจอปัจจุบัน...")
    screenshot = adb.screenshot()

    print("\nลากกรอบรอบปุ่ม/หน้าจอที่ต้องการ แล้วกด ENTER หรือ SPACE เพื่อยืนยัน (กด c เพื่อยกเลิก)\n")
    x, y, w, h = cv2.selectROI(
        "เลือกพื้นที่ template - กด ENTER เมื่อเสร็จ", screenshot, showCrosshair=True
    )
    cv2.destroyAllWindows()

    if w == 0 or h == 0:
        print("ยกเลิกการเลือกพื้นที่ ไม่มีการบันทึกไฟล์")
        return

    cropped = screenshot[y : y + h, x : x + w]

    templates_root = Path(config.get("templates.root_dir", "templates"))
    out_dir = templates_root / args.category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.png"
    cv2.imwrite(str(out_path), cropped)

    print(f"\nบันทึก template ไว้ที่: {out_path}")
    print(f"พิกัดบนภาพต้นฉบับ: x={x}, y={y}, w={w}, h={h}")


if __name__ == "__main__":
    main()
