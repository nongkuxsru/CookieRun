"""Centralized logging setup with instance context support."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
import threading

_CONFIGURED = False
_DEFAULT_LOGS_DIR = Path("logs")

# เก็บ context ของแต่ละ thread
_thread_context = threading.local()


def set_instance_context(instance_name: str):
    """ตั้งชื่อ instance สำหรับ log (เรียกจากแต่ละ worker)"""
    _thread_context.instance_name = instance_name


def get_instance_context() -> str:
    return getattr(_thread_context, 'instance_name', 'MAIN')


def setup_logging(
    logs_dir: str | Path = _DEFAULT_LOGS_DIR, level: int = logging.INFO
) -> None:
    """Configure the root logger once."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Formatter ที่มี [Instance]
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | [%(instance)s] | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    class ContextFilter(logging.Filter):
        def filter(self, record):
            record.instance = get_instance_context()
            return True

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.addFilter(ContextFilter())
    root.addHandler(console_handler)

    # File Handler
    file_handler = logging.handlers.RotatingFileHandler(
        logs_path / "automation.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(ContextFilter())
    root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Get logger (ใช้เหมือนเดิม)"""
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)