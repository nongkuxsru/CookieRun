"""A logging.Handler that pushes formatted log lines into a thread-safe queue.

Automation runs on background threads, but Tkinter widgets may only be
touched from the main thread. The GUI polls this queue on a `root.after()`
timer and appends new lines to the log Text widget from the main thread.
"""

from __future__ import annotations

import logging
import queue


class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue: "queue.Queue[str]"):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:  # pragma: no cover - formatting should not normally fail
            msg = record.getMessage()
        self.log_queue.put(msg)
