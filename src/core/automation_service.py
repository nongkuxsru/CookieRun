from __future__ import annotations

from src.automation.flow_steps import button_step
from src.automation.state_machine import StepRunner
from src.core.adb_client import AdbClient
from src.core.image_service import ImageService


class AutomationService:
    def __init__(
        self,
        adb: AdbClient,
        runner: StepRunner,
    ):
        self.adb = adb
        self.runner = runner
        self.image = ImageService(adb, runner)

    def tap(
        self,
        template: str,
        name: str,
        *,
        on_missing: str = "skip",
    ):
        return self.runner.run_step(
            button_step(
                name,
                template,
                on_missing=on_missing,
            )
        )

    def exists(self, template: str) -> bool:
        return self.image.exists(template)

    def match(self, template: str):
        return self.image.match(template)

    def tap_if_exists(
        self,
        template: str,
        name: str,
    ) -> bool:

        _, result = self.image.match(template)

        if not result.found:
            return False

        self.tap(template, name)
        return True
        
    def tap_template(
        self,
        template: str,
        *,
        name: str | None = None,
        timeout: float = 15.0,
        post_delay: float = 0.8,
        on_missing: str = "raise",
    ):
        return self.runner.run_step(
            button_step(
                name or template,
                template,
                timeout=timeout,
                post_delay=post_delay,
                on_missing=on_missing,
            )
        )