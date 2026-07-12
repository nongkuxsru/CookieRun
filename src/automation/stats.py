"""Thread-safe run counters shared across all instance worker threads.

Mirrors the 4 numbers shown in the GUI's "สถานะงาน" panel:
เริ่ม (started) / สำเร็จ (success) / ไม่สำเร็จ (failed) / เหลือ (remaining).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class RunStats:
    target: int = 0
    started: int = 0
    success: int = 0
    failed: int = 0
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    def set_target(self, target: int) -> None:
        with self._lock:
            self.target = max(int(target), 0)

    def try_reserve_slot(self) -> bool:
        """Atomically check remaining>0 and reserve it by incrementing `started`.

        Returns False once the configured target has been reached, signaling
        the calling worker thread to stop picking up new accounts.
        """
        with self._lock:
            if self.target and self.started >= self.target:
                return False
            self.started += 1
            return True

    def record_success(self) -> None:
        with self._lock:
            self.success += 1

    def record_failed(self) -> None:
        with self._lock:
            self.failed += 1

    def snapshot(self) -> tuple[int, int, int, int]:
        """Returns (started, success, failed, remaining)."""
        with self._lock:
            remaining = max(self.target - self.started, 0)
            return self.started, self.success, self.failed, remaining

    def reset(self) -> None:
        with self._lock:
            self.started = 0
            self.success = 0
            self.failed = 0
