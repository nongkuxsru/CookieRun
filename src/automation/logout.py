"""Logout the current game account via Settings -> Game info."""

from __future__ import annotations

import time

from src.automation.flow_steps import button_step
from src.automation.state_machine import StepRunner
from src.core.adb_client import AdbClient
from src.core.exceptions import AutomationError, StepVerificationError
from src.core.logger import get_logger

log = get_logger(__name__)


def build_logout_steps() -> list:
    return [
        button_step("logout_enter_setting", "logout/enter_setting.png"),
        button_step("logout_game_info", "logout/game_info.png"),
        button_step("logout_button","logout/logout_button.png",timeout=1.0,),
        button_step("submit_logout","logout/submit_logout.png",timeout=1.0,),
    ]


class AccountLogoutController:
    def __init__(
        self,
        adb: AdbClient,
        runner: StepRunner,
        package_name: str,
        control=None,
    ):
        self.adb = adb
        self.runner = runner
        self.package_name = package_name
        self.control = control

    def logout_account(self) -> None:
        """Logout the current account and return to login screen."""
        try:
            log.info("เริ่มออกจากระบบ...")

            self.runner.run_sequence(build_logout_steps())

            log.info("ออกจากระบบสำเร็จ")

        except (AutomationError, StepVerificationError):
            log.exception("ออกจากระบบไม่สำเร็จ")
            raise