"""Executes Steps against a live AdbClient with retries and error capture.

This is the "checking for correctness + error recovery" layer requested:
every step is verified against a screenshot before/after acting, failures
are retried a configurable number of times, and on exhaustion a screenshot
is saved to logs/errors/ for the user to diagnose (missing/outdated template,
unexpected popup, lag, etc.).
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from src.automation.steps import Step
from src.core.adb_client import AdbClient
from src.core.exceptions import AutomationError, StepVerificationError
from src.core.image_matcher import MatchResult, find_any_template
from src.core.logger import get_logger

log = get_logger(__name__)


class StepRunner:
    def __init__(
        self,
        adb: AdbClient,
        templates_root: str | Path,
        default_threshold: float = 0.85,
        default_scales: list[float] | None = None,
        step_retry_count: int = 3,
        step_retry_delay: float = 2.0,
        error_screenshot_dir: str | Path = "logs/errors",
        control=None,
    ):
        self.adb = adb
        self.templates_root = Path(templates_root)
        self.default_threshold = default_threshold
        self.default_scales = default_scales or [1.0]
        self.step_retry_count = step_retry_count
        self.step_retry_delay = step_retry_delay
        self.error_screenshot_dir = Path(error_screenshot_dir)
        self.control = control  # optional WorkerControl for GUI pause/resume/cancel

    def _save_error_screenshot(self, step: Step, screenshot) -> Path | None:
        try:
            self.error_screenshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.error_screenshot_dir / f"{step.name}_{timestamp}.png"
            import cv2

            cv2.imwrite(str(path), screenshot)
            log.error("บันทึกภาพหน้าจอ error ไว้ที่: %s", path)
            return path
        except Exception:  # pragma: no cover - best-effort diagnostics only
            log.exception("บันทึกภาพหน้าจอ error ไม่สำเร็จ")
            return None

    def _existing_template_paths(self, step: Step) -> list[Path]:
        """Return only template files that exist on disk."""
        all_paths = step.resolve_template_paths(self.templates_root)
        existing = [p for p in all_paths if p.exists()]
        missing = [p for p in all_paths if not p.exists()]
        if missing:
            log.warning(
                "[%s] ไม่พบไฟล์ template บนดิสก์: %s",
                step.name,
                ", ".join(str(p) for p in missing),
            )
        return existing

    def try_step_once(self, step: Step) -> tuple[bool, MatchResult]:
        """Take one screenshot and check if the step's template is visible."""
        screenshot = self.adb.screenshot()
        template_paths = self._existing_template_paths(step)
        if not template_paths:
            return False, MatchResult(
                found=False, confidence=0.0, center=None, top_left=None, size=None
            )
        _, result = find_any_template(
            screenshot,
            template_paths,
            threshold=step.threshold or self.default_threshold,
            scales=self.default_scales,
            region=step.region,
        )
        return result.found, result

    def run_step(self, step: Step) -> MatchResult:
        """Run a single step with outer (whole-attempt) retries.

        Each attempt: wait up to `step.timeout` seconds polling for the
        template, run the action if matched, then sleep `post_delay`.
        If the template never shows up, retry the whole attempt up to
        `step_retry_count` times before failing per `step.on_missing`.
        """
        last_result = MatchResult(
            found=False, confidence=0.0, center=None, top_left=None, size=None
        )
        last_screenshot = None

        template_paths = self._existing_template_paths(step)
        if not template_paths:
            if step.on_missing == "skip":
                log.warning(
                    "[%s] ไม่มีไฟล์ template ที่ใช้ได้ ข้ามขั้นตอน (on_missing=skip)",
                    step.name,
                )
                return last_result
            raise StepVerificationError(
                f"ไม่พบไฟล์ template สำหรับขั้นตอน '{step.name}' ใน {self.templates_root}"
            )

        log.info("[%s] เริ่มขั้นตอน (รอ template: %s)", step.name, step.templates)

        for attempt in range(1, self.step_retry_count + 1):
            if self.control:
                self.control.check()
            deadline = time.time() + step.timeout
            while time.time() < deadline:
                if self.control:
                    self.control.check()
                last_screenshot = self.adb.screenshot()
                _, last_result = find_any_template(
                    last_screenshot,
                    template_paths,
                    threshold=step.threshold or self.default_threshold,
                    scales=self.default_scales,
                    region=step.region,
                )
                if last_result.found:
                    log.info(
                        "[%s] พบเป้าหมาย (confidence=%.3f) ครั้งที่ %d",
                        step.name,
                        last_result.confidence,
                        attempt,
                    )
                    if step.action:
                        step.action(self.adb, last_result)
                    if step.post_delay:
                        time.sleep(step.post_delay)
                    return last_result
                time.sleep(step.retry_interval)

            log.warning(
                "[%s] ไม่พบเป้าหมายภายใน %.1f วินาที (พยายามครั้งที่ %d/%d, confidence สูงสุด=%.3f)",
                step.name,
                step.timeout,
                attempt,
                self.step_retry_count,
                last_result.confidence,
            )
            if attempt < self.step_retry_count:
                time.sleep(self.step_retry_delay)

        if last_screenshot is not None:
            self._save_error_screenshot(step, last_screenshot)

        if step.on_missing == "skip":
            log.warning("[%s] ข้ามขั้นตอนนี้ไปตามที่กำหนด (on_missing=skip)", step.name)
            return last_result

        message = f"ไม่สามารถยืนยันขั้นตอน '{step.name}' ได้ (confidence สูงสุด={last_result.confidence:.3f})"
        if step.on_missing == "raise":
            raise StepVerificationError(message)

        # "retry" is meant to be interpreted by the *caller* (e.g. loop back);
        # here we still raise so callers must explicitly catch/handle it.
        raise AutomationError(message)

    def run_sequence(self, steps: list[Step]) -> None:
        for step in steps:
            self.run_step(step)
