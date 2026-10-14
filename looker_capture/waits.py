"""Deciding when a Looker page has actually finished rendering.

Three things have to be true before a capture counts: the text on the page has
stopped changing, the mandated settle time has elapsed, and no chart is showing
a Quota Error. A scorecard reading 0 mid-load is not a zero, it is a page that
has not loaded.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from playwright.async_api import Page

from .config import QUOTA_BACKOFF_SECONDS
from .frames import frames_text

log = logging.getLogger(__name__)

QUOTA_PATTERNS = [
    re.compile(r"quota\s*error", re.I),
    re.compile(r"accessed too many times", re.I),
    re.compile(r"error de cuota", re.I),
    re.compile(r"se ha accedido demasiadas veces", re.I),
]

Reapply = Callable[[], Awaitable[None]]


@dataclass
class RenderResult:
    ok: bool
    quota_retries: int = 0
    notes: list[str] = field(default_factory=list)

    def note(self, message: str) -> None:
        self.notes.append(message)


async def sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def find_quota_error(page: Page) -> str | None:
    """Quota errors render inside the chart iframes, not the main document."""
    text = await frames_text(page)
    for pattern in QUOTA_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


async def wait_until_stable(
    page: Page,
    poll_seconds: float = 2.0,
    required_identical: int = 3,
    timeout_seconds: float = 180.0,
) -> bool:
    """Poll the page text until it stops changing."""
    deadline = time.monotonic() + timeout_seconds
    last_digest = None
    identical = 0
    while time.monotonic() < deadline:
        digest = hashlib.sha256((await frames_text(page)).encode("utf-8")).hexdigest()
        if digest == last_digest:
            identical += 1
            if identical >= required_identical:
                return True
        else:
            identical = 0
            last_digest = digest
        await asyncio.sleep(poll_seconds)
    return False


async def wait_for_render(
    page: Page,
    settle_seconds: float,
    quota_retries: int = 3,
    reapply: Reapply | None = None,
    label: str = "",
) -> RenderResult:
    """Wait out the render, retrying through Quota Errors with backoff.

    `reapply` is called before each retry because Looker sometimes resets the
    date or filter chip on its own while recovering from a quota error.
    """
    result = RenderResult(ok=False)

    for attempt in range(quota_retries + 1):
        if not await wait_until_stable(page):
            result.note("page text never settled within the stability timeout")

        log.debug("%s settling for %.0fs", label, settle_seconds)
        await asyncio.sleep(settle_seconds)

        quota = await find_quota_error(page)
        if quota is None:
            result.ok = True
            return result

        result.quota_retries = attempt + 1
        result.note(f"quota error {quota!r} on attempt {attempt + 1}")
        if attempt >= quota_retries:
            log.error("%s still showing a quota error after %d retries", label, attempt)
            return result

        backoff = QUOTA_BACKOFF_SECONDS[min(attempt, len(QUOTA_BACKOFF_SECONDS) - 1)]
        log.warning("%s hit a quota error; backing off %.0fs then retrying", label, backoff)
        await asyncio.sleep(backoff)
        if reapply is not None:
            try:
                await reapply()
            except Exception as exc:  # noqa: BLE001 - a failed reapply is not fatal here
                result.note(f"reapplying controls after the quota error failed: {exc}")

    return result
