"""Shared image helper service.

รวบรวมการตรวจจับรูปภาพ การค้นหา template และการกด template
เพื่อลดโค้ดซ้ำใน Controller ต่าง ๆ
"""

from __future__ import annotations

from pathlib import Path

from src.automation.flow_steps import button_step
from src.automation.state_machine import StepRunner
from src.core.adb_client import AdbClient
from src.core.image_matcher import MatchResult, find_any_template


class ImageService:
    def __init__(
        self,
        adb: AdbClient,
        runner: StepRunner,
    ):
        self.adb = adb
        self.runner = runner

    # ------------------------------------------------------------------
    # Template
    # ------------------------------------------------------------------

    def template_path(self, relative_path: str) -> Path:
        return self.runner.templates_root / relative_path

    def exists(self, relative_path: str) -> bool:
        return self.template_path(relative_path).exists()

    # ------------------------------------------------------------------
    # Match
    # ------------------------------------------------------------------

    def match(self, *template_rels: str) -> tuple[str | None, MatchResult]:
        """
        ค้นหา template หลายรูปพร้อมกัน

        Returns
        -------
        (matched_template, result)
        """

        screenshot = self.adb.screenshot()

        paths = [
            self.template_path(rel)
            for rel in template_rels
            if self.exists(rel)
        ]

        if not paths:
            return (
                None,
                MatchResult(
                    found=False,
                    confidence=0.0,
                    center=None,
                    top_left=None,
                    size=None,
                ),
            )

        matched_path, result = find_any_template(
            screenshot,
            paths,
            threshold=self.runner.default_threshold,
            scales=self.runner.default_scales,
        )

        if result.found and matched_path:
            rel = (
                str(Path(matched_path).relative_to(self.runner.templates_root))
                .replace("\\", "/")
            )
            return rel, result

        return None, result

    # ------------------------------------------------------------------
    # Tap
    # ------------------------------------------------------------------

    def tap(
        self,
        template_rel: str,
        step_name: str,
        *,
        on_missing: str = "skip",
    ) -> MatchResult:
        """
        ค้นหา template แล้วกดตรงกลาง
        """

        return self.runner.run_step(
            button_step(
                step_name,
                template_rel,
                on_missing=on_missing,
            )
        )

    # ------------------------------------------------------------------
    # Try
    # ------------------------------------------------------------------

    def try_match(self, template_rel: str) -> bool:
        """
        ใช้ StepRunner.try_step_once()

        คืนค่า True / False อย่างเดียว
        """

        found, _ = self.runner.try_step_once(
            button_step(
                "try_match",
                template_rel,
                timeout=0,
                on_missing="skip",
            )
        )

        return found