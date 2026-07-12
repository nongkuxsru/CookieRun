"""CSV logging for automation results: pets found and accounts exhausted/failed.

Kept intentionally simple (stdlib csv) so it's easy to open in Excel/Sheets.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock


@dataclass
class Recorder:
    output_dir: Path
    _lock: Lock = field(default_factory=Lock)

    def __post_init__(self):
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.found_pets_path = self.output_dir / "found_pets.csv"
        self.failed_accounts_path = self.output_dir / "failed_accounts.csv"
        self._ensure_header(
            self.found_pets_path,
            ["timestamp", "account_id", "pet_name", "screenshot", "note"],
        )
        self._ensure_header(
            self.failed_accounts_path,
            ["timestamp", "account_id", "reason", "screenshot"],
        )

    @staticmethod
    def _ensure_header(path: Path, header: list[str]) -> None:
        if not path.exists():
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow(header)

    def record_found_pet(
        self, account_id: str, pet_name: str, screenshot: str = "", note: str = "", treasures: str = "" 
    ) -> None:
        with self._lock:
            with open(self.found_pets_path, "a", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow(
                    [
                        datetime.now().isoformat(timespec="seconds"),
                        account_id,
                        pet_name,
                        screenshot,
                        note,
                        treasures
                    ]
                )

    def record_failed_account(
        self, account_id: str, reason: str = "เพชรหมด", screenshot: str = ""
    ) -> None:
        with self._lock:
            with open(
                self.failed_accounts_path, "a", newline="", encoding="utf-8-sig"
            ) as f:
                csv.writer(f).writerow(
                    [
                        datetime.now().isoformat(timespec="seconds"),
                        account_id,
                        reason,
                        screenshot,
                    ]
                )

    def record_new_account(
        self, account_id: str, path: str | Path = "data_output/new_accounts.txt"
    ) -> None:
        """บันทึกไอดีที่สมัครใหม่ลงไฟล์ข้อความเดียว เพื่อนำไปใช้งานอื่นต่อได้

        NOTE: account_id จะเป็น placeholder (timestamp) จนกว่าจะมีข้อมูลวิทีอ่าน UID จริงจากหน้าจอเกม
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with open(target, "a", encoding="utf-8") as f:
                f.write(
                    f"{datetime.now().isoformat(timespec='seconds')}\t{account_id}\n"
                )
