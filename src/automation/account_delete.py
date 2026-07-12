"""Delete the current game account via Settings -> Game info."""

from __future__ import annotations

import time

from src.automation.flow_steps import button_step
from src.automation.state_machine import StepRunner
from src.core.adb_client import AdbClient
from src.core.exceptions import AutomationError, StepVerificationError
from src.core.logger import get_logger

log = get_logger(__name__)

_DEFAULT_COOLDOWN_SECONDS = 60


def build_delete_nav_steps() -> list:
    return [
        button_step("delete_enter_setting", "delete/enter_setting.png"),
        button_step("delete_game_info", "delete/game_info.png"),
        button_step("delete_account", "delete/delete_account.png", timeout=20.0),
    ]


def build_delete_confirm_steps() -> list:
    return [
        button_step(
            "delete_confirm_delete",
            "delete/confirm_delete.png",
            timeout=20.0,
        ),
        button_step(
            "delete_confirm_restart",
            "delete/confirm_restart.png",
            timeout=20.0,
        ),
    ]


class AccountDeleteController:
    def __init__(
        self,
        adb: AdbClient,
        runner: StepRunner,
        package_name: str,
        cooldown_seconds: int = _DEFAULT_COOLDOWN_SECONDS,
        control=None,
    ):
        self.adb = adb
        self.runner = runner
        self.package_name = package_name
        self.cooldown_seconds = cooldown_seconds
        self.control = control

    def delete_account(self) -> None:
        """Navigate to delete, wait for cooldown, confirm, return to login."""
        try:
            log.info("เริ่มลบบัญชี...")
            self.runner.run_sequence(build_delete_nav_steps())
            log.info(
                "รอคูลดาวน์ลบตัวละคร %d วินาที...",
                self.cooldown_seconds,
            )
            deadline = time.time() + self.cooldown_seconds
            while time.time() < deadline:
                if self.control:
                    self.control.check()
                time.sleep(1)
            self.runner.run_sequence(build_delete_confirm_steps())
            log.info("ลบบัญชีเสร็จแล้ว กลับสู่หน้า login")
        except (AutomationError, StepVerificationError):
            log.exception("ลบบัญชีผ่านหน้าเกมไม่สำเร็จ จะล้างข้อมูลแอปแทน (pm clear)")
            self.adb.clear_app_data(self.package_name)
            time.sleep(3)
