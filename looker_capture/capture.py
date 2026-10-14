"""Walking every page x period x landing group and capturing it."""

from __future__ import annotations

import asyncio
import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from playwright.async_api import BrowserContext, Error as PlaywrightError, Page

from . import extract, selectors
from .auth import assert_authenticated
from .config import Period, ReportPage, slugify
from .frames import ControlError, union_box
from .netcapture import NetworkRecorder
from .waits import wait_for_render

log = logging.getLogger(__name__)


@dataclass
class Settings:
    output_dir: Path
    auth_file: Path
    account: int = 0
    settle_seconds: float = 35.0
    pause_seconds: float = 10.0
    quota_retries: int = 3
    tile_margin: int = 8
    dry_run: bool = False
    viewport: dict | None = None


@dataclass
class ComboResult:
    page: str
    period: str
    group: str
    status: str = "pending"  # ok | partial | failed | quota_error
    date_chip: str | None = None
    date_ok: bool | None = None
    date_note: str = ""
    filter_chip: str | None = None
    filter_ok: bool | None = None
    filter_note: str = ""
    quota_retries: int = 0
    tiles: list[dict[str, Any]] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    network_files: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "date_chip": self.date_chip,
            "date_verified": self.date_ok,
            "date_note": self.date_note,
            "filter_chip": self.filter_chip,
            "filter_verified": self.filter_ok,
            "filter_note": self.filter_note,
            "quota_retries": self.quota_retries,
            "screenshots": self.screenshots,
            "network_files": self.network_files,
            "errors": self.errors,
            "tiles": self.tiles,
        }


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


