"""Discovers running MuMuPlayer instances and resolves them to ADB addresses.

Strategy (best to worst):
1. Locate MuMuManager.exe (bundled with MuMu Player 12+) and query
   ``MuMuManager.exe info -v all`` for a JSON dump of every instance,
   including its adb_host_ip / adb_port / window handle / running state.
2. Cross-reference each instance's window handle with the live Windows
   window list (title/process filters from config) so the user can see
   which visible window corresponds to which instance.
3. If MuMuManager.exe cannot be found (older MuMu, non-standard install),
   fall back to scanning the well-known MuMu ADB port range
   (16384, 16416, 16448, ... by default) and probing each with
   ``adb connect``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import winreg
from dataclasses import dataclass, field
from pathlib import Path

from src.core.logger import get_logger
from src.core.window_utils import WindowInfo, find_windows, list_visible_windows

log = get_logger(__name__)

_COMMON_MUMU_MANAGER_PATHS = [
    r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\MuMuManager.exe",
    r"C:\Program Files\Netease\MuMu Player 12\shell\MuMuManager.exe",
    r"C:\Program Files\Netease\MuMuPlayer-12.0\nx_main\MuMuManager.exe",
    r"C:\Program Files\Netease\MuMu Player 12\nx_main\MuMuManager.exe",
]

_COMMON_ADB_RELATIVE_PATHS = [
    "adb.exe",
    r"..\shell\adb.exe",
    r"..\nx_main\adb.exe",
    r"vmonitor\bin\adb_server.exe",
]


@dataclass
class EmulatorInstance:
    """A resolved MuMuPlayer instance ready to be adb-connected to."""

    index: int
    name: str
    adb_address: str  # e.g. "127.0.0.1:16384"
    is_android_started: bool
    window: WindowInfo | None = None
    raw: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        win_part = (
            f" | หน้าต่าง: {self.window.title}" if self.window else " | (ไม่พบหน้าต่าง)"
        )
        state = "รันอยู่" if self.is_android_started else "ยังไม่ได้เปิด Android"
        return f"[{self.index}] {self.name} -> {self.adb_address} ({state}){win_part}"


def _find_mumu_manager(configured_path: str | None) -> Path | None:
    if configured_path:
        p = Path(configured_path)
        if p.exists():
            return p
        log.warning("ระบุ mumu_manager_path ไว้แต่ไม่พบไฟล์: %s", p)

    for candidate in _COMMON_MUMU_MANAGER_PATHS:
        p = Path(candidate)
        if p.exists():
            return p

    # ค้นหาผ่าน Windows Registry (Uninstall keys) ที่มีคำว่า MuMu
    for hive, subkey in (
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
    ):
        try:
            with winreg.OpenKey(hive, subkey) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    sub_name = winreg.EnumKey(key, i)
                    try:
                        with winreg.OpenKey(key, sub_name) as sub:
                            display_name = winreg.QueryValueEx(sub, "DisplayName")[0]
                            if "mumu" not in display_name.lower():
                                continue
                            install_loc = winreg.QueryValueEx(sub, "InstallLocation")[0]
                    except (OSError, FileNotFoundError):
                        continue
                    for rel in ("shell/MuMuManager.exe", "nx_main/MuMuManager.exe"):
                        p = Path(install_loc) / rel
                        if p.exists():
                            return p
        except OSError:
            continue

    return None


def _find_adb_executable(configured_path: str | None, mumu_manager: Path | None) -> str:
    if configured_path and Path(configured_path).exists():
        return configured_path

    on_path = shutil.which("adb")
    if on_path:
        return on_path

    if mumu_manager:
        base = mumu_manager.parent
        for rel in _COMMON_ADB_RELATIVE_PATHS:
            candidate = (base / rel).resolve()
            if candidate.exists():
                return str(candidate)

    log.warning(
        "ไม่พบ adb.exe โดยอัตโนมัติ กรุณาระบุ emulator.adb_path ใน config.yaml "
        "หรือติดตั้ง Android platform-tools แล้วเพิ่มลง PATH"
    )
    return "adb"  # last resort, will fail loudly later if truly missing


def _query_mumu_manager_instances(mumu_manager: Path) -> list[dict]:
    try:
        proc = subprocess.run(
            [str(mumu_manager), "info", "-v", "all"],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="ignore",
        )
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("เรียก MuMuManager.exe ไม่สำเร็จ: %s", exc)
        return []

    if proc.returncode != 0 or not proc.stdout.strip():
        log.warning("MuMuManager.exe ไม่คืนข้อมูล (returncode=%s)", proc.returncode)
        return []

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        log.warning("แปลงผลลัพธ์ JSON จาก MuMuManager.exe ไม่ได้")
        return []

    # ผลลัพธ์อาจเป็น dict เดียว (instance เดียว) หรือ dict ของหลาย index
    if isinstance(data, dict) and "index" in data:
        return [data]
    if isinstance(data, dict):
        return [v for v in data.values() if isinstance(v, dict)]
    if isinstance(data, list):
        return data
    return []


def _match_window_for_instance(
    info: dict, windows: list[WindowInfo]
) -> WindowInfo | None:
    main_wnd_hex = info.get("main_wnd")
    if main_wnd_hex:
        try:
            hwnd = int(str(main_wnd_hex), 16)
        except ValueError:
            hwnd = None
        if hwnd:
            for win in windows:
                if win.hwnd == hwnd:
                    return win

    # fallback: match by pid (shell process)
    pid = info.get("pid")
    if pid:
        for win in windows:
            if win.pid == pid:
                return win
    return None


def scan_via_mumu_manager(config) -> list[EmulatorInstance]:
    """Primary discovery path using MuMuManager.exe."""
    mumu_manager = _find_mumu_manager(config.get("emulator.mumu_manager_path"))
    if not mumu_manager:
        log.info("ไม่พบ MuMuManager.exe จะใช้วิธีสแกนพอร์ตสำรองแทน")
        return []

    log.info("พบ MuMuManager.exe ที่: %s", mumu_manager)
    raw_instances = _query_mumu_manager_instances(mumu_manager)
    if not raw_instances:
        return []

    # ใช้รายการหน้าต่างทั้งหมด (ไม่กรองด้วย title/process) เพราะหน้าต่างของแต่ละ
    # instance จะถูกตั้งชื่อตามแอปที่กำลังรันอยู่ (เช่น "Cookie - 01") ไม่ใช่ "MuMuPlayer"
    # เสมอไป - จับคู่ที่แม่นยำกว่าคือใช้ main_wnd handle / pid จาก MuMuManager แทน
    windows = list_visible_windows()

    results: list[EmulatorInstance] = []
    for info in raw_instances:
        adb_ip = info.get("adb_host_ip")
        adb_port = info.get("adb_port")
        is_started = bool(info.get("is_android_started"))
        if not (adb_ip and adb_port):
            # instance is not running -> no adb address available yet
            continue
        results.append(
            EmulatorInstance(
                index=int(info.get("index", -1)),
                name=info.get("name", f"MuMu-{info.get('index', '?')}"),
                adb_address=f"{adb_ip}:{adb_port}",
                is_android_started=is_started,
                window=_match_window_for_instance(info, windows),
                raw=info,
            )
        )
    return results


def scan_via_port_fallback(config) -> list[EmulatorInstance]:
    """Fallback discovery: probe the conventional MuMu ADB port range directly."""
    from src.core.adb_client import AdbClient  # local import to avoid cycle

    adb_path = _find_adb_executable(config.get("emulator.adb_path"), None)
    port_base = int(config.get("emulator.fallback_port_base", 16384))
    port_step = int(config.get("emulator.fallback_port_step", 32))
    max_instances = int(config.get("emulator.fallback_max_instances", 8))

    windows = find_windows(
        title_filters=config.get("emulator.window_title_filters"),
        process_name_filters=config.get("emulator.process_name_filters"),
    )

    client = AdbClient(adb_path=adb_path, address="")
    results: list[EmulatorInstance] = []
    for idx in range(max_instances):
        port = port_base + idx * port_step
        address = f"127.0.0.1:{port}"
        if client.try_connect(address):
            results.append(
                EmulatorInstance(
                    index=idx,
                    name=f"MuMuPlayer-{idx}",
                    adb_address=address,
                    is_android_started=True,
                    window=windows[idx] if idx < len(windows) else None,
                    raw={},
                )
            )
    return results


def scan(config) -> list[EmulatorInstance]:
    """Run the full discovery pipeline."""
    instances = scan_via_mumu_manager(config)
    
    if len(instances) < 3:   # ถ้าเจอน้อยเกินไป ให้ลอง fallback
        log.info("พบ instance น้อย ใช้โหมด fallback เพิ่ม")
        fallback_instances = scan_via_port_fallback(config)
        # รวมและ deduplicate ตาม adb_address
        seen = {inst.adb_address for inst in instances}
        for inst in fallback_instances:
            if inst.adb_address not in seen:
                instances.append(inst)
                seen.add(inst.adb_address)

    if not instances:
        log.warning("ไม่พบ MuMuPlayer ที่เปิดอยู่เลย")
    else:
        log.info(f"พบ MuMuPlayer ทั้งหมด {len(instances)} instance")
        for inst in instances:
            log.info(inst.display_name)

    return instances


def resolve_adb_path(config) -> str:
    mumu_manager = _find_mumu_manager(config.get("emulator.mumu_manager_path"))
    return _find_adb_executable(config.get("emulator.adb_path"), mumu_manager)
