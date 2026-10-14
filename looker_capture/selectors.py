"""Locators for Looker Studio's custom controls.

These widgets are not standard HTML inputs — they are Material-ish components
whose class names are generated and change without notice. Everything here is
therefore addressed by role, aria-label or visible text, with a cascade of
fallbacks, and every action is verified by reading the control's own chip back.

Two hard rules, both learned the hard way:
  * Never press Escape to close one of these dropdowns — it cancels the
    selection instead of committing it.
  * Never drag. The report is driven in /edit mode, where a dragged component
    would be autosaved into the report for everyone.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date
from typing import Awaitable, Callable

from playwright.async_api import (
    Frame,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeout,
)

from . import dates
from .config import ALL_GROUPS, CONTROL_ATTEMPTS, CONTROL_BACKOFF_SECONDS, GROUP_ROW_PATTERNS
from .frames import ControlError, all_frames, chart_iframes, first_visible, union_box

log = logging.getLogger(__name__)

Sleep = Callable[[float], Awaitable[None]]

_ONLY_RE = re.compile(r"^\s*only\s*$", re.I)
_APPLY_RE = re.compile(r"^\s*(apply|aplicar|ok)\s*$", re.I)
_CUSTOM_RE = re.compile(r"^\s*(custom|fixed|personalizado|fecha personalizada)\b", re.I)
_GROUP_LABEL_RE = re.compile(r"landing\s*page\s*group", re.I)
_SELECT_ALL_RE = re.compile(r"^\s*(select all|all|\(all\)|todos|seleccionar todo)\s*$", re.I)

_POPUP_BUILDERS = [
    lambda f: f.locator('[role="listbox"]'),
    lambda f: f.locator('[role="menu"]'),
    lambda f: f.locator('[role="dialog"]'),
    lambda f: f.get_by_text(_ONLY_RE),
    lambda f: f.get_by_role("button", name=_APPLY_RE),
]


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------


async def popup_visible(page: Page) -> bool:
    return await first_visible(page, _POPUP_BUILDERS, timeout=600) is not None


async def close_dropdown(
    page: Page, sleep: Sleep, still_open: Callable[[], Awaitable[bool]] | None = None
) -> bool:
    """Commit an open dropdown by clicking empty canvas. Never Escape.

    Click points are chosen below / right / left of the block of charts, so the
    click always lands on the grey canvas surround rather than on a component.
    Stops at the first click that actually closes the panel, so it never keeps
    clicking around a canvas whose components could be selected by a stray hit.

    `still_open` lets the caller test the specific panel it opened; the generic
    popup_visible() default matches too broadly across frames to be reliable.
    """
    is_open = still_open or (lambda: popup_visible(page))
    boxes = [box for _, _, box, _ in await chart_iframes(page)]
    area = union_box(boxes)
    viewport = page.viewport_size or {"width": 1280, "height": 800}
    vw, vh = viewport["width"], viewport["height"]

    candidates: list[tuple[float, float]] = []
    if area:
        candidates += [
            (area["x"] + area["width"] / 2, area["y"] + area["height"] + 40),
            (area["x"] + area["width"] + 40, area["y"] + 20),
            (area["x"] - 40, area["y"] + area["height"] / 2),
        ]
    candidates += [(vw - 8, vh - 8), (8, vh - 8)]

    for x, y in candidates:
        if not (0 < x < vw and 0 < y < vh):
            continue
        await page.mouse.click(x, y)  # single click; no mouse.down/move/up anywhere
        await sleep(0.8)
        if not await is_open():
            return True
    log.warning("Dropdown still looks open after clicking every neutral point")
    return False


async def toggle_control(control: Locator, sleep: Sleep) -> None:
    """Click a control's toggle, immune to overlay interception.

    A real mouse click is the honest way to drive a control, but Looker leaves
    draggable cdk-overlay-panes sitting on top of its own controls; Playwright
    then refuses the click ("subtree intercepts pointer events") and times out
    after 30s on an element that is plainly visible. These controls are Angular
    components with ordinary click handlers, so dispatching the click on the
    element itself opens them regardless of what is floating above.
    """
    try:
        await control.click(timeout=5_000)
        return
    except Exception as exc:  # noqa: BLE001
        log.debug("Real click intercepted (%s); retrying forced", type(exc).__name__)
    # force=True still dispatches real mouse events at the element, it just
    # skips Playwright's "is anything on top of this?" guard — which is what
    # Looker's floating overlay panes trip.
    try:
        await control.click(timeout=5_000, force=True)
        return
    except Exception as exc:  # noqa: BLE001
        log.debug("Forced click failed (%s); dispatching a DOM click", type(exc).__name__)
    await control.evaluate("element => element.click()")
    await sleep(0.3)


async def open_control(
    control: Locator,
    is_open: Callable[[], Awaitable[bool]],
    sleep: Sleep,
    clicks: int = 3,
) -> bool:
    """Click a control until its panel opens.

    In /edit mode the first click on a control only SELECTS the component;
    a second click is what opens its dropdown. Which of the two a given click
    does depends on whether the component was already selected, so this cannot
    be assumed either way — it clicks and checks.
    """
    for attempt in range(clicks):
        if await is_open():
            return True
        try:
            await toggle_control(control, sleep)
        except Exception as exc:  # noqa: BLE001 - retry; the panel check decides
            log.debug("Control click %d/%d failed: %s", attempt + 1, clicks, exc)
        await sleep(1.5)
        if await is_open():
            return True
    return False


async def dismiss_overlays(page: Page, sleep: Sleep, attempts: int = 3) -> bool:
    """Clear any cdk overlay still floating over the canvas.

    Looker's date dialog is a draggable cdk-overlay-pane, and if it lingers it
    silently intercepts pointer events for every later control click — which
    surfaces as a 30s click timeout on a control that is plainly visible.
    Dismissing is always a backdrop click or an explicit Cancel, never Escape.
    """
    for _ in range(attempts):
        backdrop = page.locator(".cdk-overlay-backdrop-showing").first
        try:
            if await backdrop.count() and await backdrop.is_visible(timeout=500):
                # The backdrop is a transparent full-page layer; force past
                # Playwright's "is something on top of it" check.
                await backdrop.click(force=True)
                await sleep(0.8)
                continue
        except Exception:  # noqa: BLE001
            pass

        pane = page.locator(".cdk-overlay-pane").first
        try:
            if not await pane.count() or not await pane.is_visible(timeout=500):
                return True
        except Exception:  # noqa: BLE001
            return True

        cancel = pane.get_by_role("button", name=re.compile(r"^\s*(cancel|cancelar)\s*$", re.I)).first
        try:
            if await cancel.count() and await cancel.is_visible(timeout=500):
                await cancel.click()
                await sleep(0.8)
                continue
        except Exception:  # noqa: BLE001
            pass
        log.debug("An overlay pane is still present and offers no way to dismiss it")
        return False
    return False


async def _row_container(label: Locator) -> Locator:
    """The clickable row that owns a checklist label."""
    for xpath in (
        "xpath=ancestor-or-self::*[@role='option' or @role='menuitem' or "
        "@role='menuitemcheckbox' or @role='checkbox' or self::li or self::tr][1]",
        "xpath=ancestor::*[2]",
    ):
        try:
            candidate = label.locator(xpath).first
            if await candidate.count():
                return candidate
        except Exception:  # noqa: BLE001
            continue
    return label


# ---------------------------------------------------------------------------
# Date range control
# ---------------------------------------------------------------------------

_DATE_CONTROL_BUILDERS = [
    lambda f: f.locator('[aria-label*="Date range" i]'),
    lambda f: f.locator('[aria-label*="date-range" i]'),
    lambda f: f.get_by_role("button").filter(has_text=dates.DATE_RANGE_RE),
    lambda f: f.get_by_text(dates.DATE_RANGE_RE),
]


async def find_date_control(page: Page) -> tuple[Frame, Locator]:
    found = await first_visible(page, _DATE_CONTROL_BUILDERS)
    if not found:
        raise ControlError("date range control not found on the page")
    return found


async def read_date_chip(page: Page) -> str:
    _, locator = await find_date_control(page)
    return (await locator.inner_text(timeout=10_000)).strip()


_DIALOG_SELECTOR = ".canvas-date-picker-dialog, ng2-date-picker-dialog, .ng2-date-picker-dialog"
MAX_MONTH_STEPS = 48  # four years of paging, plenty for a YoY comparison


async def _open_date_dialog(page: Page, sleep: Sleep) -> Locator:
    """Click the chip and return the date picker dialog.

    The dialog is a cdk overlay in the main document, not in a chart iframe,
    and it lays a transparent backdrop over the page — so anything that tries
    to click the canvas while it is open will be intercepted.
    """
    await dismiss_overlays(page, sleep)
    _frame, control = await find_date_control(page)
    dialog = page.locator(_DIALOG_SELECTOR).first

    async def dialog_visible() -> bool:
        try:
            return await dialog.is_visible(timeout=800)
        except Exception:  # noqa: BLE001
            return False

    if not await open_control(control, dialog_visible, sleep):
        raise ControlError("the date range control did not open its picker dialog")
    return dialog


async def _pick_day(dialog: Locator, wrapper_class: str, day: date, sleep: Sleep) -> None:
    """Page a mat-calendar to the right month, then click the day cell.

    Days are buttons labelled "1 Aug 2026"; there is no text field to type
    into (an earlier version of this code tried, and ended up filling the
    edit-mode Properties panel's "start date offset" number box instead).
    """
    wrapper = dialog.locator(f".{wrapper_class}").first
    if not await wrapper.count():
        raise ControlError(f"date picker has no .{wrapper_class} calendar")

    period = wrapper.locator(".mat-calendar-period-button").first
    for _ in range(MAX_MONTH_STEPS):
        text = (await period.inner_text(timeout=5_000)).strip()
        current = dates.parse_month_year(text)
        if current is None:
            raise ControlError(f"could not read the calendar month from {text!r}")
        if current == (day.year, day.month):
            break
        going_back = (day.year, day.month) < current
        button = wrapper.locator(
            '[aria-label="Previous month"]' if going_back else '[aria-label="Next month"]'
        ).first
        await button.click()
        await sleep(0.35)
    else:
        raise ControlError(
            f"could not page the {wrapper_class} calendar to {day.isoformat()} "
            f"within {MAX_MONTH_STEPS} months"
        )

    label = dates.day_cell_label(day)
    cell = wrapper.locator(f'button.mat-calendar-body-cell[aria-label="{label}"]').first
    if not await cell.count():
        # Fall back to the visible day number, in case the aria-label is
        # localised differently than the English abbreviation we built.
        cell = (
            wrapper.locator(".mat-calendar-body-cell-content")
            .filter(has_text=re.compile(rf"^\s*{day.day}\s*$"))
            .first
        )
        if not await cell.count():
            raise ControlError(f"day cell {label!r} not found in the {wrapper_class} calendar")
    await cell.click()
    await sleep(0.5)


async def set_date_range(
    page: Page, start: date, end: date, sleep: Sleep
) -> tuple[str, bool, str]:
    """Set and verify the date range. Returns (chip_text, matched, note)."""
    dialog = await _open_date_dialog(page, sleep)

    await _pick_day(dialog, "start-date-picker", start, sleep)
    await _pick_day(dialog, "end-date-picker", end, sleep)

    apply_button = dialog.get_by_role("button", name=_APPLY_RE).first
    if not await apply_button.count():
        raise ControlError("no Apply button in the date picker dialog")
    await apply_button.click()
    # Wait for the dialog to actually go: while it lingers it intercepts every
    # later control click, which shows up as an inexplicable click timeout.
    try:
        await dialog.wait_for(state="hidden", timeout=15_000)
    except PlaywrightTimeout:
        log.warning("Date dialog did not close after Apply; dismissing it")
        await dismiss_overlays(page, sleep)
    await sleep(3.0)

    chip_text = await read_date_chip(page)
    matched, note = dates.range_matches(chip_text, start, end)
    return chip_text, matched, note


async def verify_date_chip(page: Page, start: date, end: date) -> tuple[str, bool, str]:
    chip_text = await read_date_chip(page)
    matched, note = dates.range_matches(chip_text, start, end)
    return chip_text, matched, note


# ---------------------------------------------------------------------------
# Landing Page Group control
# ---------------------------------------------------------------------------

_GROUP_CONTROL_BUILDERS = [
    lambda f: f.locator('[aria-label*="Landing Page Group" i]'),
    lambda f: f.get_by_role("button").filter(has_text=_GROUP_LABEL_RE),
    lambda f: f.get_by_text(_GROUP_LABEL_RE),
]


async def find_group_control(page: Page) -> tuple[Frame, Locator]:
    found = await first_visible(page, _GROUP_CONTROL_BUILDERS)
    if not found:
        raise ControlError("Landing Page Group control not found on the page")
    return found


_CHIP_TEXT_JS = """() => {
  // The authoritative "what is actually filtered" indicator is the report's
  // applied-filters bar, which reads e.g. "Landing Page Group Home page (1)".
  //
  // Not to be confused with the editor's field chip (ng2-concept-chip /
  // .common-chip, whose .left-half carries aria-label="Landing Page Group"):
  // that one only ever shows the FIELD NAME, with no selection or count, so
  // reading it made every applied filter look unapplied.
  const bar = document.querySelector('[aria-label*="Filters applied" i]');
  if (bar) {
    const t = (bar.innerText || '').replace(/\\s+/g, ' ').trim();
    if (t) return t;
  }
  // Fallback: the on-canvas control's own chip, which renders the selection
  // as "Landing Page Group: Home pa... (1)".
  const anchor = [...document.querySelectorAll('.left-half[aria-label]')]
    .find(e => /landing\\s*page\\s*group/i.test(e.getAttribute('aria-label') || ''));
  if (!anchor) return '';
  let best = '', e = anchor;
  for (let i = 0; i < 5 && e; i++, e = e.parentElement) {
    const t = (e.innerText || '').replace(/\\s+/g, ' ').trim();
    if (t && t.length < 160 && /landing\\s*page\\s*group/i.test(t) && t.length > best.length) {
      best = t;
    }
  }
  return best;
}"""


async def read_group_chip(page: Page, attempts: int = 4) -> str:
    """Read the filter chip's visible text, retrying while it re-renders.

    Done in JS across frames rather than via the aria-labelled element: that
    element is a wrapper div whose own innerText is empty, which previously
    produced a blank chip that then "verified" as all-groups-selected.
    """
    for attempt in range(attempts):
        for frame in all_frames(page):
            try:
                text = await frame.evaluate(_CHIP_TEXT_JS)
            except Exception:  # noqa: BLE001 - frame detached mid-render
                continue
            if text:
                return str(text).strip()
        if attempt + 1 < attempts:
            await asyncio.sleep(1.0)
    return ""


def verify_group_chip(chip_text: str, group: str) -> tuple[bool, str]:
    """Does the applied-filters bar show exactly this group isolated?

    The bar reads "Add filter Landing Page Group Home page (1)" when one group
    is isolated, and just "Add filter" when nothing is filtered — which is what
    the unfiltered (all groups) view looks like. An empty read is never treated
    as evidence either way.
    """
    text = (chip_text or "").strip()
    if not text:
        return False, "filter chip read back empty; the selection cannot be confirmed"

    squashed = re.sub(r"[^a-z0-9]", "", text.lower())
    has_count = re.search(r"\(\s*\d+\s*\)", text) is not None

    if group == ALL_GROUPS:
        if has_count:
            return False, f"chip {text!r} still shows an active filter selection"
        return True, "no Landing Page Group filter applied, reading as all groups"

    if "landingpagegroup" not in squashed:
        return False, f"chip {text!r} shows no Landing Page Group filter"
    # Looker truncates long chips ("Home p..."), so match on a short prefix.
    prefix = re.sub(r"[^a-z0-9]", "", group.lower())[:4]
    if prefix not in squashed:
        return False, f"chip {text!r} does not mention {group!r}"
    if not has_count:
        return False, f"chip {text!r} mentions {group!r} but shows no selection count"
    return True, "matched"


_SELECT_ALL_CHECKBOX = 'md-checkbox[aria-label*="(Select all)"]'
_ONLY_LINK = "span.only"


def _group_checkbox_selector(group: str) -> str:
    escaped = group.replace('"', '\\"')
    return f'md-checkbox[aria-label="{escaped}"]'


_CHECKBOX_STATE_JS = """() => {
  const out = {};
  document.querySelectorAll('md-checkbox[aria-label]').forEach(e => {
    out[e.getAttribute('aria-label')] = e.classList.contains('md-checked');
  });
  return out;
}"""


async def _checkbox_state(frame: Frame) -> dict[str, bool]:
    """Every checklist row's label -> ticked?  (state is the md-checked class)."""
    try:
        return await frame.evaluate(_CHECKBOX_STATE_JS)
    except Exception as exc:  # noqa: BLE001
        raise ControlError(f"could not read the Landing Page Group checklist: {exc}") from exc


def _select_all_key(state: dict[str, bool]) -> str | None:
    for label in state:
        if "select all" in label.lower():
            return label
    return None


def _ticked_groups(state: dict[str, bool]) -> list[str]:
    """Ticked rows, excluding the (Select all) row itself."""
    select_all = _select_all_key(state)
    return [label for label, on in state.items() if on and label != select_all]


async def _is_checked(checkbox: Locator) -> bool:
    classes = (await checkbox.get_attribute("class") or "").split()
    return "md-checked" in classes


async def _clear_all(frame: Frame, sleep: Sleep) -> None:
    """Untick everything via the (Select all) box, which toggles."""
    select_all = frame.locator(_SELECT_ALL_CHECKBOX).first
    if not await select_all.count():
        raise ControlError("no '(Select all)' checkbox in the Landing Page Group list")
    for _ in range(4):
        if not _ticked_groups(await _checkbox_state(frame)):
            return
        await select_all.click()
        await sleep(1.0)
    raise ControlError("could not clear the Landing Page Group selection")


async def _select_all_groups(frame: Frame, sleep: Sleep) -> None:
    select_all = frame.locator(_SELECT_ALL_CHECKBOX).first
    if not await select_all.count():
        raise ControlError("no '(Select all)' checkbox in the Landing Page Group list")
    for _ in range(4):
        state = await _checkbox_state(frame)
        ticked = _ticked_groups(state)
        if ticked and len(ticked) == len(state) - (1 if _select_all_key(state) else 0):
            return
        await select_all.click()
        await sleep(1.0)
    raise ControlError("could not select every Landing Page Group")


async def _isolate_group(frame: Frame, group: str, sleep: Sleep) -> str:
    """Leave exactly one group ticked, verified inside the panel.

    Clear-then-tick is the primary path because it is deterministic. The ONLY
    hover link is used only as a shortcut, and either way success is checked by
    counting ticked rows — an earlier version asked "is the target ticked?",
    which is trivially true when every row starts ticked, so it reported
    success without the filter ever being applied.
    """
    checkbox = frame.locator(_group_checkbox_selector(group)).first
    if not await checkbox.count():
        raise ControlError(f"no checkbox labelled {group!r} in the Landing Page Group list")

    how = "clear-then-tick"
    row = checkbox.locator("xpath=..")
    try:
        await row.hover()
        await sleep(0.6)
        only = row.locator(_ONLY_LINK).first
        if await only.count() and await only.is_visible(timeout=1_500):
            await only.click()
            await sleep(1.2)
            if _ticked_groups(await _checkbox_state(frame)) == [group]:
                return "ONLY link"
            log.debug("ONLY link did not isolate %s; clearing and ticking instead", group)
    except PlaywrightTimeout:
        pass
    except Exception as exc:  # noqa: BLE001
        log.debug("ONLY link unusable for %s: %s", group, exc)

    await _clear_all(frame, sleep)
    if not await _is_checked(checkbox):
        await checkbox.click()
        await sleep(1.0)

    ticked = _ticked_groups(await _checkbox_state(frame))
    if ticked != [group]:
        raise ControlError(
            f"expected only {group!r} ticked, but the list shows {ticked!r}"
        )
    return how


async def set_landing_group(page: Page, group: str, sleep: Sleep) -> tuple[str, bool, str]:
    """Isolate one landing page group (or select them all). Returns the chip."""
    await dismiss_overlays(page, sleep)
    frame, control = await find_group_control(page)

    async def checklist_visible() -> bool:
        try:
            return await frame.locator(_SELECT_ALL_CHECKBOX).first.is_visible(timeout=800)
        except Exception:  # noqa: BLE001
            return False

    if not await open_control(control, checklist_visible, sleep):
        raise ControlError("Landing Page Group control did not open its checklist")

    if group == ALL_GROUPS:
        await _select_all_groups(frame, sleep)
        how = "select all"
    else:
        how = await _isolate_group(frame, group, sleep)

    await sleep(1.0)
    # Close by toggling the control itself. Clicking the canvas to dismiss can
    # land on a component and change the editor's selection state, which then
    # stops the next control from opening at all.
    if await checklist_visible():
        try:
            await toggle_control(control, sleep)
            await sleep(1.2)
        except Exception as exc:  # noqa: BLE001
            log.debug("Toggling the control closed failed: %s", exc)
    if await checklist_visible():
        await close_dropdown(page, sleep, still_open=checklist_visible)
    await sleep(1.5)

    chip_text = await read_group_chip(page)
    ok, note = verify_group_chip(chip_text, group)
    return chip_text, ok, f"{note} (via {how})"


# ---------------------------------------------------------------------------
# Outer retry: "control did not respond after 3 attempts" from the spec.
# ---------------------------------------------------------------------------
# set_date_range/set_landing_group already retry internally in narrower ways
# (date format guessing, the ONLY-link fallback); this is the outer envelope
# for when the control just did not respond at all — an exception, or a chip
# that never verifies. It never raises: the caller gets the last (chip, ok,
# note) it saw and logs+continues, matching "no abortar todo el script".


async def _with_control_retries(
    action: Callable[[], Awaitable[tuple[str, bool, str]]],
    describe: str,
    sleep: Sleep,
    attempts: int = CONTROL_ATTEMPTS,
) -> tuple[str, bool, str]:
    last: tuple[str, bool, str] = ("", False, "control never attempted")
    for attempt in range(attempts):
        try:
            chip, ok, note = await action()
        except ControlError as exc:
            last = ("", False, str(exc))
        else:
            last = (chip, ok, note)
            if ok:
                return last
        if attempt + 1 < attempts:
            backoff = CONTROL_BACKOFF_SECONDS[min(attempt, len(CONTROL_BACKOFF_SECONDS) - 1)]
            log.warning(
                "%s did not verify on attempt %d/%d (%s); retrying in %.0fs",
                describe,
                attempt + 1,
                attempts,
                last[2],
                backoff,
            )
            await sleep(backoff)
    log.error("%s failed after %d attempts: %s", describe, attempts, last[2])
    return last


async def set_date_range_with_retries(
    page: Page, start: date, end: date, sleep: Sleep
) -> tuple[str, bool, str]:
    return await _with_control_retries(
        lambda: set_date_range(page, start, end, sleep),
        f"date range control ({start.isoformat()}..{end.isoformat()})",
        sleep,
    )


async def set_landing_group_with_retries(
    page: Page, group: str, sleep: Sleep
) -> tuple[str, bool, str]:
    return await _with_control_retries(
        lambda: set_landing_group(page, group, sleep),
        f"landing page group control ({group})",
        sleep,
    )
