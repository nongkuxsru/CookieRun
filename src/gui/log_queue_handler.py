from __future__ import annotations

import logging
import queue

from src.core.logger import get_instance_context


class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue: "queue.Queue[str]"):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # ใส่ชื่อ instance ให้แน่นอน
            if not hasattr(record, 'instance') or record.instance == 'MAIN':
                record.instance = get_instance_context()
            
            # Formatter แบบสั้นสำหรับ GUI
            msg = f"[{record.instance}] {record.getMessage()}"
        except Exception:
            msg = record.getMessage()

        self.log_queue.put(msg)