"""'ปั้มทำใจ-ชวนเพื่อน' (referral pump) loop."""

from __future__ import annotations

from src.automation.account_delete import AccountDeleteController
from src.automation.game_flow import GameFlow
from src.automation.state_machine import StepRunner
from src.core.adb_client import AdbClient
from src.core.logger import get_logger

log = get_logger(__name__)


class ReferralPumpController:
    def __init__(
        self,
        adb: AdbClient,
        runner: StepRunner,
        game_flow: GameFlow,
        package_name: str,
        cleanup_method: str = "clear_data",
        delete_cooldown_seconds: int = 60,
        control=None,
    ):
        self.adb = adb
        self.runner = runner
        self.game_flow = game_flow
        self.package_name = package_name
        self.cleanup_method = cleanup_method
        self.control = control
        self.delete_controller = AccountDeleteController(
            adb,
            runner,
            package_name,
            cooldown_seconds=delete_cooldown_seconds,
            control=control,
        )

    def cleanup_current_account(self) -> None:
        if self.cleanup_method == "logout":
            log.warning("โหมด logout ยังไม่รองรับขั้นตอนในเกม — ใช้ลบบัญชีแทน")
        self.delete_controller.delete_account()

    def run_one_cycle(self) -> None:
        if self.control:
            self.control.check()
        self.game_flow.ensure_ready()
        self.cleanup_current_account()
