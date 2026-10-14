"""Browser-level checks against a fixture page shaped like a Looker report.

This cannot reach the real report (that needs an authenticated Google session),
but it does exercise the actual Playwright plumbing: iframe discovery, tile
extraction across frames, chip reads, quota detection and tile screenshots.

Run: .venv/bin/python tests/test_browser.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.async_api import async_playwright  # noqa: E402

from looker_capture import export, extract, selectors, waits  # noqa: E402
from looker_capture.capture import ComboResult, Runner, Settings  # noqa: E402
from looker_capture.netcapture import NetworkRecorder  # noqa: E402
from looker_capture.frames import chart_iframes, union_box  # noqa: E402

FIXTURE = (Path(__file__).parent / "fixture" / "report.html").resolve()
FAILURES: list[str] = []


def check(label: str, got, expected) -> None:
    if got != expected:
        FAILURES.append(f"{label}: expected {expected!r}, got {got!r}")


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1000}, device_scale_factor=2
        )
        page = await context.new_page()
        await page.goto(FIXTURE.as_uri())
        await page.wait_for_timeout(500)

        # -- chips ------------------------------------------------------
        date_chip = await selectors.read_date_chip(page)
        check("date chip text", date_chip, "1 Aug 2026 - 23 Aug 2026")
        _chip, matched, note = await selectors.verify_date_chip(
            page, date(2026, 8, 1), date(2026, 8, 23)
        )
        check("date chip verifies", matched, True)
        _chip, wrong, _note = await selectors.verify_date_chip(
            page, date(2025, 8, 1), date(2025, 8, 23)
        )
        check("date chip rejects the wrong year", wrong, False)

        group_chip = await selectors.read_group_chip(page)
        check("group chip text", group_chip, "Add filter Landing Page Group Home page (1)")
        ok, _ = selectors.verify_group_chip(group_chip, "Home page")
        check("group chip verifies", ok, True)

        # -- the only iframe is reCAPTCHA's -----------------------------
        # Charts are NOT in iframes; an earlier version of extract.py assumed
        # they were, found only this frame, and produced an empty workbook.
        tiles_meta = await chart_iframes(page)
        check("the sole iframe is reCAPTCHA", len(tiles_meta), 1)
        area = union_box([box for _, _, box, _ in tiles_meta])
        check("union box computed", area is not None, True)

        # -- extraction from the main DOM --------------------------------
        tiles = await extract.collect(page)
        scorecards = [t for t in tiles if t.kind == "scorecard"]
        tables = [t for t in tiles if t.kind == "table"]
        check("scorecards extracted", len(scorecards), 7)
        check("tables extracted", len(tables), 4)
        check("controls are not mistaken for components",
              any("arrow_drop_down" in (t.raw_text or "") for t in tiles), False)

        by_title = {t.title: t for t in scorecards}
        paid_total = by_title["Total sessions - Paid Search traffic"]
        check("scorecard value parsed", paid_total.value, 63399.0)
        check("scorecard channel resolved", paid_total.channel, "Paid Search")
        check("scorecard delta captured", paid_total.delta_text, "-27.6%")

        # The short channel forms on the per-device tiles must still resolve.
        check("short 'Paid' resolves", by_title["Mobile Total sessions - Paid"].channel, "Paid Search")
        check("short 'Org' resolves", by_title["Desktop Total sessions - Org"].channel, "Organic")

        abbreviated = by_title["Desktop Total sessions - Direct"]
        check("abbreviated value flagged", abbreviated.abbreviated, True)
        check("abbreviated value notes precision loss", bool(abbreviated.notes), True)
        check("abbreviated value still parsed", abbreviated.value, 12300.0)

        # Tables: channel from page position, device from their own rows.
        paid_desktop = [t for t in tables if t.channel == "Paid Search"
                        and t.table.device == "Desktop"]
        check("paid desktop table found", len(paid_desktop), 1)
        table = paid_desktop[0].table
        check("table row count", len(table.rows), 3)
        check("table first row", table.rows[0], ["United Kingdom", "desktop", "6,044", "-38.1%"])
        check("(not set) kept verbatim", table.rows[2][0], "(not set)")
        check("pagination verbatim", table.pagination_text, "1 - 100 / 154")
        check("pagination total", table.pagination["total"], 154)

        check("paid mobile table found",
              len([t for t in tables if t.channel == "Paid Search"
                   and t.table.device == "Mobile"]), 1)
        check("organic desktop table found",
              len([t for t in tables if t.channel == "Organic"
                   and t.table.device == "Desktop"]), 1)

        # The Newsletter table must keep its own channel, not drift onto a
        # workbook channel — that would file Newsletter markets under Direct.
        newsletter = [t for t in tables if t.channel == "Newsletter"]
        check("newsletter table keeps its own channel", len(newsletter), 1)
        check("newsletter table is not attributed to a workbook channel",
              all(t.channel != "Direct" for t in tables if t.table.pagination
                  and t.table.pagination["total"] == 46), True)
        ch, dev, why = export.classify(newsletter[0].to_dict(), None)
        check("newsletter table is refused by the workbook mapper", ch, None)
        check("newsletter refusal explains itself", "no column" in why, True)

        # -- screenshots -------------------------------------------------
        out = Path("/tmp/looker_capture_browsertest")
        out.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out / "full.png"), full_page=True)
        index, box = tables[0].index, tables[0].box
        await page.screenshot(
            path=str(out / f"tile_{index:02d}.png"),
            clip={
                "x": box["x"] - 8,
                "y": box["y"] - 8,
                "width": box["width"] + 16,
                "height": box["height"] + 16,
            },
        )
        full_size = (out / "full.png").stat().st_size
        tile_size = (out / f"tile_{index:02d}.png").stat().st_size
        check("full screenshot written", full_size > 1000, True)
        check("tile screenshot written", tile_size > 500, True)
        check("tile screenshot is smaller than the full page", tile_size < full_size, True)

        # -- Runner artefacts, with tiles below the fold -----------------
        # A short viewport puts the lower tiles outside it, which is what
        # broke clipped screenshots before full_page was passed alongside clip.
        short = await browser.new_context(
            viewport={"width": 800, "height": 400}, device_scale_factor=2
        )
        short_page = await short.new_page()
        await short_page.goto(FIXTURE.as_uri())
        await short_page.wait_for_timeout(400)

        runner_out = Path("/tmp/looker_capture_runnertest")
        shutil.rmtree(runner_out, ignore_errors=True)
        runner_out.mkdir(parents=True)
        runner = Runner(
            short,
            Settings(output_dir=runner_out, auth_file=Path("auth.json")),
            NetworkRecorder(enabled=False),
        )
        result = ComboResult("sessions", "current", "Home page")
        short_tiles = await extract.collect(short_page)
        await runner._screenshots(short_page, runner_out, result, short_tiles)
        written = sorted(f.name for f in runner_out.glob("*.png"))
        check("full page shot written", "full.png" in written, True)
        check("canvas shot written", "canvas.png" in written, True)
        check(
            "one shot per component, all of them below the fold included",
            len([n for n in written if n.startswith("tile_")]),
            len([t for t in short_tiles if t.box]),
        )
        check("no screenshot errors recorded", result.errors, [])

        runner._write_tables(runner_out, short_tiles)
        csvs = sorted(f.name for f in runner_out.glob("*.csv"))
        check(
            "one CSV per table tile",
            len(csvs),
            len([t for t in short_tiles if t.kind == "table"]),
        )
        joined = "\n".join((runner_out / name).read_text() for name in csvs)
        check("CSV carries the rows", "United Kingdom,desktop,\"6,044\"" in joined, True)
        check("CSV carries the pagination footer verbatim", "1 - 100 / 154" in joined, True)
        shutil.rmtree(runner_out, ignore_errors=True)

        await short.close()

        # -- outer control retries ---------------------------------------
        # A control that never appears must exhaust CONTROL_ATTEMPTS, log the
        # reason, and return ok=False instead of raising — so one stuck combo
        # never aborts the whole run.
        from looker_capture.config import CONTROL_ATTEMPTS

        calls = {"n": 0}

        async def _always_fails():
            calls["n"] += 1
            raise selectors.ControlError("simulated: control never responded")

        async def _fast_sleep(_seconds):
            return None

        chip, ok, note = await selectors._with_control_retries(
            _always_fails, "fake control", _fast_sleep
        )
        check("exhausted retries return ok=False, not raise", ok, False)
        check("exhausted retries report the real reason", "never responded" in note, True)
        check("exhausted retries used every attempt", calls["n"], CONTROL_ATTEMPTS)

        # And a control that fails once then recovers should succeed without
        # burning every attempt.
        calls["n"] = 0

        async def _fails_once_then_ok():
            calls["n"] += 1
            if calls["n"] == 1:
                raise selectors.ControlError("simulated: transient failure")
            return "chip text", True, "matched"

        chip, ok, note = await selectors._with_control_retries(
            _fails_once_then_ok, "flaky control", _fast_sleep
        )
        check("recovers after a transient failure", ok, True)
        check("stops retrying once it succeeds", calls["n"], 2)

        await context.close()
        await browser.close()


asyncio.run(main())

if FAILURES:
    print(f"{len(FAILURES)} failure(s):")
    for line in FAILURES:
        print(f"  - {line}")
    sys.exit(1)
print("all browser checks passed")
