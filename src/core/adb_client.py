"""Thin wrapper around the `adb` command line tool.

All game control (tap, swipe, screenshot, launching/uninstalling the app)
goes through this class so the rest of the codebase never shells out directly.
"""

from __future__ import annotations

import random
import subprocess
import time
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - cv2 is a hard requirement at runtime
    cv2 = None

from src.core.exceptions import AdbCommandError, AdbConnectionError
from src.core.logger import get_logger

log = get_logger(__name__)


class AdbClient:
    """Controls a single ADB device (one MuMuPlayer instance)."""

    def __init__(self, adb_path: str, address: str, timeout: int = 20):
        self.adb_path = adb_path
        self.address = address
        self.timeout = timeout

    # ---------------------------------------------------------------- core --
    def _run(
        self, args: list[str], timeout: int | None = None
    ) -> subprocess.CompletedProcess:
        cmd = [self.adb_path, *args]
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout or self.timeout,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            raise AdbConnectionError(
                f"เรียกคำสั่ง adb ล้มเหลว: {' '.join(cmd)} ({exc})"
            ) from exc

    def _run_on_device(
        self, args: list[str], timeout: int | None = None
    ) -> subprocess.CompletedProcess:
        return self._run(["-s", self.address, *args], timeout=timeout)

    def try_connect(self, address: str | None = None) -> bool:
        """Attempt `adb connect <address>`; returns True if a device is reachable."""
        target = address or self.address
        proc = self._run(["connect", target], timeout=8)
        output = (proc.stdout + proc.stderr).decode(errors="ignore").lower()
        connected = "connected" in output or "already connected" in output
        if connected and address:
            self.address = address
        return connected

    def connect(self) -> None:
        if not self.try_connect():
            raise AdbConnectionError(f"เชื่อมต่อ adb ไปที่ {self.address} ไม่สำเร็จ")
        log.info("เชื่อมต่อ adb สำเร็จ: %s", self.address)

    def is_device_online(self) -> bool:
        proc = self._run(["devices"], timeout=8)
        output = proc.stdout.decode(errors="ignore")
        for line in output.splitlines():
            if line.startswith(self.address) and "device" in line:
                return True
        return False

    # ------------------------------------------------------------- input --
    def tap(self, x: int, y: int) -> None:
        self._shell(f"input tap {x} {y}")

    def get_screen_size(self) -> tuple[int, int]:
        """Return (width, height) in pixels for the device display."""
        try:
            output = self._shell("wm size")
            override = physical = None
            for line in output.splitlines():
                line = line.strip()
                if "Override size:" in line:
                    override = line.split(":")[-1].strip()
                elif "Physical size:" in line:
                    physical = line.split(":")[-1].strip()
            size_str = override or physical
            if size_str and "x" in size_str:
                w, h = size_str.split("x", 1)
                return int(w), int(h)
        except AdbCommandError:
            pass

        image = self.screenshot()
        height, width = image.shape[:2]
        return width, height

    def tap_random_empty(self, margin_ratio: float = 0.12) -> tuple[int, int]:
        """Tap a random point away from screen edges (dismiss keyboard/overlays)."""
        width, height = self.get_screen_size()
        margin_x = max(int(width * margin_ratio), 1)
        margin_y = max(int(height * margin_ratio), 1)
        x = random.randint(margin_x, max(width - margin_x - 1, margin_x))
        y = random.randint(margin_y, max(height - margin_y - 1, margin_y))
        log.info("แตะพื้นที่ว่างแบบสุ่มที่ (%d, %d)", x, y)
        self.tap(x, y)
        return x, y

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        self._shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def key_event(self, keycode: int) -> None:
        self._shell(f"input keyevent {keycode}")

    def input_text(self, text: str) -> None:
        # adb input text ไม่รองรับภาษาไทย/ตัวอักษรพิเศษ ใช้ได้กับ ASCII เท่านั้น
        escaped = text.replace(" ", "%s")
        self._shell(f"input text {escaped}")

    def back(self) -> None:
        self.key_event(4)

    def enter(self) -> None:
        self.key_event(66)  # KEYCODE_ENTER

    def dismiss_input_overlay(self) -> None:
        """Dismiss MuMu/Android top input bar after ``input text`` (needs Enter)."""
        log.info("กด Enter เพื่อยืนยันข้อความและปิดแถบ input ด้านบน...")
        time.sleep(0.4)
        self.key_event(66)  # KEYCODE_ENTER
        time.sleep(0.3)
        self.key_event(66)  # some emulators need a second Enter
        time.sleep(0.2)
        self.key_event(160)  # KEYCODE_NUMPAD_ENTER fallback

    def home(self) -> None:
        self.key_event(3)

    def open_url(self, url: str) -> None:
        """Opens a URL/deep-link via the Android VIEW intent (e.g. referral links)."""
        self._shell(f'am start -a android.intent.action.VIEW -d "{url}"')

    # ------------------------------------------------------------- shell --
    def _shell(self, command: str) -> str:
        proc = self._run_on_device(["shell", command])
        if proc.returncode != 0:
            raise AdbCommandError(
                f"คำสั่ง adb shell ล้มเหลว: {command}\n{proc.stderr.decode(errors='ignore')}"
            )
        return proc.stdout.decode(errors="ignore")

    def shell(self, command: str) -> str:
        return self._shell(command)

    # --------------------------------------------------------- screenshot --
    def screenshot(self) -> np.ndarray:
        """Capture the current screen as a BGR numpy array (OpenCV format)."""
        if cv2 is None:
            raise RuntimeError("ต้องติดตั้ง opencv-python ก่อนใช้งานฟังก์ชันนี้")

        proc = self._run_on_device(["exec-out", "screencap", "-p"], timeout=15)
        if proc.returncode != 0 or not proc.stdout:
            raise AdbCommandError("ถ่ายภาพหน้าจอผ่าน adb ไม่สำเร็จ")

        img_array = np.frombuffer(proc.stdout, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if image is None:
            raise AdbCommandError("แปลงข้อมูลภาพหน้าจอไม่สำเร็จ (ข้อมูลอาจเสียหาย)")
        return image

    def save_screenshot(self, path: str | Path) -> Path:
        image = self.screenshot()  # raises RuntimeError if cv2 is unavailable
        assert cv2 is not None
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), image)
        return path

    # -------------------------------------------------------------- apps --
    def start_app(self, package_name: str, activity: str | None = None) -> None:
        if activity:
            self._shell(f"am start -n {package_name}/{activity}")
        else:
            self._shell(
                f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
            )

    def bring_to_foreground(
        self, package_name: str, activity: str | None = None, settle_seconds: float = 3.0
    ) -> None:
        """Resume/bring the app to the front without force-stopping it."""
        log.info("นำเกม %s มาหน้าแรก (ไม่ปิดแอป)...", package_name)
        self.start_app(package_name, activity)
        if settle_seconds:
            time.sleep(settle_seconds)

    def stop_app(self, package_name: str) -> None:
        self._shell(f"am force-stop {package_name}")

    def clear_app_data(self, package_name: str) -> None:
        """Wipes local save data - used as the 'delete account' fallback for guest/dev accounts."""
        self._shell(f"pm clear {package_name}")

    def uninstall_app(self, package_name: str) -> None:
        self._run_on_device(["uninstall", package_name])

    def is_app_running(self, package_name: str) -> bool:
        output = self._shell(f"pidof {package_name} 2>/dev/null || true").strip()
        if output:
            return True
        output = self._shell("dumpsys window | grep mCurrentFocus || true")
        return package_name in output

    def wait_for_boot_complete(self, timeout: int = 60) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                result = self._shell("getprop sys.boot_completed").strip()
                if result == "1":
                    return True
            except AdbCommandError:
                pass
            time.sleep(1)
        return False
