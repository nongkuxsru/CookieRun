"""Shared Step builders used across automation flow modules."""

from __future__ import annotations

from src.automation.steps import OnMissing, Step, tap_matched_center


def button_step(
    name: str,
    template: str,
    *,
    timeout: float = 15.0,
    on_missing: OnMissing = "raise",
    post_delay: float = 0.8,
    action=tap_matched_center,
) -> Step:
    return Step(
        name=name,
        templates=[template],
        action=action,
        timeout=timeout,
        on_missing=on_missing,
        post_delay=post_delay,
    )
