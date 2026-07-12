"""Claim rewards from the in-game mail box."""

from __future__ import annotations

from src.automation.flow_steps import button_step
from src.automation.state_machine import StepRunner
from src.automation.steps import Step
from src.core.logger import get_logger

log = get_logger(__name__)


def build_claim_mail_steps() -> list[Step]:
    return [
        button_step("claim_mail_enter", "claim_mail/enter_mail.png"),
        button_step("claim_mail_rewards", "claim_mail/enter_rewards.png"),
        button_step("claim_mail_claim_all", "claim_mail/claim_all.png"),
        button_step("claim_mail_confirm", "claim_mail/confirm.png"),
        button_step("claim_mail_close", "claim_mail/close_mail.png"),
    ]


class ClaimMailController:
    def __init__(self, runner: StepRunner, control=None):
        self.runner = runner
        self.control = control

    def run(self) -> None:
        if self.control:
            self.control.check()
        log.info("เริ่มรับของขวัญจากอีเมล...")
        self.runner.run_sequence(build_claim_mail_steps())
        log.info("รับของขวัญจากอีเมลเสร็จแล้ว")
