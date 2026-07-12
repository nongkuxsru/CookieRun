"""OpenCV template-matching helpers used to verify each step's expected screen.

Every automation Step declares one or more template images (screenshots of
buttons/screens cropped ahead of time - see tools/calibrate.py) and this
module answers: "is this template currently visible on screen, and where?"
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.core.exceptions import TemplateNotFoundError
from src.core.logger import get_logger

log = get_logger(__name__)

_TEMPLATE_CACHE: dict[str, np.ndarray] = {}


@dataclass
class MatchResult:
    found: bool
    confidence: float
    center: tuple[int, int] | None  # (x, y) in screenshot coordinates
    top_left: tuple[int, int] | None
    size: tuple[int, int] | None  # (w, h) of the matched template


def _load_template(path: str | Path) -> np.ndarray:
    key = str(path)
    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]

    p = Path(path)
    if not p.exists():
        raise TemplateNotFoundError(f"ไม่พบไฟล์รูปแบบ (template): {p}")

    image = cv2.imread(str(p), cv2.IMREAD_COLOR)
    if image is None:
        raise TemplateNotFoundError(f"เปิดไฟล์รูปแบบไม่ได้ (ไฟล์อาจเสียหาย): {p}")

    _TEMPLATE_CACHE[key] = image
    return image


def clear_template_cache() -> None:
    _TEMPLATE_CACHE.clear()


def find_template(
    screenshot: np.ndarray,
    template_path: str | Path,
    threshold: float = 0.85,
    scales: list[float] | None = None,
    region: tuple[int, int, int, int] | None = None,
) -> MatchResult:
    """Search for `template_path` inside `screenshot`.

    region: optional (x, y, w, h) to restrict the search area (faster + more accurate).
    scales: try resizing the template at these scale factors (handles minor DPI/window-size drift).
    """
    template = _load_template(template_path)
    scales = scales or [1.0]

    offset_x, offset_y = 0, 0
    search_area = screenshot
    if region:
        x, y, w, h = region
        search_area = screenshot[y : y + h, x : x + w]
        offset_x, offset_y = x, y

    best_confidence = -1.0
    best_top_left: tuple[int, int] | None = None
    best_size: tuple[int, int] | None = None

    for scale in scales:
        if scale != 1.0:
            resized = cv2.resize(
                template, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR
            )
        else:
            resized = template

        th, tw = resized.shape[:2]
        if th > search_area.shape[0] or tw > search_area.shape[1]:
            continue

        result = cv2.matchTemplate(search_area, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_confidence:
            best_confidence = max_val
            best_top_left = (int(max_loc[0]), int(max_loc[1]))
            best_size = (tw, th)

    if best_top_left is None or best_confidence < threshold:
        return MatchResult(
            found=False,
            confidence=max(best_confidence, 0.0),
            center=None,
            top_left=None,
            size=None,
        )

    assert best_size is not None  # guaranteed by the found-check above
    abs_top_left = (best_top_left[0] + offset_x, best_top_left[1] + offset_y)
    w, h = best_size
    center = (abs_top_left[0] + w // 2, abs_top_left[1] + h // 2)
    return MatchResult(
        found=True,
        confidence=best_confidence,
        center=center,
        top_left=abs_top_left,
        size=best_size,
    )


def find_any_template(
    screenshot: np.ndarray,
    template_paths: Sequence[str | Path],
    threshold: float = 0.85,
    scales: list[float] | None = None,
    region: tuple[int, int, int, int] | None = None,
) -> tuple[str | Path | None, MatchResult]:
    """Try multiple templates and return the first (path, result) that matches."""
    best_path = None
    best_result = MatchResult(
        found=False, confidence=0.0, center=None, top_left=None, size=None
    )
    for path in template_paths:
        result = find_template(
            screenshot, path, threshold=threshold, scales=scales, region=region
        )
        if result.found and result.confidence > best_result.confidence:
            best_path, best_result = path, result
    return best_path, best_result


def wait_for_template(
    capture_fn,
    template_path: str | Path,
    threshold: float = 0.85,
    scales: list[float] | None = None,
    region: tuple[int, int, int, int] | None = None,
    timeout: float = 10.0,
    interval: float = 0.5,
) -> MatchResult:
    """Poll `capture_fn()` (usually adb_client.screenshot) until the template appears or timeout."""
    import time

    deadline = time.time() + timeout
    last_result = MatchResult(
        found=False, confidence=0.0, center=None, top_left=None, size=None
    )
    while time.time() < deadline:
        screenshot = capture_fn()
        last_result = find_template(
            screenshot, template_path, threshold=threshold, scales=scales, region=region
        )
        if last_result.found:
            return last_result
        time.sleep(interval)
    return last_result