class Runner:
    def __init__(
        self,
        context: BrowserContext,
        settings: Settings,
        recorder: NetworkRecorder,
        checkpoint: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.context = context
        self.settings = settings
        self.recorder = recorder
        self.results: dict[str, Any] = {}
        # Called after every combination so a crash an hour in cannot cost the
        # combinations that already succeeded. Writing only at the end lost a
        # full 56-combination run when Chrome died on the second-to-last page.
        self._checkpoint = checkpoint

    def _save(self) -> None:
        if self._checkpoint is None:
            return
        try:
            self._checkpoint(self.results)
        except Exception as exc:  # noqa: BLE001 - a failed save must not stop the run
            log.warning("Could not checkpoint results: %s", exc)

    # -- output paths -----------------------------------------------------

    def combo_dir(self, page_def: ReportPage, period: Period, group: str) -> Path:
        return self.settings.output_dir / page_def.slug / period.slug / slugify(group)

    def raw_dir(self, page_def: ReportPage, period: Period, group: str) -> Path:
        return (
            self.settings.output_dir / "raw" / page_def.slug / period.slug / slugify(group)
        )

    # -- main loop --------------------------------------------------------

    async def run(
        self, pages: list[ReportPage], periods: list[Period], groups: list[str]
    ) -> dict[str, Any]:
        page = await self.context.new_page()
        # The context comes from a browser we attached to over CDP, so it
        # carries no viewport of its own — set it on the page instead, or the
        # report canvas renders at whatever size Chrome happened to open.
        if self.settings.viewport:
            try:
                await page.set_viewport_size(self.settings.viewport)
            except PlaywrightError as exc:
                log.warning("Could not set the viewport to %s: %s", self.settings.viewport, exc)
        self.recorder.attach(page)
        try:
            for page_def in pages:
                for period in periods:
                    await self._run_page_period(page, page_def, period, groups)
        finally:
            await page.close()
        return self.results

    async def _run_page_period(
        self, page: Page, page_def: ReportPage, period: Period, groups: list[str]
    ) -> None:
        url = page_def.url(self.settings.account)
        bucket = (
            self.results.setdefault(page_def.slug, {"title": page_def.title, "periods": {}})[
                "periods"
            ]
            .setdefault(
                period.name,
                {
                    "range": {"start": period.start.isoformat(), "end": period.end.isoformat()},
                    "url": url,
                    "groups": {},
                },
            )
        )

        # One fresh navigation per landing group, not one per page+period.
        # Reusing a loaded page for several groups does not work: after the
        # first filter selection the control will not reopen (the editor keeps
        # the component selected and leaves a floating overlay over it), so
        # every group after the first failed. Reloading also costs nothing in
        # correctness terms — Looker drops the filter selection on navigation
        # anyway, so it always had to be re-applied per page load.
        for group in groups:
            log.info(
                "Navigating to %s (%s) for %s / %s", page_def.title, url, period, group
            )
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                await assert_authenticated(page, self.settings.auth_file)
            except PlaywrightError as exc:
                log.error("Navigation to %s failed: %s", url, exc)
                result = ComboResult(page_def.slug, period.name, group, status="failed")
                result.errors.append(f"navigation failed: {exc}")
                bucket["groups"][group] = result.to_dict()
                self._save()
                continue

            render = await wait_for_render(
                page,
                self.settings.settle_seconds,
                self.settings.quota_retries,
                label=f"{page_def.slug}/{period.name}/{group}/load",
            )
            if not render.ok:
                log.warning(
                    "Load of %s for %s never came clean: %s",
                    page_def.slug,
                    group,
                    render.notes,
                )

            date_state: tuple[str, bool, str]
            try:
                date_state = await selectors.set_date_range_with_retries(
                    page, period.start, period.end, _sleep
                )
                log.info(
                    "%s/%s/%s date chip=%r verified=%s (%s)",
                    page_def.slug,
                    period.name,
                    group,
                    date_state[0],
                    date_state[1],
                    date_state[2],
                )
            except ControlError as exc:
                log.error(
                    "%s/%s/%s could not set the date range: %s",
                    page_def.slug,
                    period.name,
                    group,
                    exc,
                )
                date_state = ("", False, str(exc))

            await wait_for_render(
                page,
                self.settings.settle_seconds,
                self.settings.quota_retries,
                label=f"{page_def.slug}/{period.name}/{group}/after-date",
            )

            result = await self._capture_combo(page, page_def, period, group, date_state)
            bucket["groups"][group] = result.to_dict()
            self._save()
            log.info(
                "DONE page=%s period=%s group=%s status=%s date_chip=%s filter_chip=%s "
                "quota_retries=%d tiles=%d",
                page_def.slug,
                period.name,
                group,
                result.status,
                "OK" if result.date_ok else "FAIL",
                "OK" if result.filter_ok else "FAIL",
                result.quota_retries,
                len(result.tiles),
            )
            await asyncio.sleep(self.settings.pause_seconds)

    # -- one combination --------------------------------------------------

    async def _capture_combo(
        self,
        page: Page,
        page_def: ReportPage,
        period: Period,
        group: str,
        date_state: tuple[str, bool, str],
    ) -> ComboResult:
        result = ComboResult(page_def.slug, period.name, group)
        result.date_chip, result.date_ok, result.date_note = date_state
        self.recorder.reset()

        async def reapply() -> None:
            """Re-assert both controls; Looker can reset them mid-recovery."""
            chip, ok, note = await selectors.verify_date_chip(page, period.start, period.end)
            if not ok:
                chip, ok, note = await selectors.set_date_range_with_retries(
                    page, period.start, period.end, _sleep
                )
            result.date_chip, result.date_ok, result.date_note = chip, ok, note
            chip, ok, note = await selectors.set_landing_group_with_retries(page, group, _sleep)
            result.filter_chip, result.filter_ok, result.filter_note = chip, ok, note

        chip, ok, note = await selectors.set_landing_group_with_retries(page, group, _sleep)
        result.filter_chip, result.filter_ok, result.filter_note = chip, ok, note
        if not ok:
            # The control never responded after CONTROL_ATTEMPTS retries — the
            # exact reason is already logged by set_landing_group_with_retries.
            # Skip this one combination and move on, per the spec: never abort
            # the whole run over a single stuck control.
            result.status = "failed"
            result.errors.append(f"landing page group control never verified: {note}")
            return result

        render = await wait_for_render(
            page,
            self.settings.settle_seconds,
            self.settings.quota_retries,
            reapply=reapply,
            label=f"{page_def.slug}/{period.name}/{group}",
        )
        result.quota_retries = render.quota_retries
        result.errors.extend(render.notes)

        # Re-read the date chip: a quota recovery can have reset it.
        try:
            chip, ok, note = await selectors.verify_date_chip(page, period.start, period.end)
            result.date_chip, result.date_ok, result.date_note = chip, ok, note
        except ControlError as exc:
            result.date_ok = False
            result.date_note = str(exc)

        if not render.ok:
            result.status = "quota_error"
            result.errors.append(
                "captured nothing: the page was still showing a quota error after retries"
            )
            log.error(
                "%s/%s/%s abandoned after %d quota retries",
                page_def.slug,
                period.name,
                group,
                render.quota_retries,
            )
            return result

        if self.settings.dry_run:
            result.status = "ok" if (result.date_ok and result.filter_ok) else "partial"
            return result

        directory = self.combo_dir(page_def, period, group)
        directory.mkdir(parents=True, exist_ok=True)

        tiles: list[extract.Tile] = []
        try:
            tiles = await extract.collect(page)
            result.tiles = [tile.to_dict() for tile in tiles]
            self._write_tables(directory, tiles)
        except PlaywrightError as exc:
            result.errors.append(f"DOM extraction failed: {exc}")
            log.warning("DOM extraction failed for %s: %s", directory, exc)

        try:
            await self._screenshots(page, directory, result, tiles)
        except PlaywrightError as exc:
            result.errors.append(f"screenshots failed: {exc}")
            log.warning("Screenshots failed for %s: %s", directory, exc)

        result.network_files = self.recorder.flush(self.raw_dir(page_def, period, group))

        verified = bool(result.date_ok) and bool(result.filter_ok)
        result.status = "ok" if verified and not result.errors else "partial"
        return result

    # -- artefacts --------------------------------------------------------

    async def _screenshots(
        self,
        page: Page,
        directory: Path,
        result: ComboResult,
        tiles: list[extract.Tile],
    ) -> None:
        """full.png, canvas.png, and one clipped shot per report component.

        Clips come from the components extract.py found, NOT from iframes:
        Looker renders its charts in the main document, so the only iframe on
        the page is reCAPTCHA's and clipping to iframes produced a single
        screenshot of a reCAPTCHA badge.
        """
        full = directory / "full.png"
        await page.screenshot(path=str(full), full_page=True)
        result.screenshots.append(full.name)

        # Clipped shots pass full_page=True as well: a tile below the fold is
        # outside the viewport, and clip alone would be rejected as empty.
        bounds = await self._page_bounds(page)
        boxes = [(tile.index, tile.box) for tile in tiles if tile.box]
        area = union_box([box for _index, box in boxes])
        if area:
            canvas = directory / "canvas.png"
            try:
                await page.screenshot(
                    path=str(canvas), full_page=True, clip=self._pad(area, bounds, 16)
                )
                result.screenshots.append(canvas.name)
            except PlaywrightError as exc:
                result.errors.append(f"canvas screenshot failed: {exc}")

        for index, box in boxes:
            target = directory / f"tile_{index:02d}.png"
            try:
                await page.screenshot(
                    path=str(target),
                    full_page=True,
                    clip=self._pad(box, bounds, self.settings.tile_margin),
                )
                result.screenshots.append(target.name)
            except PlaywrightError as exc:
                # One unreachable tile must not cost us the rest of the combo.
                result.errors.append(f"tile {index} screenshot failed: {exc}")

    async def _page_bounds(self, page: Page) -> dict:
        viewport = page.viewport_size or {"width": 1680, "height": 2400}
        try:
            scroll = await page.evaluate(
                "() => ({width: document.documentElement.scrollWidth,"
                " height: document.documentElement.scrollHeight})"
            )
        except PlaywrightError:
            scroll = viewport
        return {
            "width": max(viewport["width"], scroll.get("width", 0)),
            "height": max(viewport["height"], scroll.get("height", 0)),
        }

    def _pad(self, box: dict, bounds: dict, margin: int) -> dict:
        x = max(0.0, box["x"] - margin)
        y = max(0.0, box["y"] - margin)
        width = min(box["width"] + 2 * margin, bounds["width"] - x)
        height = min(box["height"] + 2 * margin, bounds["height"] - y)
        return {"x": x, "y": y, "width": max(width, 1.0), "height": max(height, 1.0)}

    def _write_tables(self, directory: Path, tiles: list[extract.Tile]) -> None:
        for tile in tiles:
            if tile.kind != "table" or tile.table is None:
                continue
            target = directory / f"table_{tile.index:02d}.csv"
            with target.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                if tile.table.headers:
                    writer.writerow(tile.table.headers)
                writer.writerows(tile.table.rows)
                if tile.table.pagination_text:
                    writer.writerow([])
                    writer.writerow(["pagination", tile.table.pagination_text])
