"""Pet luxury hatch loop: roll until target pet or crystals run out."""

from __future__ import annotations

import time
from pathlib import Path

from src.automation.account_delete import AccountDeleteController
from src.automation.claim_mail import ClaimMailController
from src.automation.flow_steps import button_step
from src.automation.game_flow import GameFlow
from src.automation.state_machine import StepRunner
from src.automation.steps import Step
from src.automation.treasure_reroll import TreasureRerollController
from src.automation.logout import AccountLogoutController
from src.core.adb_client import AdbClient
from src.core.image_matcher import MatchResult, find_any_template
from src.core.logger import get_logger
from src.data.recorder import Recorder
from datetime import datetime
from pathlib import Path
from src.notification.discord_manager import DiscordManager
from src.models.account_info import AccountInfo

log = get_logger(__name__)

_CRYSTALS_LEFT = "pet_reroll/Crystals_left.png"
_CRYSTALS_LEFT_CLOSE = "pet_reroll/Crystals_left_close.png"
_HATCH = "pet_reroll/hatch.png"
_SKIP_HATCH = "pet_reroll/skip_hatch.png"
_CLOSE_POPUP_NEWPET = "pet_reroll/close_popup_newpet.png"
_CLOSE_HATCH = "pet_reroll/close_hatch_popup.png"
_CLOSE_BAG = "pet_reroll/close_bag_pet.png"
_CLOSE_POPUP_DELAY = 2.5
_TARGET_CHECK_DELAY = 0.8
_UNLIMITED_HATCH_CAP = 10_000


def target_pet_template(target_pet_key: str) -> str:
    return f"pet_reroll/{target_pet_key}.png"


def build_enter_pet_steps() -> list[Step]:
    return [
        button_step("pet_enter_pet", "pet_reroll/enter_pet.png", timeout=20.0, post_delay=0.3),
        button_step("pet_enter_hatch", "pet_reroll/enter_hatch.png", timeout=20.0, post_delay=0.3),
    ]


def build_hatch_step() -> Step:
    return button_step(
        "pet_hatch",
        _HATCH,
        post_delay=0.2,
    )


def build_skip_hatch_step() -> Step:
    return button_step(
        "pet_skip_hatch",
        _SKIP_HATCH,
        timeout=12.0,
        post_delay=0.5,
    )

