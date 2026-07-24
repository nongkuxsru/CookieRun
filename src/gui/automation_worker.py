"""Runs automation across one or more selected MuMuPlayer instances in
background threads, coordinated by a shared WorkerControl and RunStats so
the GUI's Start/Pause/Resume/Cancel buttons and stat counters reflect every
instance combined.

Supports two distinct modes (selected in the GUI's header tabs):
  - "referral" -> ReferralPumpController: launch + (referral) + collect account
  - "reroll"   -> PetRerollController: roll gacha until target found / gems out
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
from typing import Callable, Literal

from src.automation.logout import AccountLogoutController
from src.automation.account_delete import AccountDeleteController
from src.automation.game_flow import GameFlow
from src.automation.pet_reroll import PetRerollController
from src.automation.referral_pump import ReferralPumpController
from src.automation.state_machine import StepRunner
from src.automation.stats import RunStats
from src.automation.treasure_reroll import TreasureRerollController
from src.automation.worker_control import WorkerControl
from src.core import emulator_scanner
from src.core.adb_client import AdbClient
from src.core.config import Config
from src.core.emulator_scanner import EmulatorInstance
from src.core.exceptions import AutomationBaseError, AutomationCancelled
from src.core.logger import get_logger
from src.data.recorder import Recorder
from src.emulator.emulator_controller import EmulatorController   # ← เพิ่มบรรทัดนี้\
from src.notification.discord_manager import DiscordManager


log = get_logger(__name__)

_MAX_CONSECUTIVE_ERRORS = 3
_UNLIMITED_ROLLS_CAP = 10_000_000

Mode = Literal["referral", "reroll"]


class AutomationWorker:
    def __init__(
        self,
        config: Config,
        instances: list[EmulatorInstance],
        stats: RunStats,
        control: WorkerControl,
        recorder: Recorder,
        on_finished: Callable[[], None],
        mode: Mode = "reroll",
        found_queue: "queue.Queue[str] | None" = None,
        discord: DiscordManager | None = None,
        
    ):
        self.config = config
        self.instances = instances
        self.stats = stats
        self.control = control
        self.recorder = recorder
        self.on_finished = on_finished
        self.mode = mode
        self.found_queue = found_queue
        self._threads: list[threading.Thread] = []
        self.discord = discord


    def start(self) -> None:
        target_fn = (
            self._run_instance_referral
            if self.mode == "referral"
            else self._run_instance_reroll
        )
        self._threads = [
            threading.Thread(
                target=target_fn, args=(inst,), daemon=True, name=f"worker-{inst.name}"
            )
            for inst in self.instances
        ]
        for t in self._threads:
            t.start()
        threading.Thread(
            target=self._watch_completion, daemon=True, name="worker-watchdog"
        ).start()

    def _watch_completion(self) -> None:
        for t in self._threads:
            t.join()
        log.info("=== ทุกจอทำงานจบแล้ว (หรือถูกยกเลิก) ===")
        self.on_finished()

    def _connect(self, inst: EmulatorInstance) -> AdbClient | None:
        cfg = self.config
        adb_path = emulator_scanner.resolve_adb_path(cfg)
        adb = AdbClient(adb_path=adb_path, address=inst.adb_address)
        try:
            adb.connect()
        except AutomationBaseError:
            log.exception("[%s] เชื่อมต่อ adb ไม่สำเร็จ ข้าม instance นี้", inst.name)
            return None
        return adb

    def _build_runner(self, adb: AdbClient) -> StepRunner:
        cfg = self.config
        return StepRunner(
            adb=adb,
            templates_root=cfg.get("templates.root_dir", "templates"),
            default_threshold=cfg.get("templates.match_threshold", 0.85),
            default_scales=cfg.get("templates.match_scales", [1.0]),
            step_retry_count=cfg.get("automation.step_retry_count", 3),
            step_retry_delay=cfg.get("automation.step_retry_delay_seconds", 2.0),
            error_screenshot_dir=cfg.get("paths.error_screenshots_dir", "logs/errors"),
            control=self.control,
        )

    # ------------------------------------------------------ mode: referral --
    def _run_instance_referral(self, inst: EmulatorInstance) -> None:
        tag = inst.name
        cfg = self.config

        package_name = cfg.get("game.package_name")
        activity = cfg.get("game.main_activity")
        launch_wait = cfg.get("game.launch_wait_seconds", 25)
        referral_link = cfg.get("referral.link")
        send_referral = cfg.get("referral.send_before_open", False)
        cleanup_method = cfg.get("run.cleanup_method", "clear_data")
        delete_cooldown = cfg.get("delete.cooldown_seconds", 60)
        player_name = cfg.get("game.player_name", "Nongku56")

        adb = self._connect(inst)
        if adb is None:
            return

        runner = self._build_runner(adb)
        game_flow = GameFlow(
            adb,
            runner,
            package_name,
            activity,
            launch_wait,
            referral_link=referral_link if send_referral else None,
            player_name=player_name,
        )
        controller = ReferralPumpController(
            adb,
            runner,
            game_flow,
            package_name,
            cleanup_method=cleanup_method,
            delete_cooldown_seconds=delete_cooldown,
            control=self.control,
        )

        consecutive_errors = 0
        while True:
            if not self.stats.try_reserve_slot():
                log.info("[%s] ครบเป้าหมายรวมแล้ว หยุดทำงานที่จอนี้", tag)
                break
            try:
                self.control.check()
                log.info("[%s] === เริ่มรอบไอดีใหม่ (ปั้มทำใจ-ชวนเพื่อน) ===", tag)
                controller.run_one_cycle()
                self.stats.record_success()
                consecutive_errors = 0
            except AutomationCancelled:
                log.info("[%s] ยกเลิกการทำงานแล้ว", tag)
                break
            except AutomationBaseError:
                log.exception("[%s] เกิดข้อผิดพลาดระหว่างทำงาน", tag)
                self.stats.record_failed()
                consecutive_errors += 1
                if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                    log.error(
                        "[%s] เกิดข้อผิดพลาดต่อเนื่อง %d ครั้ง หยุดการทำงานของจอนี้",
                        tag,
                        consecutive_errors,
                    )
                    break
                time.sleep(2)

        log.info("[%s] จบการทำงานของจอนี้ (ปั้มทำใจ-ชวนเพื่อน)", tag)

    # -------------------------------------------------------- mode: reroll --
    def _run_instance_reroll(self, inst: EmulatorInstance) -> None:
        tag = inst.name
        from src.core.logger import set_instance_context
        set_instance_context(tag)

        cfg = self.config
        log.info(f"[{tag}] Worker เริ่มทำงาน (Debug Mode)")

        # ── กำหนดค่าเริ่มต้นไว้ก่อน กันเคส error เกิดก่อนตัวแปรถูก assign ──
        outcome = "unknown"
        error_detail = None

        try:
            adb = self._connect(inst)
            if adb is None:
                log.error(f"[{tag}] เชื่อมต่อ ADB ล้มเหลว")
                return

            runner = self._build_runner(adb)

            # === โหลด config ทั้งหมดก่อน ===
            package_name = cfg.get("game.package_name")
            activity = cfg.get("game.main_activity")
            launch_wait = cfg.get("game.launch_wait_seconds", 25)
            target_pet = cfg.get("game.target_pet")
            target_treasure = cfg.get("reroll.target_treasure", "Victor_Feather_Laurel_Wreath")
            target_display_name = (
                cfg.get("reroll.target_item_display_name")
                or f"{target_pet} + {target_treasure}"
            )
            referral_link = cfg.get("referral.link")
            send_referral = cfg.get("referral.send_before_open", False)
            create_new_account = cfg.get("run.create_new_account_each_cycle", True)
            new_accounts_file = cfg.get("run.new_accounts_file", "data_output/new_accounts.txt")
            unlimited_rolls = cfg.get("reroll.unlimited_rolls", True)
            rolls_per_round = cfg.get("reroll.rolls_per_round", 10)
            treasure_max_draws = cfg.get("reroll.treasure_max_draws", 12)
            delete_cooldown = cfg.get("delete.cooldown_seconds", 60)
            max_hatches = (
                _UNLIMITED_ROLLS_CAP if unlimited_rolls else max(int(rolls_per_round), 1)
            )
            player_name = cfg.get("game.player_name", "Nongku56")

            # สร้าง GameFlow และ Controller
            game_flow = GameFlow(
                adb, runner, package_name, activity, launch_wait,
                referral_link=referral_link if send_referral else None,
                player_name=player_name,
            )

            delete_controller = AccountDeleteController(
                adb, runner, package_name, 
                cooldown_seconds=delete_cooldown, 
                control=self.control
            )
            
            logout_controller = AccountLogoutController(
                adb=adb,
                runner=runner,
                package_name=package_name,
                control=self.control,
            )

            emulator_controller = EmulatorController(
                cfg.get("emulator.mumu_manager_path")
            )

            pet_controller = PetRerollController(
                adb=adb,
                runner=runner,
                game_flow=game_flow,
                recorder=self.recorder,
                target_pet_key=target_pet,
                package_name=package_name,
                config=self.config,
                emulator_controller=emulator_controller,
                delete_controller=delete_controller,
                logout_controller=logout_controller,   # ← เพิ่มบรรทัดนี้
                max_hatches=max_hatches,
                control=self.control,
                discord=self.discord,   # ← ต้องเพิ่ม
            )

            treasure_controller = TreasureRerollController(
                adb=adb,
                runner=runner,
                recorder=self.recorder,
                target_treasure_key=target_treasure,
                max_draws=treasure_max_draws,
                control=self.control,
            )

            # เริ่ม loop
            consecutive_errors = 0
            while True:
                if not self.stats.try_reserve_slot():
                    log.info("[%s] ครบเป้าหมายรวมแล้ว หยุดทำงานที่จอนี้", tag)
                    break

                try:
                    self.control.check()
                    log.info("[%s] === เริ่มรอบบัญชีใหม่ ===", tag)

                    if create_new_account:
                        placeholder_id = time.strftime(f"{tag}_%Y%m%d_%H%M%S")
                        self.recorder.record_new_account(placeholder_id, new_accounts_file)

                    outcome, account = pet_controller.run_one_account_cycle(treasure_controller)
                    consecutive_errors = 0

                    if outcome == "kept":
                        self.stats.record_success()
                        log.info("[%s] เจอครบทั้งคู่! อีเมล=%s", tag, account.email if account else "?")

                        if self.found_queue is not None and account is not None:
                            self.found_queue.put({
                                "time": time.strftime("%H:%M:%S"),
                                "instance": tag,
                                "email": account.email,
                                "password": account.password,
                                "pet_name": account.pet_name,
                                "treasures": list(account.treasures),
                                "treasure_screenshot_path": account.treasure_screenshot_path,
                                "pet_screenshot_path": account.pet_screenshot_path,
                                "target_display_name": target_display_name,
                                "found_time": account.found_time.strftime("%Y-%m-%d %H:%M:%S"),
                            })

                        log.info("[%s] Logout แล้ว เริ่มสร้างบัญชีใหม่...", tag)
                        continue

                    elif outcome == "logout":
                        self.stats.record_failed()
                        log.info("[%s] ไม่ครบเป้าหมาย ออกจากระบบแล้ววนต่อ", tag)
                        continue

                    else:
                        self.stats.record_failed()
                        log.info("[%s] จบการทำงานด้วยสถานะ %s", tag, outcome)
                        continuee
                except AutomationCancelled:
                    log.info("[%s] ถูกยกเลิกโดยผู้ใช้", tag)
                    break
                except AutomationBaseError as e:
                    log.exception("[%s] เกิดข้อผิดพลาดระหว่างทำงาน", tag)
                    self.stats.record_failed()
                    consecutive_errors += 1
                    if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                        log.error("[%s] เกิดข้อผิดพลาดต่อเนื่อง %d ครั้ง หยุดจอนี้", tag, consecutive_errors)
                        break
                    time.sleep(2)

        except Exception as e:
            outcome = "error"
            error_detail = traceback.format_exc()
            if len(error_detail) > 1500:
                error_detail = error_detail[-1500:]
            log.exception(
                f"[{tag}] ERROR ใหญ่เกิดขึ้น: {e}"
            )
        finally:
            log.info(f"[{tag}] จบการทำงานของ instance นี้")

            try:
                self.discord.status.send_embed(
                    title=f"🤖 Instance Finished : {tag}",
                    outcome=outcome,
                    error=error_detail,
                )

            except Exception as e:
                log.warning(f"ส่ง Discord ล้มเหลว: {e}")