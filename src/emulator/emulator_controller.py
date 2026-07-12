"""ควบคุม MuMu Emulator"""

import subprocess
import time
from pathlib import Path

from src.core.logger import get_logger

log = get_logger(__name__)


class EmulatorController:
    def __init__(self, mumu_manager_path: str):
        self.mumu_manager = mumu_manager_path
        if not self.mumu_manager or not Path(self.mumu_manager).exists():
            log.warning(f"ไม่พบ MuMuManager.exe ที่: {self.mumu_manager}")

    def close_instance(self, instance_index: int):
        """ปิด instance"""
        try:
            if not self.mumu_manager:
                log.error("ไม่พบ path ของ MuMuManager")
                return False

            # คำสั่งที่ถูกต้องสำหรับ MuMu Manager
            cmd = [self.mumu_manager, "control", "--vmindex", str(instance_index), "shutdown"]
            result = subprocess.run(cmd, capture_output=True, timeout=15, text=True, encoding="utf-8")

            if result.returncode == 0:
                log.info(f"ปิด instance {instance_index} สำเร็จ")
                return True
            else:
                log.error(f"ปิด instance ล้มเหลว (code {result.returncode}): {result.stderr}")
                return False
        except Exception as e:
            log.error(f"ปิด instance ล้มเหลว: {e}")
            return False

    def rename_instance(self, instance_index: int, new_name: str):
        """เปลี่ยนชื่อ instance"""
        try:
            cmd = [self.mumu_manager, "control", str(instance_index), "rename", new_name]
            subprocess.run(cmd, capture_output=True, timeout=10)
            log.info(f"เปลี่ยนชื่อ instance {instance_index} เป็น {new_name}")
            return True
        except Exception as e:
            log.error(f"เปลี่ยนชื่อล้มเหลว: {e}")
            return False

    def rename_instance(self, instance_index: int, new_name: str):
        """เปลี่ยนชื่อ instance"""
        try:
            cmd = [self.mumu_manager, "control", str(instance_index), "rename", new_name]
            subprocess.run(cmd, capture_output=True, timeout=10)
            log.info(f"เปลี่ยนชื่อ instance {instance_index} เป็น {new_name}")
            return True
        except Exception as e:
            log.error(f"เปลี่ยนชื่อล้มเหลว: {e}")
            return False

    def clone_instance(self, source_index: int, target_index: int = None):
        """โคลนจาก instance หลัก"""
        try:
            cmd = [self.mumu_manager, "clone", str(source_index)]
            if target_index is not None:
                cmd.extend(["--index", str(target_index)])
            subprocess.run(cmd, capture_output=True, timeout=30)
            log.info(f"โคลน instance {source_index} สำเร็จ")
            return True
        except Exception as e:
            log.error(f"โคลน instance ล้มเหลว: {e}")
            return False