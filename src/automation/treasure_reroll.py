"""Treasure gacha loop after the target pet has been found."""

from __future__ import annotations

import time
from dataclasses import dataclass

from src.automation.flow_steps import button_step
from src.automation.state_machine import StepRunner
from src.automation.steps import Step
from src.core.adb_client import AdbClient
from src.core.image_service import ImageService
from src.core.logger import get_logger
from src.data.recorder import Recorder


log = get_logger(__name__)

_TICKET_LEFT = "treasure_reroll/ticket_left.png"
_SKIP_TREASURE = "treasure_reroll/skip_treasure.png"
_CLOSE_POPUP_NEWTREASURE = "treasure_reroll/close_popup_newtreasure.png"
_DRAW_ANIMATION_DELAY = 1.5
_DEFAULT_MAX_DRAWS = 6
VICTOR_TEMPLATE = "treasure_reroll/Victor_Feather_Laurel_Wreath.png"
BANANA_TEMPLATE = "treasure_reroll/Dropped_Banana_Peel.png"
COIN_TEMPLATE = "treasure_reroll/coin_wallet.png"

def target_treasure_template(target_key: str) -> str:
    return f"treasure_reroll/{target_key}.png"


def build_enter_treasure_step() -> Step:
    return button_step(
        "treasure_enter",
        "treasure_reroll/enter_treasure.png",
        timeout=20.0,
    )


def build_draw_step() -> Step:
    return button_step(
        "treasure_draw",
        "treasure_reroll/draw_treasure.png",
        post_delay=0.5,
    )


def build_click_free_step() -> Step:
    return button_step(
        "treasure_click_free",
        "treasure_reroll/click_free_treasure.png",
        post_delay=0.3,
        on_missing="skip",  # สำคัญ: ถ้าไม่เจอจะข้ามและเช็คสถานะ
    )


def build_skip_treasure_step() -> Step:
    return button_step(
        "treasure_skip",
        "treasure_reroll/skip_treasure.png",
        post_delay=0.3,
        on_missing="skip",
    )

@dataclass(frozen=True)
class TreasureTemplate:
    key: str
    template: str
    display_name: str
    icon: str


TREASURE_TARGETS = (
    TreasureTemplate(
        "victor",
        VICTOR_TEMPLATE,
        "Victor Feather Laurel Wreath",
        "🎉",
    ),
    TreasureTemplate(
        "banana",
        BANANA_TEMPLATE,
        "Dropped Banana Peel",
        "🍌",
    ),
    TreasureTemplate(
        "coin",
        COIN_TEMPLATE,
        "Coin Wallet",
        "🪙",
    ),
)


