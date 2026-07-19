from __future__ import annotations

from src.core.logger import get_logger

log = get_logger(__name__)


class TreasureResultService:

    def log_summary(self, found_treasures: dict[str, int]) -> None:
        log.info("========== Treasure Summary ==========")
        log.info("Victor      : %d", found_treasures["victor"])
        log.info("Banana      : %d", found_treasures["banana"])
        log.info("Coin Wallet : %d", found_treasures["coin"])
        log.info("======================================")