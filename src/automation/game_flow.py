"""Launches CookieRun, logs in via Email + Password, and completes first-run onboarding."""

from __future__ import annotations

import random
import string
import time
from typing import Literal

from src.automation.state_machine import StepRunner
from src.automation.steps import (
    OnMissing,
    Step,
    tap_matched_center,
    tap_matched_center_then_type,
)
from src.core.adb_client import AdbClient
from src.core.exceptions import AutomationError
from src.core.image_matcher import MatchResult, find_template
from src.core.logger import get_logger

log = get_logger(__name__)

_DEFAULT_PLAYER_NAME = "Nongku56"
_LOBBY_TEMPLATE = "login/lobby_marker.png"
_DEV_LOGIN_TEMPLATE = "login/dev_mode_button.png"

GameScreenState = Literal["lobby", "dev_login", "unknown"]


def generate_random_email() -> str:
    """สุ่มอีเมล 4-5 ตัวอักษร (พิมพ์ใหญ่-เล็ก) + ตัวเลข 2 หลัก + @gmail.com"""
    letters = string.ascii_letters
    name = "".join(random.choice(letters) for _ in range(6))
    numbers = "".join(random.choice(string.digits) for _ in range(3))
    return f"{name}{numbers}@gmail.com"


def _button_step(
    name: str,
    template: str,
    *,
    timeout: float = 0.5,
    on_missing: OnMissing = "raise",
    post_delay: float = 0.8,
    action=tap_matched_center,
) -> Step:
    return Step(
        name=name,
        templates=[template],
        action=action,
        timeout=timeout,
        on_missing=on_missing,
        post_delay=post_delay,
    )


class GameFlow:
    def __init__(
        self,
        adb: AdbClient,
        runner: StepRunner,
        package_name: str,
        activity: str | None,
        launch_wait_seconds: float,
        referral_link: str | None = None,
        player_name: str = _DEFAULT_PLAYER_NAME,
    ):
        self.adb = adb
        self.runner = runner
        self.package_name = package_name
        self.activity = activity
        self.launch_wait_seconds = launch_wait_seconds
        self.referral_link = referral_link
        self.player_name = player_name
        
        # สำหรับบันทึกอีเมล
        self.current_email: str | None = None
        self.current_password = "Zxc.1234"

    def build_login_steps(self) -> list[Step]:
        """ล็อกอินด้วย Email + Password"""
        email = generate_random_email()
        self.current_email = email
        password = self.current_password

        return [
            _button_step("login_dev_mode_entry", "login/dev_mode_button.png", timeout=20.0),
            _button_step("login_email_button", "login/login_email_button.png", timeout=12.0),
            
            Step(
                name="enter_email",
                templates=["login/email_box.png"],
                action=tap_matched_center_then_type(
                    email, focus_delay=0.8, commit_with_enter=True
                ),
                timeout=15.0,
                post_delay=1.0,
            ),
            #_button_step("submit_email", "login/submit_email.png", timeout=10.0),
            
            Step(
                name="enter_password_1st",
                templates=["login/password_box_1st.png"],
                action=tap_matched_center_then_type(
                    password, focus_delay=0.8, commit_with_enter=False
                ),
                timeout=12.0,
                post_delay=1.0,
            ),
            Step(
                name="enter_password_2nd",
                templates=["login/password_box_2nd.png"],
                action=tap_matched_center_then_type(
                    password, focus_delay=0.8, commit_with_enter=False
                ),
                timeout=12.0,
                post_delay=1.0,
            ),
            _button_step("submit_password", "login/submit_password.png", timeout=2.0),
            #_button_step("check_and_handle_error", "login/error_submit.png", timeout=0.5, on_missing="skip"),
        ]

    def build_boot_steps(self, player_name: str = _DEFAULT_PLAYER_NAME) -> list[Step]:
        """รวม Login + Onboarding"""
        return [*self.build_login_steps(), *build_onboarding_steps(player_name)]

    def has_login_error(self) -> bool:
        """ตรวจว่ามี popup Error 40212 หรือไม่"""
        result = self._match_on_screen("login/error_40212.png")
        return result.found

    # === ส่วน onboarding (เหมือนเดิม) ===
    def _match_on_screen(self, template_rel: str) -> MatchResult:
        path = self.runner.templates_root / template_rel
        if not path.exists():
            return MatchResult(found=False, confidence=0.0, center=None, top_left=None, size=None)
        screenshot = self.adb.screenshot()
        return find_template(
            screenshot, path,
            threshold=self.runner.default_threshold,
            scales=self.runner.default_scales,
        )

    def detect_game_screen(self) -> GameScreenState:
        lobby = self._match_on_screen(_LOBBY_TEMPLATE)
        if lobby.found:
            log.info("ตรวจพบหน้า lobby (confidence=%.3f)", lobby.confidence)
            return "lobby"

        dev_login = self._match_on_screen(_DEV_LOGIN_TEMPLATE)
        if dev_login.found:
            log.info("ตรวจพบหน้า DevPlay Login (confidence=%.3f)", dev_login.confidence)
            return "dev_login"

        return "unknown"

    def send_referral_if_needed(self) -> None:
        if not self.referral_link:
            return
        log.info("เปิดลิงก์ referral: %s", self.referral_link)
        self.adb.open_url(self.referral_link)
        time.sleep(3)

    def launch_game(self) -> None:
        log.info("เปิดเกม %s ...", self.package_name)
        self.adb.start_app(self.package_name, self.activity)
        time.sleep(self.launch_wait_seconds)

    def ensure_game_launched(self) -> GameScreenState:
        state = self.detect_game_screen()
        if state in ("lobby", "dev_login"):
            return state

        if self.adb.is_app_running(self.package_name):
            self.adb.bring_to_foreground(self.package_name, self.activity, settle_seconds=3.0)
            state = self.detect_game_screen()
            if state in ("lobby", "dev_login"):
                return state

        self.launch_game()
        return self.detect_game_screen()

    def restart_game(self) -> None:
        log.warning("รีสตาร์ทเกม")
        self.adb.stop_app(self.package_name)
        time.sleep(2)
        self.launch_game()

    def login_dev_mode(self, max_recovery_attempts: int = 2) -> None:
        if self.detect_game_screen() == "lobby":
            return

        for attempt in range(1, max_recovery_attempts + 1):
            try:
                # ---------- Login ----------
                self.runner.run_sequence(self.build_login_steps())

                # รอให้ Popup Error ขึ้น (ถ้ามี)
                time.sleep(1.0)

                # ---------- ตรวจ Error ----------
                if self.has_login_error():
                    log.warning("พบ Login Error 40212")

                    if attempt >= max_recovery_attempts:
                        raise AutomationError("Login Error 40212")

                    self.restart_game()
                    continue

                # ---------- Onboarding ----------
                self.runner.run_sequence(
                    build_onboarding_steps(self.player_name)
                )

                log.info("เข้าเกมสำเร็จ")
                return

            except AutomationError:
                log.exception("เข้าเกมล้มเหลว (ครั้งที่ %d)", attempt)

                if attempt < max_recovery_attempts:
                    self.restart_game()

        raise AutomationError("เข้าเกมล้มเหลว")

    def ensure_ready(self) -> None:
        self.send_referral_if_needed()
        state = self.ensure_game_launched()
        if state == "lobby":
            return
        self.login_dev_mode()