def log_successful_account(
    email: str,
    password: str,
    target_pet: str,
    target_treasure: str = "N/A"
) -> None:
    """บันทึกบัญชีที่เจอของดี"""
    try:
        output_dir = Path("data_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "successful_accounts.txt"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        line = f"{email}|{password}|{target_pet}|{target_treasure}|{timestamp}\n"
        
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(line)
            
        log.info(f"💾 บันทึกบัญชีสำเร็จ → {email}")
    except Exception as e:
        log.error(f"บันทึกบัญชีล้มเหลว: {e}")

class PetRerollController:
    """Hatch pets until target found or crystals exhausted."""

    def __init__(
        self,
        adb: AdbClient,
        runner: StepRunner,
        game_flow: GameFlow,
        recorder: Recorder,
        target_pet_key: str,
        package_name: str,
        config,                                   # ← ต้องมี
        emulator_controller=None,                 # ← เพิ่ม
        delete_controller: AccountDeleteController | None = None,
        logout_controller: AccountLogoutController | None = None,
        max_hatches: int = _UNLIMITED_HATCH_CAP,
        control=None,
        discord: DiscordManager | None = None,
    ):
        self.adb = adb
        self.runner = runner
        self.game_flow = game_flow
        self.recorder = recorder
        self.target_pet_key = target_pet_key
        self.package_name = package_name
        self.config = config
        self.emulator_controller = emulator_controller   # ← เพิ่ม
        self.delete_controller = delete_controller
        self.logout_controller = logout_controller
        self.max_hatches = max_hatches
        self.control = control
        self.discord = discord

    def _template_path(self, rel: str) -> Path:
        return self.runner.templates_root / rel

    def _template_exists(self, rel: str) -> bool:
        return self._template_path(rel).exists()

    def _resolve_target_template(self) -> str | None:
        """Locate target pet PNG on disk (exact name or case-insensitive match)."""
        key = (self.target_pet_key or "").strip()
        if not key:
            return None

        exact = target_pet_template(key)
        if self._template_exists(exact):
            return exact

        folder = self._template_path("pet_reroll")
        if folder.is_dir():
            for path in folder.glob("*.png"):
                if path.stem.lower() == key.lower():
                    rel = f"pet_reroll/{path.name}"
                    log.info("พบ template สัตว์เลี้ยงเป้าหมาย: %s", rel)
                    return rel
        return None

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
            rel = str(Path(matched_path).relative_to(self.runner.templates_root)).replace(
                "\\", "/"
            )
            return rel, result
        return None, result

    def _tap_template(self, template_rel: str, name: str) -> None:
        step = button_step(name, template_rel, on_missing="skip")
        self.runner.run_step(step)

    def _close_pet_bag(self) -> None:
        self._tap_template(_CLOSE_HATCH, "pet_close_hatch_popup")
        self._tap_template(_CLOSE_BAG, "pet_close_bag")

    def _return_to_lobby_after_target_found(self) -> None:
        """ปิดทุกชั้น popup หลังเจอสัตว์เลี้ยงเป้าหมาย (แก้ปัญหาค้างหน้า)"""
        log.info("เจอสัตว์เลี้ยงเป้าหมาย — เริ่มปิดหน้าทุกชั้นเพื่อกลับ lobby")

        # 1. ปิด popup สัตว์ใหม่ก่อน
        self._tap_template(_CLOSE_POPUP_NEWPET, "pet_close_popup_new")
        time.sleep(1.8)

        # 2. ปิดหน้าต่างสุ่มไข่ (Hatch Popup) หลายครั้ง
        log.info("ปิดหน้าต่างสุ่มไข่...")
        self._tap_template(_CLOSE_HATCH, "pet_close_hatch_popup")
        time.sleep(1.0)

        # 3. ปิดหน้ากระเป๋าสัตว์เลี้ยงหลายครั้ง
        log.info("ปิดหน้ากระเป๋าสัตว์เลี้ยง...")
        self._tap_template(_CLOSE_BAG, "pet_close_bag")
        time.sleep(1.2)

        log.info("ปิดหน้าฟักและกระเป๋าเสร็จสิ้น — ควรกลับสู่ lobby แล้ว")

    def _close_on_crystals_empty(self) -> None:
        log.info("เพชรหมด — ปิดหน้าฟักสัตว์เลี้ยง")
        self._tap_template(_CRYSTALS_LEFT_CLOSE, "pet_crystals_left_close")
        self._close_pet_bag()

    def _current_account_id(self) -> str:
        return time.strftime("acct_%Y%m%d_%H%M%S")

    def hatch_until_result(self, account: AccountInfo) -> str:
        """Returns (\"found\" | \"exhausted\", account_id)."""
        target_tpl = self._resolve_target_template()

        if not target_tpl:
            log.warning(
                "ยังไม่มี template สัตว์เลี้ยงเป้าหมายสำหรับ '%s' "
                "(คาดหวังไฟล์ templates/pet_reroll/%s.png) — จะสุ่มต่อไปจนเพชรหมด",
                self.target_pet_key,
                self.target_pet_key,
            )

        self.runner.run_sequence(build_enter_pet_steps())
        hatch_step = build_hatch_step()
        skip_step = build_skip_hatch_step()

        for hatch_num in range(1, self.max_hatches + 1):
            if self.control:
                self.control.check()

            # ── กดฟัก ──
            self.runner.run_step(hatch_step)

            # ── เช็คเพชรหมดก่อน: popup Crystals_left จะปรากฏก่อน skip_hatch ──
            crystals_found, _ = self.runner.try_step_once(
                button_step("check_crystals_empty", _CRYSTALS_LEFT, timeout=0, on_missing="skip")
            )
            if crystals_found:
                log.info("เพชรหมดแล้ว (รอบฟักที่ %d)", hatch_num)
                self.recorder.record_failed_account(
                    account.account_id, reason=f"เพชรหมด (hatch #{hatch_num})"
                )
                # Crystals_left_close → close_hatch_popup → close_bag_pet
                self._close_on_crystals_empty()
                return "exhausted", account.account_id

            # ── ข้ามแอนิเมชันสุ่ม (skip_hatch) ──
            self.runner.run_step(skip_step)
            time.sleep(_TARGET_CHECK_DELAY)

            # ── เช็คเป้าหมาย (tater_Trader.png ฯลฯ) ──
            if target_tpl:
                _, target_result = self._match(target_tpl)
                if target_result.found:
                    log.info(
                        "เจอสัตว์เลี้ยงที่ต้องการ! %s (confidence=%.3f, รอบฟักที่ %d)",
                        target_tpl,
                        target_result.confidence,
                        hatch_num,
                    )
                    screenshot_path = f"logs/found_pet_{account.account_id}.png"
                    self.adb.save_screenshot(screenshot_path)

                    account.pet_name = self.target_pet_key
                    
                    self.recorder.record_found_pet(
                        account.account_id,
                        self.target_pet_key,
                        screenshot_path,
                        note=f"hatch #{hatch_num}",
                        treasures="",   # หรือใส่ชื่อ treasure ถ้ามี
                        
                    )
                    self._return_to_lobby_after_target_found()
                    return "found", account.account_id

            # ── ไม่ตรงเป้าหมาย → ปิด popup สัตว์ใหม่แล้ววนกลับไป hatch อีกรอบ ──
            self._tap_template(_CLOSE_POPUP_NEWPET, "pet_close_popup_new")
            time.sleep(_CLOSE_POPUP_DELAY)

        log.warning("ฟักครบ %d ครั้งแล้วยังไม่เจอเป้าหมาย", self.max_hatches)
        self.recorder.record_failed_account(
            account.account_id, reason="เกินจำนวนฟักสูงสุด"
        )
        self._close_pet_bag()
        return "exhausted", account.account_id

    def run_one_account_cycle(
        self, treasure_controller: TreasureRerollController
    ) -> tuple[str, str | None]:
        """Full account cycle: รับ mail → สุ่มสมบัติ → สุ่มสัตว์เลี้ยง"""
        self.game_flow.ensure_ready()

        # สร้าง account_id ครั้งเดียวตั้งแต่ต้นรอบ
        email = getattr(self.game_flow, "current_email", "")
        password = getattr(self.game_flow, "current_password", "")

        account = AccountInfo(
            email=email,
            password=password,
        )
        log.info("[%s] เริ่มรอบบัญชีใหม่", account.account_id)

        # รับของขวัญใน mail
        ClaimMailController(self.runner, control=self.control).run()

        # === สุ่มสมบัติก่อน ===
        log.info("[%s] เริ่มสุ่มสมบัติ...", account.account_id)
        treasure_outcome = treasure_controller.run(account)

        if treasure_outcome != "found":
            log.info("[%s] ไม่เจอสมบัติที่ต้องการ → ออกจากระบบ", account.account_id)
            log.info("logout_controller = %s", self.logout_controller)
            if self.logout_controller:
                self.logout_controller.logout_account()
            return "logout", account.account_id

        # === เจอสมบัติแล้ว → สุ่มสัตว์เลี้ยง ===
        log.info("[%s] เจอสมบัติแล้ว เริ่มสุ่มสัตว์เลี้ยง...", account.account_id)
        pet_outcome = self.hatch_until_result(account) # ใช้ pet_account_id เพื่อความปลอดภัย

        if pet_outcome == "found":
            log.info("[%s] ✅ เจอทั้งสมบัติและสัตว์เลี้ยง — เก็บไอดี", account.account_id)

            # === บันทึกข้อมูลบัญชี ===
            email = self.game_flow.current_email if hasattr(self.game_flow, 'current_email') else "unknown"
            log_successful_account(
                email=email,
                password=self.game_flow.current_password if hasattr(self.game_flow, 'current_password') else "Zxc.1234",
                target_pet=self.target_pet_key,
                target_treasure="found"   # หรือใส่ชื่อ treasure จริงถ้ามี
            )
            
            # === แจ้ง Discord ===
            try:
                screenshot = f"logs/found_pet_{account.account_id}.png"

                if self.discord:
                    self.discord.found.send_found_account(
                        account_id=account.account_id,
                        target_item=f"{self.target_pet_key} + Treasure",
                        screenshot_path=screenshot,
                    )

            except Exception as e:
                log.warning(f"ส่ง Discord ล้มเหลว: {e}")

            # === Logout === #
            if self.logout_controller:
                self.logout_controller.logout_account()

            return "kept", account.account_id

        else:
            log.info("[%s]  เจอสมบัติแต่ไม่เจอสัตว์เลี้ยง → ออกจากระบบ", account.account_id,)
            if self.logout_controller:
                self.logout_controller.logout_account()
            return "logout", account.account_id
