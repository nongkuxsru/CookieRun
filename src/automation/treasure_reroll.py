"""Treasure gacha loop after the target pet has been found."""

from __future__ import annotations

import time
from pathlib import Path

from src.automation.flow_steps import button_step
from src.automation.state_machine import StepRunner
from src.automation.steps import Step
from src.core.adb_client import AdbClient
from src.core.image_matcher import MatchResult, find_any_template
from src.core.logger import get_logger
from src.data.recorder import Recorder

log = get_logger(__name__)

_TICKET_LEFT = "treasure_reroll/ticket_left.png"
_SKIP_TREASURE = "treasure_reroll/skip_treasure.png"
_CLOSE_POPUP_NEWTREASURE = "treasure_reroll/close_popup_newtreasure.png"
_DRAW_ANIMATION_DELAY = 1.5
_DEFAULT_MAX_DRAWS = 6


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
        self.recorder = recorder
        self.target_treasure_key = target_treasure_key
        self.max_draws = max_draws
        self.draw_delay = draw_delay
        self.control = control

    def _template_path(self, rel: str) -> Path:
        return self.runner.templates_root / rel

    def _template_exists(self, rel: str) -> bool:
        return self._template_path(rel).exists()

    def _match(self, *template_rels: str) -> tuple[str | None, MatchResult]:
        screenshot = self.adb.screenshot()
        paths = [self._template_path(r) for r in template_rels if self._template_exists(r)]
        if not paths:
            return None, MatchResult(
                found=False, confidence=0.0, center=None, top_left=None, size=None
            )
        matched_path, result = find_any_template(
            screenshot,
            paths,
            threshold=self.runner.default_threshold,
            scales=self.runner.default_scales,
        )
        if result.found and matched_path:
            rel = str(Path(matched_path).relative_to(self.runner.templates_root)).replace("\\", "/")
            return rel, result
        return None, result

    def _tap_template(self, template_rel: str, name: str) -> None:
        self.runner.run_step(button_step(name, template_rel, on_missing="skip"))

    def _close_treasure_bag(self) -> None:
        self._tap_template("treasure_reroll/close_treasure_bag.png", "treasure_close_bag")

    def _close_not_found(self) -> None:
        """ปิดเมื่อหมดตั๋วหรือไม่เจอสมบัติ"""
        self._tap_template("treasure_reroll/close_treasure_draw.png", "treasure_close_draw")
        self._close_treasure_bag()

    def _close_popup_new_treasure(self) -> None:
        self._tap_template(_CLOSE_POPUP_NEWTREASURE, "treasure_close_popup_new")
        time.sleep(0.5)

    def _close_found(self, account_id: str) -> None:
        """ปิดและบันทึกเมื่อเจอสมบัติเป้าหมาย"""
    
        self._close_popup_new_treasure()
        self._tap_template("treasure_reroll/close_treasure_draw.png", "treasure_close_draw")
        self._tap_template("treasure_reroll/enter_treasure_cabinet.png", "treasure_enter_cabinet")

        screenshot_path = f"logs/found_treasure_{account_id}.png"
        self.adb.save_screenshot(screenshot_path)
        log.info("บันทึกภาพกระเป๋าสมบัติไว้ที่ %s", screenshot_path)
        
        self._tap_template("treasure_reroll/close_treasure_cabinet.png", "treasure_close_cabinet")
        self._close_treasure_bag()

    def run(self, account_id: str | None) -> str:
        """Draw treasures until target found or tickets exhausted.
        Returns "found" or "not_found".
        """
        if self.control:
            self.control.check()

        target_tpl = target_treasure_template(self.target_treasure_key)
        if not self._template_exists(target_tpl):
            log.warning(
                "ยังไม่มี template สมบัติเป้าหมาย: %s (จะสุ่มต่อไปจนหมดตั๋ว)",
                target_tpl,
            )

        log.info("เริ่มสุ่มสมบัติ (account_id=%s)...", account_id)
        
        # เข้าหน้าเมนูสมบัติ
        self.runner.run_step(build_enter_treasure_step())
        
        # เปิดหน้าต่างสุ่มสมบัติ (ทำครั้งเดียว)
        self.runner.run_step(build_draw_step())

        for draw_num in range(1, self.max_draws + 1):
            if self.control:
                self.control.check()

            # ── เช็คตั๋วหมดก่อน ──
            ticket_found, _ = self.runner.try_step_once(
                button_step("check_ticket_empty", _TICKET_LEFT, timeout=0, on_missing="skip")
            )
            if ticket_found:
                log.info("ตั๋วหมดแล้ว (รอบสุ่มที่ %d)", draw_num)
                self.recorder.record_failed_account(
                    account_id, reason=f"ตั๋วหมด (treasure #{draw_num})"
                )
                self._close_not_found()
                return "not_found"

            log.info("รอบสุ่มที่ %d", draw_num)

            # กดสุ่มฟรี
            free_result = self.runner.run_step(build_click_free_step())

            # กด Skip ถ้ามี
            self.runner.run_step(build_skip_treasure_step())

            # === แก้ไขใหม่: รอ + ตรวจซ้ำหลายครั้ง ===
            log.info("รอภาพสมบัติโผล่...")
            time.sleep(self.draw_delay)

            # ตรวจสอบของที่ได้
            if self._template_exists(target_tpl):
                _, target_result = self._match(target_tpl)

                if target_result.found:
                    log.info("เจอสมบัติเป้าหมาย (รอบ %d)", draw_num)

                    if account_id:
                        self.recorder.record_found_pet(
                            account_id,
                            self.target_treasure_key,
                            f"logs/found_treasure_{account_id}.png",
                            note=f"treasure draw #{draw_num}",
                            treasures=self.target_treasure_key   # ← เพิ่ม
                        )

                    self._close_found(account_id or "unknown")
                    return "found"

            log.info("ไม่เจอสมบัติเป้าหมาย สุ่มรอบถัดไป")

            self._close_popup_new_treasure()

        log.info("หมดรอบสุ่มสมบัติ %d รอบ", self.max_draws)
        return "not_found"
        