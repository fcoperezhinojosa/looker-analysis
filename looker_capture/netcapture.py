"""Archiving Looker's own data responses as a safety net.

The report front-end fetches its figures from an internal batchedDataV2
endpoint. Those responses carry the exact numbers, including rows hidden behind
a table's pagination. It is undocumented and can change without warning, so it
is archived alongside the DOM extraction and never replaces it — data.json
always reports what the DOM said.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from playwright.async_api import Page, Response

log = logging.getLogger(__name__)

XSSI_PREFIX = ")]}'"
MATCH = "batchedDataV2"


class NetworkRecorder:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._buffer: list[tuple[str, str]] = []

    def attach(self, page: Page) -> None:
        if self.enabled:
            page.on("response", self._on_response)

    def reset(self) -> None:
        self._buffer.clear()

    async def _on_response(self, response: Response) -> None:
        if MATCH not in response.url:
            return
        try:
            body = await response.text()
        except Exception as exc:  # noqa: BLE001 - body gone after a navigation
            log.debug("Could not read a %s response body: %s", MATCH, exc)
            return
        self._buffer.append((response.url, body))

    def flush(self, directory: Path) -> int:
        """Write buffered responses to disk. Returns how many were written."""
        if not self.enabled or not self._buffer:
            self.reset()
            return 0
        directory.mkdir(parents=True, exist_ok=True)
        written = 0
        for index, (url, body) in enumerate(self._buffer):
            payload = body.lstrip()
            if payload.startswith(XSSI_PREFIX):
                payload = payload[len(XSSI_PREFIX) :].lstrip()
            target = directory / f"net_{index:02d}.json"
            try:
                parsed = json.loads(payload)
                target.write_text(
                    json.dumps({"url": url, "response": parsed}, ensure_ascii=False, indent=1),
                    encoding="utf-8",
                )
            except json.JSONDecodeError:
                # Keep it anyway — an unparsed body is still better than nothing.
                target.with_suffix(".txt").write_text(f"{url}\n\n{body}", encoding="utf-8")
            written += 1
        self.reset()
        return written