# === ฟังก์ชัน onboarding (ต้องอยู่ภายนอกคลาส) ===
def build_newgame_steps() -> list[Step]:
    return [
        _button_step("newgame_enter", "newgame/enter_newgame.png", timeout=20.0),
        _button_step("newgame_stop", "newgame/stop_button.png"),
        _button_step("newgame_quit", "newgame/quit_button.png"),
        _button_step("newgame_confirm_quit", "newgame/confirm_quit_button.png"),
    ]

def build_setname_steps(player_name: str = _DEFAULT_PLAYER_NAME) -> list[Step]:
    return [
        Step(
            name="setname_enter_name",
            templates=["setname/name_box.png"],
            action=tap_matched_center_then_type(player_name, focus_delay=0.8, commit_with_enter=True),
            timeout=15.0,
            post_delay=1.0,
        ),
        _button_step("setname_confirm", "setname/confirm_button.png"),
    ]

def build_popup_close_steps() -> list[Step]:
    return [
        _button_step(
            f"popup_close_{i:02d}",
            f"popup/close_popup_{i:02d}.png",
            timeout=0.3,
            on_missing="skip",
        )
        for i in range(1, 4)
    ]

def build_daily_checkin_steps() -> list[Step]:
    steps = [_button_step(f"daily_checkin_confirm_{i:02d}", f"daily_checkin_popup/confirm_{i:02d}.png") for i in range(1, 4)]
    steps.append(_button_step("daily_checkin_close", "daily_checkin_popup/confirm_close.png"))
    return steps

def build_free_item_steps() -> list[Step]:
    return [_button_step(f"free_item_confirm_{i:02d}", f"free_item/confirm_{i:02d}.png") for i in range(1, 6)]

def build_lobby_ready_step() -> Step:
    return Step(name="lobby_ready", templates=["login/lobby_marker.png"], action=None, timeout=30.0)

def build_onboarding_steps(player_name: str = _DEFAULT_PLAYER_NAME) -> list[Step]:
    return [
        *build_newgame_steps(),
        *build_setname_steps(player_name),
        *build_popup_close_steps(),
        #close_all_popups(),
        *build_daily_checkin_steps(),
        *build_free_item_steps(),
        build_lobby_ready_step(),
    ]