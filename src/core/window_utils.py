"""Windows-only helpers to enumerate top-level windows and their owning processes.

Used to discover MuMuPlayer windows currently open on the desktop.
"""

from __future__ import annotations

from dataclasses import dataclass

import psutil
import win32gui
import win32process


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    pid: int
    process_name: str
    rect: tuple[int, int, int, int]  # left, top, right, bottom


def _get_process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return ""


def list_visible_windows() -> list[WindowInfo]:
    """Return info for every visible, titled top-level window."""
    results: list[WindowInfo] = []

    def _callback(hwnd: int, _extra) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        results.append(
            WindowInfo(
                hwnd=hwnd,
                title=title,
                pid=pid,
                process_name=_get_process_name(pid),
                rect=rect,
            )
        )
        return True

    win32gui.EnumWindows(_callback, None)
    return results


def find_windows(
    title_filters: list[str] | None = None,
    process_name_filters: list[str] | None = None,
) -> list[WindowInfo]:
    """Filter visible windows by (case-insensitive) title substring and/or process name."""
    title_filters = [t.lower() for t in (title_filters or [])]
    process_name_filters = [p.lower() for p in (process_name_filters or [])]

    # หน้าต่างของแต่ละ instance ใน MuMuPlayer จะถูกตั้งชื่อ (title) ตามแอปที่กำลังรัน
    # อยู่ (เช่น "Cookie - 01") ไม่ใช่ "MuMuPlayer" เสมอไป ดังนั้นจับคู่แบบ OR:
    # ถือว่าตรงถ้า title หรือ process name อย่างใดอย่างหนึ่งตรงกับที่กำหนด
    matches: list[WindowInfo] = []
    for win in list_visible_windows():
        if not title_filters and not process_name_filters:
            matches.append(win)
            continue
        title_ok = bool(title_filters) and any(
            t in win.title.lower() for t in title_filters
        )
        proc_ok = (
            bool(process_name_filters)
            and win.process_name.lower() in process_name_filters
        )
        if title_ok or proc_ok:
            matches.append(win)
    return matches


def find_window_by_handle(hwnd: int) -> WindowInfo | None:
    for win in list_visible_windows():
        if win.hwnd == hwnd:
            return win
    return None
