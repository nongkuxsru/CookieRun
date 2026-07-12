"""Cooperative pause/resume/cancel signaling shared across all automation loops.

A single WorkerControl instance is created per GUI "run" and threaded through
StepRunner / PetRerollController / GameFlow. Long-running loops call
`control.check()` periodically; it blocks while paused and raises
AutomationCancelled once the user hits "ยกเลิก" (Cancel).
"""

from __future__ import annotations

import threading
import time

from src.core.exceptions import AutomationCancelled


class WorkerControl:
    def __init__(self):
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()

    def reset(self) -> None:
        self._stop_event.clear()
        self._pause_event.clear()

    @property
    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    @property
    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def check(self, poll_interval: float = 0.2) -> None:
        """Block while paused; raise AutomationCancelled once stopped.

        Call this at natural loop boundaries (start of each roll/step/account
        cycle) so the GUI's Pause/Resume/Cancel buttons take effect promptly
        without interrupting a single ADB action mid-flight.
        """
        while self._pause_event.is_set():
            if self._stop_event.is_set():
                raise AutomationCancelled("ยกเลิกการทำงานโดยผู้ใช้")
            time.sleep(poll_interval)
        if self._stop_event.is_set():
            raise AutomationCancelled("ยกเลิกการทำงานโดยผู้ใช้")
