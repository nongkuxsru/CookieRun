from __future__ import annotations

from src.core.logger import get_logger
from src.data.recorder import Recorder

log = get_logger(__name__)


class TreasureResultService:
    def __init__(self, recorder: Recorder):
        self.recorder = recorder

    def log_summary(self, found_treasures: dict[str, int]) -> None:
        log.info("========== Treasure Summary ==========")
        log.info("Victor      : %d", found_treasures["victor"])
        log.info("Banana      : %d", found_treasures["banana"])
        log.info("Coin Wallet : %d", found_treasures["coin"])
        log.info("======================================")

    def record_success(
        self,
        account_id: str,
        treasure_key: str,
        found_treasures: dict[str, int],
    ) -> None:

        self.recorder.record_found_pet(
            account_id,
            treasure_key,
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

    def record_failed(
        self,
        account_id: str | None,
        found_treasures: dict[str, int],
    ) -> None:

        self.recorder.record_failed_account(
            account_id,
            reason=(
                f"Treasure Result : "
                f"Victor={found_treasures['victor']} "
                f"Banana={found_treasures['banana']} "
                f"Coin={found_treasures['coin']}"
            ),
        )