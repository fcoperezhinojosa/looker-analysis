"""Cross-frame helpers.

Looker Studio renders each chart into its own iframe, and depending on the
component type the controls may live in the main document or in a frame of
their own. Nothing in this project assumes which — every lookup sweeps the main
frame first and then every child frame.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Iterable

from playwright.async_api import Frame, Locator, Page

log = logging.getLogger(__name__)

LocatorBuilder = Callable[[Frame], Locator]


def all_frames(page: Page) -> list[Frame]:
    """Main frame first, then children, skipping detached ones."""
    frames = [page.main_frame]
    for frame in page.frames:
        if frame is not page.main_frame and not frame.is_detached():
            frames.append(frame)
    return frames


async def safe_text(frame: Frame, timeout: float = 5_000) -> str:
    """inner_text of a frame's body, or "" if the frame went away mid-read."""
    try:
        return await frame.locator("body").inner_text(timeout=timeout)
    except Exception:  # noqa: BLE001 - frames detach constantly while Looker renders
        return ""


async def frames_text(page: Page) -> str:
    parts = []
    for frame in all_frames(page):
        text = await safe_text(frame, timeout=3_000)
        if text:
            parts.append(text)
    return "\n".join(parts)


async def first_visible(
    page: Page,
    builders: Iterable[LocatorBuilder],
    timeout: float = 2_000,
    max_matches: int = 6,
) -> tuple[Frame, Locator] | None:
    """First visible match for any builder, tried strategy-by-strategy.

    Strategies are tried in order across all frames, so a precise selector that
    matches in a late frame still beats a loose fallback in the main frame. Up
    to max_matches candidates per frame are checked, because Looker keeps
    hidden template copies of rows in the DOM alongside the real ones.
    """
    for build in builders:
        for frame in all_frames(page):
            try:
                locator = build(frame)
                count = min(await locator.count(), max_matches)
            except Exception:  # noqa: BLE001 - bad selector for this frame, try next
                continue
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if await candidate.is_visible(timeout=timeout):
                        return frame, candidate
                except Exception:  # noqa: BLE001 - stale match, try the next one
                    continue
    return None


async def chart_iframes(page: Page) -> list[tuple[int, Locator, dict, Frame | None]]:
    """Every iframe on the page, paired with its box and content frame.

    The index is what pairs a tile's numbers with its tile_<n>.png, so the two
    outputs can always be lined up afterwards.
    """
    out: list[tuple[int, Locator, dict, Frame | None]] = []
    handles = await page.locator("iframe").all()
    for index, handle in enumerate(handles):
        try:
            box = await handle.bounding_box()
        except Exception:  # noqa: BLE001
            box = None
        if not box or box["width"] < 40 or box["height"] < 24:
            continue
        # Locator.content_frame is a FrameLocator property, not the Frame we
        # need — go through the element handle to get the real Frame.
        frame = None
        try:
            element = await handle.element_handle(timeout=5_000)
            if element is not None:
                frame = await element.content_frame()
        except Exception:  # noqa: BLE001
            frame = None
        out.append((index, handle, box, frame))
    return out


def union_box(boxes: Iterable[dict]) -> dict | None:
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    left = min(b["x"] for b in boxes)
    top = min(b["y"] for b in boxes)
    right = max(b["x"] + b["width"] for b in boxes)
    bottom = max(b["y"] + b["height"] for b in boxes)
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


async def retry(
    action: Callable[[], Awaitable],
    attempts: int,
    backoff: list[float],
    describe: str,
    sleep: Callable[[float], Awaitable[None]],
):
    """Run an async action with bounded retries, keeping the real failure."""
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return await action()
        except Exception as exc:  # noqa: BLE001 - the caller decides what is fatal
            last = exc
            log.debug("%s failed on attempt %d/%d: %s", describe, attempt + 1, attempts, exc)
            if attempt + 1 < attempts:
                await sleep(backoff[min(attempt, len(backoff) - 1)])
    raise ControlError(f"{describe} failed after {attempts} attempts: {last}") from last


class ControlError(RuntimeError):
    """A Looker control could not be driven; the combination is skipped."""
