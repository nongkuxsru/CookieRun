"""Centralized logging setup - เวอร์ชันสะอาด"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
import threading

_CONFIGURED = False
_DEFAULT_LOGS_DIR = Path("logs")

_thread_context = threading.local()


def set_instance_context(instance_name: str):
    _thread_context.instance_name = instance_name


def get_instance_context() -> str:
    return getattr(_thread_context, 'instance_name', 'MAIN')


def setup_logging(logs_dir: str | Path = _DEFAULT_LOGS_DIR, level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | [%(instance)s] | %(message)s",
        datefmt="%H:%M:%S",
    )

    class ContextFilter(logging.Filter):
        def filter(self, record):
            record.instance = get_instance_context()
            return True

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.addFilter(ContextFilter())
    root.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        logs_path / "automation.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(ContextFilter())
    root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)


# ซ่อน log จากบาง module ที่เยอะเกิน
logging.getLogger("src.automation.state_machine").setLevel(logging.WARNING)
logging.getLogger("src.automation.game_flow").setLevel(logging.INFO)
logging.getLogger("src.core.image_matcher").setLevel(logging.WARNING)