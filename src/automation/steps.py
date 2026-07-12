"""Building blocks for describing a screen-verified automation step.

A Step says: "somewhere on screen, one of these template images should
appear; once it does, do this action". The StepRunner (state_machine.py)
takes care of screenshotting, retrying, and raising on failure.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from src.core.image_matcher import MatchResult

OnMissing = Literal["retry", "skip", "raise"]


@dataclass
class Step:
    """A single verifiable, actionable unit of the automation flow.

    Attributes:
        name: human-readable id, used in logs and error screenshot filenames.
        templates: list of template file names (relative to the templates
            root, e.g. "login/dev_mode_button.png"). The step succeeds as
            soon as ANY of these is found - useful when a screen can look
            slightly different (e.g. popup may or may not be present).
        action: callable `(adb_client, MatchResult) -> None` executed once the
            template is found. Leave as None for steps that only *verify*
            a screen without interacting with it (e.g. "wait for lobby").
        threshold: overrides the global match confidence threshold.
        region: optional (x, y, w, h) to restrict the search area.
        timeout: total seconds to keep retrying before giving up.
        retry_interval: seconds to sleep between screenshot attempts.
        on_missing: what to do if the template never appears:
            - "raise": raise StepVerificationError (default, stops the flow)
            - "skip": log a warning and move on to the next step
            - "retry": handled by the caller (e.g. loop back to a previous step)
        post_delay: seconds to sleep after the action runs (lets animations settle).
    """

    name: str
    templates: list[str]
    action: Callable[..., None] | None = None
    threshold: float | None = None
    region: tuple[int, int, int, int] | None = None
    timeout: float = 10.0
    retry_interval: float = 0.5
    on_missing: OnMissing = "raise"
    post_delay: float = 0.8
    extra: dict = field(default_factory=dict)

    def resolve_template_paths(self, templates_root: str | Path) -> list[Path]:
        root = Path(templates_root)
        return [root / name for name in self.templates]


# --------------------------------------------------------------------------- #
# Common ready-made actions, so game_flow.py / pet_reroll.py stay declarative #
# --------------------------------------------------------------------------- #


def tap_matched_center(adb, match: MatchResult) -> None:
    """Tap the center of whatever template was matched."""
    if match.center:
        adb.tap(*match.center)


def tap_matched_center_then_type(
    text: str,
    focus_delay: float = 0.5,
    tap_empty_after: bool = False,
    commit_with_enter: bool = False,
):
    """Tap, type ASCII text, then optionally dismiss MuMu input bar or tap empty area."""

    def _action(adb, match: MatchResult) -> None:
        if match.center:
            adb.tap(*match.center)
        if focus_delay:
            time.sleep(focus_delay)
        adb.input_text(text)
        if commit_with_enter:
            adb.dismiss_input_overlay()
        elif tap_empty_after:
            time.sleep(0.3)
            adb.tap_random_empty()

    return _action


def tap_at(x: int, y: int):
    def _action(adb, match: MatchResult) -> None:
        adb.tap(x, y)

    return _action


def swipe_from_match(dx: int, dy: int, duration_ms: int = 300):
    def _action(adb, match: MatchResult) -> None:
        if match.center:
            x, y = match.center
            adb.swipe(x, y, x + dx, y + dy, duration_ms)

    return _action


def press_back():
    def _action(adb, match: MatchResult) -> None:
        adb.back()

    return _action
