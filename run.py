"""Main entry point for the CookieRun MuMuPlayer automation.



Usage:

    python run.py list                 # สแกนหา MuMuPlayer ที่เปิดอยู่

    python run.py run --instance 0     # เริ่มทำงานอัตโนมัติบน instance ที่เลือก

    python run.py run --instance 0 --cycles 5   # จำกัดจำนวนรอบบัญชี (ค่าเริ่มต้น = ไม่จำกัด)

"""



from __future__ import annotations



import argparse

import sys

from pathlib import Path



sys.path.insert(0, str(Path(__file__).resolve().parent))



from src.automation.account_delete import AccountDeleteController

from src.automation.game_flow import GameFlow

from src.automation.pet_reroll import PetRerollController

from src.automation.state_machine import StepRunner

from src.automation.treasure_reroll import TreasureRerollController

from src.core import emulator_scanner

from src.core.adb_client import AdbClient

from src.core.config import Config

from src.core.exceptions import AutomationBaseError

from src.core.logger import get_logger, setup_logging

from src.data.recorder import Recorder



log = get_logger(__name__)



_UNLIMITED_HATCH_CAP = 10_000_000





def cmd_list(config: Config) -> None:

    instances = emulator_scanner.scan(config)

    if not instances:

        print("ไม่พบ MuMuPlayer ที่เปิดอยู่")

        return

    print("\nพบ MuMuPlayer instance ทั้งหมด:")

    for inst in instances:

        print(f"  {inst.display_name}")





def build_runner(adb: AdbClient, config: Config) -> StepRunner:

    return StepRunner(

        adb=adb,

        templates_root=config.get("templates.root_dir", "templates"),

        default_threshold=config.get("templates.match_threshold", 0.85),

        default_scales=config.get("templates.match_scales", [1.0]),

        step_retry_count=config.get("automation.step_retry_count", 3),

        step_retry_delay=config.get("automation.step_retry_delay_seconds", 2.0),

        error_screenshot_dir=config.get("paths.error_screenshots_dir", "logs/errors"),

    )





def cmd_run(config: Config, instance_index: int, max_cycles: int | None) -> None:

    instances = emulator_scanner.scan(config)

    if not instances:

        print("ไม่พบ MuMuPlayer ที่เปิดอยู่ กรุณาเปิดโปรแกรมจำลองก่อนแล้วลองใหม่")

        return

    if instance_index >= len(instances):

        print(f"ไม่พบ instance ลำดับที่ {instance_index} (พบทั้งหมด {len(instances)} ตัว)")

        return



    inst = instances[instance_index]

    adb_path = emulator_scanner.resolve_adb_path(config)

    adb = AdbClient(adb_path=adb_path, address=inst.adb_address)

    adb.connect()



    runner = build_runner(adb, config)

    package_name = config.get("game.package_name")

    activity = config.get("game.main_activity")

    launch_wait = config.get("game.launch_wait_seconds", 25)

    target_pet = config.get("game.target_pet")

    target_treasure = config.get("reroll.target_treasure", "Victor_Feather_Laurel_Wreath")

    player_name = config.get("game.player_name", "Nongku56")

    unlimited_rolls = config.get("reroll.unlimited_rolls", True)

    rolls_per_round = config.get("reroll.rolls_per_round", 10)

    treasure_max_draws = config.get("reroll.treasure_max_draws", 12)

    delete_cooldown = config.get("delete.cooldown_seconds", 60)

    max_hatches = (

        _UNLIMITED_HATCH_CAP if unlimited_rolls else max(int(rolls_per_round), 1)

    )



    if not target_pet or target_pet == "CHANGE_ME":

        print(

            "กรุณาตั้งค่า game.target_pet ใน config/config.yaml ให้ตรงกับชื่อไฟล์ template "

            "ของสัตว์เลี้ยงที่ต้องการ (templates/pet_reroll/<target_pet>.png) ก่อนเริ่มทำงาน"

        )

        return



    game_flow = GameFlow(

        adb, runner, package_name, activity, launch_wait, player_name=player_name

    )

    recorder = Recorder(config.get("paths.output_dir", "data_output"))

    delete_controller = AccountDeleteController(

        adb, runner, package_name, cooldown_seconds=delete_cooldown

    )

    pet_controller = PetRerollController(

        adb=adb,

        runner=runner,

        game_flow=game_flow,

        recorder=recorder,

        target_pet_key=target_pet,

        package_name=package_name,

        config=config,

        delete_controller=delete_controller,

        max_hatches=max_hatches,

    )

    treasure_controller = TreasureRerollController(

        adb=adb,

        runner=runner,

        recorder=recorder,

        target_treasure_key=target_treasure,

        max_draws=treasure_max_draws,

    )



    cycle = 0

    while max_cycles is None or cycle < max_cycles:

        cycle += 1

        log.info("=== เริ่มรอบบัญชีที่ %d ===", cycle)

        try:

            outcome, account_id = pet_controller.run_one_account_cycle(

                treasure_controller

            )

            if outcome == "kept":

                log.info(

                    "เจอครบทั้งสัตว์เลี้ยงและสมบัติ! เก็บไอดี %s หยุดที่นี่",

                    account_id,

                )

                break

        except AutomationBaseError:

            log.exception("เกิดข้อผิดพลาดที่ไม่สามารถกู้คืนได้ในรอบที่ %d หยุดการทำงาน", cycle)

            break





def main() -> None:

    parser = argparse.ArgumentParser(description="CookieRun MuMuPlayer ADB Automation")

    subparsers = parser.add_subparsers(dest="command", required=True)



    subparsers.add_parser("list", help="สแกนหา MuMuPlayer ที่เปิดอยู่")



    run_parser = subparsers.add_parser("run", help="เริ่มทำงานอัตโนมัติ")

    run_parser.add_argument(

        "--instance", type=int, default=0, help="ลำดับ instance ที่ต้องการใช้งาน"

    )

    run_parser.add_argument(

        "--cycles", type=int, default=None, help="จำกัดจำนวนรอบบัญชี (ไม่ระบุ = ไม่จำกัด)"

    )



    args = parser.parse_args()



    setup_logging()

    config = Config.load()



    if args.command == "list":

        cmd_list(config)

    elif args.command == "run":

        cmd_run(config, args.instance, args.cycles)





if __name__ == "__main__":

    main()