class TreasureRerollController:
    def __init__(
        self,
        adb: AdbClient,
        runner: StepRunner,
        recorder: Recorder,
        target_treasure_key: str,
        max_draws: int = _DEFAULT_MAX_DRAWS,
        draw_delay: float = _DRAW_ANIMATION_DELAY,
        control=None,
    ):
        self.adb = adb
        self.runner = runner
        self.image = ImageService(adb, runner)
        self.recorder = recorder
        self.target_treasure_key = target_treasure_key
        self.max_draws = max_draws
        self.draw_delay = draw_delay

    def _close_treasure_bag(self) -> None:
        self.image.tap("treasure_reroll/close_treasure_bag.png", "treasure_close_bag")

    def _close_not_found(self) -> None:
        """ปิดเมื่อหมดตั๋วหรือไม่เจอสมบัติ"""
        self.image.tap("treasure_reroll/close_treasure_draw.png", "treasure_close_draw")
        self._close_treasure_bag()

    def _close_popup_new_treasure(self) -> None:
        self.image.tap(_CLOSE_POPUP_NEWTREASURE, "treasure_close_popup_new")
        time.sleep(0.5)

    def _close_found(self, account_id: str) -> None:
        """ปิดและบันทึกเมื่อเจอสมบัติเป้าหมาย"""
    
        self.image.tap("treasure_reroll/close_treasure_draw.png", "treasure_close_draw")
        self.image.tap("treasure_reroll/enter_treasure_cabinet.png", "treasure_enter_cabinet")

        screenshot_path = f"logs/found_treasure_{account_id}.png"
        self.adb.save_screenshot(screenshot_path)
        log.info("บันทึกภาพกระเป๋าสมบัติไว้ที่ %s", screenshot_path)
        
        self.image.tap("treasure_reroll/close_treasure_cabinet.png", "treasure_close_cabinet")
        self._close_treasure_bag()
    
    def _detect_treasures(self, found_treasures):
        for treasure in TREASURE_TARGETS:
            _, result = self.image.match(treasure.template)

            if result.found:
                found_treasures[treasure.key] += 1

                log.info(
                    "%s พบ %s (%d)",
                    treasure.icon,
                    treasure.display_name,
                    found_treasures[treasure.key],
                )

    def _log_summary(self, found_treasures: dict[str, int]) -> None:
        log.info("========== Treasure Summary ==========")
        log.info("Victor      : %d", found_treasures["victor"])
        log.info("Banana      : %d", found_treasures["banana"])
        log.info("Coin Wallet : %d", found_treasures["coin"])
        log.info("======================================")

    def _finish_result(
        self,
        account_id: str | None,
        found_treasures: dict[str, int],
    ) -> str:

        self._log_summary(found_treasures)

        if found_treasures["victor"] > 0:

            if account_id:
                self.recorder.record_found_pet(
                    account_id,
                    self.target_treasure_key,
                    f"logs/found_treasure_{account_id}.png",
                    note=(
                        f"Victor x{found_treasures['victor']} | "
                        f"Banana x{found_treasures['banana']} | "
                        f"Coin x{found_treasures['coin']}"
                    ),
                    treasures=(
                        f"Victor={found_treasures['victor']}, "
                        f"Banana={found_treasures['banana']}, "
                        f"Coin={found_treasures['coin']}"
                    ),
                )

            self._close_found(account_id or "unknown")

            return "found"

        self.recorder.record_failed_account(
            account_id,
            reason=(
                f"Treasure Result : "
                f"Victor={found_treasures['victor']} "
                f"Banana={found_treasures['banana']} "
                f"Coin={found_treasures['coin']}"
            ),
        )

        self._close_not_found()

        return "not_found"

    def _draw_loop(
        self,
        account_id: str | None,
        found_treasures: dict[str, int],
    ) -> str | None:

        for draw_num in range(1, self.max_draws + 1):
                if self.control:
                    self.control.check()

                # ── เช็คตั๋วหมดก่อน ──
                ticket_found, _ = self.runner.try_step_once(
                    button_step("check_ticket_empty", _TICKET_LEFT, timeout=0, on_missing="skip")
                )
                if ticket_found:
                    return self._finish_result(
                        account_id,
                        found_treasures,
                    )

                log.info(
                    "สรุปรอบ %d : Victor=%d Banana=%d Coin=%d",
                    draw_num,
                    found_treasures["victor"],
                    found_treasures["banana"],
                    found_treasures["coin"],
                )

                # กดสุ่มฟรี
                self.runner.run_step(build_click_free_step())

                # กด Skip ถ้ามี
                self.runner.run_step(build_skip_treasure_step())

                # === แก้ไขใหม่: รอ + ตรวจซ้ำหลายครั้ง ===
                log.info("รอภาพสมบัติโผล่...")
                time.sleep(self.draw_delay)

                # ---------- ตรวจสมบัติที่สุ่มได้ ----------
                self._detect_treasures(found_treasures)

                log.info("ไม่เจอสมบัติเป้าหมาย สุ่มรอบถัดไป")

                self._close_popup_new_treasure()

        log.info("หมดรอบสุ่มสมบัติ %d รอบ", self.max_draws)
        return "not_found"

    def run(self, account_id: str | None) -> str:
        """Draw treasures until target found or tickets exhausted.
        Returns "found" or "not_found".
        """
        if self.control:
            self.control.check()

        target_tpl = target_treasure_template(self.target_treasure_key)
        if not self.image.exists(target_tpl):
            log.warning(
                "ยังไม่มี template สมบัติเป้าหมาย: %s (จะสุ่มต่อไปจนหมดตั๋ว)",
                target_tpl,
            )

        log.info("เริ่มสุ่มสมบัติ (account_id=%s)...", account_id)
        found_treasures = {
            "victor": 0,
            "banana": 0,
            "coin": 0,
        }
        
        # เข้าหน้าเมนูสมบัติ
        self.runner.run_step(build_enter_treasure_step())
        
        # เปิดหน้าต่างสุ่มสมบัติ (ทำครั้งเดียว)
        self.runner.run_step(build_draw_step())

        result = self._draw_loop(
            account_id,
            found_treasures,
        )

        if result:
            return result

        return "not_found"
        