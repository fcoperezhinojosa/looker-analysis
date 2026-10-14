"""Writing the run out: data.json, and the workbook's data*.py files.

The workbook files follow suntransfers-yoy-funnel/references/data-schema.md.
Two consequences of how build.py reads them shape the code below:

  * TOTALS is indexed directly (cy[lg][ch][dev]), so the full skeleton has to
    exist — unknown cells are written as None, never 0.
  * COUNTRIES rows are summed, so a row whose number could not be parsed is
    left out of the list entirely rather than carried through as None.

Attribution of a tile to a (channel, device) is done from the tile's own text.
Anything that cannot be attributed with certainty goes to UNMAPPED.md for a
human to resolve — it is never assigned a default.
"""

from __future__ import annotations

import json
import shutil
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import (
    CHANNEL_PATTERNS,
    CHANNELS,
    DEVICE_PRECEDENCE,
    DEVICES,
    LANDING_GROUPS,
    PAGES,
    Period,
)
from .extract import parse_number

log = logging.getLogger(__name__)

# variable-name prefixes per workbook data file
VARIABLES = {
    "data": ("TOTALS", "FULL_ROW_COUNTS", "COUNTRIES"),
    "data_ly": ("TOTALS_LY", "FULL_ROW_COUNTS_LY", "COUNTRIES_LY"),
    "data_start_search": (
        "STARTSEARCH_TOTALS",
        "FULL_ROW_COUNTS_STARTSEARCH",
        "STARTSEARCH_COUNTRIES",
    ),
    "data_start_search_ly": (
        "STARTSEARCH_TOTALS_LY",
        "FULL_ROW_COUNTS_STARTSEARCH_LY",
        "STARTSEARCH_COUNTRIES_LY",
    ),
    "data_search": ("SEARCH_TOTALS", "FULL_ROW_COUNTS_SEARCH", "SEARCH_COUNTRIES"),
    "data_search_ly": (
        "SEARCH_TOTALS_LY",
        "FULL_ROW_COUNTS_SEARCH_LY",
        "SEARCH_COUNTRIES_LY",
    ),
    "data_purchase": ("PURCHASE_TOTALS", "FULL_ROW_COUNTS_PURCHASE", "PURCHASE_COUNTRIES"),
    "data_select_item": (
        "SELECTITEM_TOTALS", "FULL_ROW_COUNTS_SELECTITEM", "SELECTITEM_COUNTRIES",
    ),
    "data_select_item_ly": (
        "SELECTITEM_TOTALS_LY", "FULL_ROW_COUNTS_SELECTITEM_LY", "SELECTITEM_COUNTRIES_LY",
    ),
    "data_add_to_cart": (
        "ADDTOCART_TOTALS", "FULL_ROW_COUNTS_ADDTOCART", "ADDTOCART_COUNTRIES",
    ),
    "data_add_to_cart_ly": (
        "ADDTOCART_TOTALS_LY", "FULL_ROW_COUNTS_ADDTOCART_LY", "ADDTOCART_COUNTRIES_LY",
    ),
    "data_begin_checkout": (
        "BEGINCHECKOUT_TOTALS", "FULL_ROW_COUNTS_BEGINCHECKOUT", "BEGINCHECKOUT_COUNTRIES",
    ),
    "data_begin_checkout_ly": (
        "BEGINCHECKOUT_TOTALS_LY", "FULL_ROW_COUNTS_BEGINCHECKOUT_LY",
        "BEGINCHECKOUT_COUNTRIES_LY",
    ),
    "data_purchase_ly": (
        "PURCHASE_TOTALS_LY",
        "FULL_ROW_COUNTS_PURCHASE_LY",
        "PURCHASE_COUNTRIES_LY",
    ),
}


def merge_results(existing: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    """Combine a previous run's pages with a new run's, per combination.

    An hour-long capture that dies near the end must not cost the 45
    combinations that already succeeded — this lets a short re-run of just the
    missing pages be folded into what is already on disk.

    Fresh data wins, but ONLY where it actually succeeded: a failed re-capture
    never overwrites a good earlier result with a blank.
    """
    merged: dict[str, Any] = json.loads(json.dumps(existing))  # deep copy
    for page_slug, page in fresh.items():
        target_page = merged.setdefault(page_slug, {"title": page.get("title"), "periods": {}})
        for period_name, period in page.get("periods", {}).items():
            target_period = target_page.setdefault("periods", {}).setdefault(
                period_name, {"range": period.get("range"), "url": period.get("url"), "groups": {}}
            )
            for group, combo in period.get("groups", {}).items():
                previous = target_period.setdefault("groups", {}).get(group)
                if (
                    previous is not None
                    and combo.get("status") not in ("ok", "partial")
                    and previous.get("status") in ("ok", "partial")
                ):
                    log.info(
                        "Keeping the earlier %s result for %s/%s/%s; the re-run was %s",
                        previous.get("status"),
                        page_slug,
                        period_name,
                        group,
                        combo.get("status"),
                    )
                    continue
                target_period["groups"][group] = combo
    return merged


def load_data_json(path: Path) -> dict[str, Any]:
    """The 'pages' section of a previous run, or {} if there is none."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("pages", {})
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read %s to merge into: %s", path, exc)
        return {}


def write_data_json(
    results: dict[str, Any], path: Path, meta: dict[str, Any], quiet: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "pages": results}
    # Write via a temp file and replace: a crash partway through a write would
    # otherwise leave truncated JSON where the completed combinations were.
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    if not quiet:
        log.info("Wrote %s", path)


# ---------------------------------------------------------------------------
# Tile attribution
# ---------------------------------------------------------------------------


@dataclass
class Unmapped:
    page: str
    period: str
    group: str
    tile_index: int
    kind: str
    title: str | None
    value_text: str | None
    reason: str


def _match_channel(text: str) -> tuple[str | None, str]:
    hits = [name for name, pattern in CHANNEL_PATTERNS.items() if pattern.search(text)]
    if len(hits) == 1:
        return hits[0], ""
    if not hits:
        return None, "no match"
    return None, f"ambiguous ({', '.join(hits)})"


def _match_device(text: str) -> tuple[str | None, str]:
    """First match wins, in Mobile -> Desktop -> Total order.

    Precedence, not uniqueness: "Mobile Total sessions - Paid" names both
    Mobile and Total, and rejecting that as ambiguous left every per-device
    scorecard unattributed and the workbook empty.

    A tile naming no device at all is the channel total — the Searches page
    labels its top tile "Searches - Paid Search traffic", with no "Total" in
    it, and its Mobile/Desktop siblings are the ones that say so explicitly.
    """
    for name, pattern in DEVICE_PRECEDENCE:
        if pattern.search(text):
            return name, ""
    return "Total", "no device named; read as the channel total"


def classify(
    tile: dict[str, Any],
    override: tuple[str, str] | None,
    metric_pattern: Any | None = None,
) -> tuple[str | None, str | None, str]:
    """Resolve a tile to (channel, device).

    Prefers what extract.py already worked out — a table's channel comes from
    its position on the page and its device from its own rows, neither of which
    is recoverable from the tile's text alone.
    """
    if override:
        return override[0], override[1], ""

    channel = tile.get("channel")
    channel_note = "" if channel else "no match"
    device: str | None = None
    device_note = ""

    if tile.get("kind") == "table":
        table = tile.get("table") or {}
        device = table.get("device")
        device_note = "" if device else "table rows named more than one device"
    else:
        text = " ".join(filter(None, [tile.get("title"), tile.get("raw_text")]))
        label = tile.get("title") or text
        if metric_pattern is not None and not metric_pattern.search(label):
            return None, None, (
                f"scorecard {label!r} is not this page's metric "
                f"(expected /{metric_pattern.pattern}/)"
            )
        if not channel:
            channel, channel_note = _match_channel(text)
        device, device_note = _match_device(text)

    if channel and channel not in CHANNELS:
        return None, device, f"channel {channel!r} has no column in the workbook"

    if channel and device:
        return channel, device, ""
    reason = "; ".join(
        part
        for part in (
            f"channel: {channel_note}" if not channel else "",
            f"device: {device_note}" if not device else "",
        )
        if part
    )
    return channel, device, reason


def _country_rows(table: dict[str, Any]) -> list[tuple[str, float]]:
    """Market plus its metric value, per row.

    extract.py emits [country, device, value, % delta], so the metric is the
    VALUE column — taking the last column instead would file the % change as
    the session count. A row whose metric will not parse is dropped, not zeroed.
    """
    rows: list[tuple[str, float]] = []
    for raw in table.get("rows", []):
        if len(raw) < 3:
            continue
        country = (raw[0] or "").strip()
        if not country:
            continue
        if country.lower() in {"total", "grand total", "totals"}:
            continue
        value, _abbrev, reason = parse_number(raw[2])
        if value is None:
            log.debug("Dropping country row %r: %s", raw, reason)
            continue
        rows.append((country, int(value) if float(value).is_integer() else value))
    return rows


# ---------------------------------------------------------------------------
# Workbook files
# ---------------------------------------------------------------------------


def _empty_totals() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        lg: {ch: {dev: None for dev in DEVICES} for ch in CHANNELS} for lg in LANDING_GROUPS
    }


def _empty_row_counts() -> dict[tuple[str, str, str], Any]:
    return {
        (lg, ch, dev): None
        for lg in LANDING_GROUPS
        for ch in CHANNELS
        for dev in ("Desktop", "Mobile")
    }


def _empty_countries() -> dict[tuple[str, str, str], list]:
    return {
        (lg, ch, dev): []
        for lg in LANDING_GROUPS
        for ch in CHANNELS
        for dev in ("Desktop", "Mobile")
    }


def _render_totals(name: str, totals: dict) -> str:
    lines = [f"{name} = {{"]
    for lg, channels in totals.items():
        lines.append(f'    "{lg}": {{')
        for ch, devices in channels.items():
            cells = ", ".join(f'"{dev}": {devices[dev]!r}' for dev in DEVICES)
            lines.append(f'        "{ch}": {{{cells}}},')
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def _render_keyed(name: str, data: dict, empty_repr: str) -> str:
    lines = [f"{name} = {{"]
    for key, value in data.items():
        rendered = repr(value) if value not in (None, [], {}) else empty_repr
        lines.append(f'    ("{key[0]}", "{key[1]}", "{key[2]}"): {rendered},')
    lines.append("}")
    return "\n".join(lines)


HEADER = '''# Generated by looker-yoy-capture on {stamp}.
# Source: Looker Studio report {report}, page "{page_title}" ({page_id}),
# period {start}..{end}, captured with the Landing Page Group control isolated
# per group.
#
# Rules this file obeys (suntransfers-yoy-funnel/references/data-schema.md):
#  * A value that could not be read is None (TOTALS / FULL_ROW_COUNTS) or an
#    absent row (COUNTRIES). It is never 0.
#  * Country names are copied verbatim from Looker, "(not set)" included.
#  * LANDING_GROUPS / CHANNELS / DEVICES are untouched.
#
# Check UNMAPPED.md next to this file before quoting anything: any tile the
# capture could not attribute to a (channel, device) is listed there and is
# missing from the dicts below.
'''

BASE_LISTS = '''
LANDING_GROUPS = {groups!r}
CHANNELS = {channels!r}
DEVICES = {devices!r}

# The period these numbers actually cover, taken from the report's own verified
# date chip. Exported as data, not just as the header comment above, so an
# analysis can assert it got the period it asked for. This matters because the
# workbook directory is reused by every run: a stale __pycache__ in it has
# silently served a previous period's numbers with no error at all.
PERIOD = {period!r}
PERIOD_NAME = {period_name!r}
CAPTURED_AT = {stamp!r}
'''


def write_workbook_files(
    results: dict[str, Any],
    periods: dict[str, Period],
    out_dir: Path,
    stamp: str,
    report_id: str,
    layout_map: dict[str, Any] | None = None,
) -> list[Unmapped]:
    """Emit the eight data*.py files. Returns everything left unattributed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    unmapped: list[Unmapped] = []
    layout_map = layout_map or {}

    for page_slug, page_data in results.items():
        page_def = PAGES.get(page_slug)
        if page_def is None or page_def.workbook_stem is None:
            continue
        page_layout = layout_map.get(page_slug, {})

        for period_name, period_data in page_data.get("periods", {}).items():
            period = periods.get(period_name)
            if period is None:
                continue
            stem = page_def.workbook_stem + ("_ly" if period_name == "prior" else "")
            totals_name, counts_name, countries_name = VARIABLES[stem]

            totals = _empty_totals()
            row_counts = _empty_row_counts()
            countries = _empty_countries()

            for group, combo in period_data.get("groups", {}).items():
                if group not in LANDING_GROUPS:
                    continue
                for tile in combo.get("tiles", []):
                    index = str(tile.get("index"))
                    override = None
                    raw_override = page_layout.get(index)
                    if isinstance(raw_override, list) and len(raw_override) == 2:
                        override = (raw_override[0], raw_override[1])

                    channel, device, reason = classify(
                        tile, override, page_def.metric_pattern
                    )
                    if not channel or not device:
                        unmapped.append(
                            Unmapped(
                                page_slug,
                                period_name,
                                group,
                                tile.get("index", -1),
                                tile.get("kind", "unknown"),
                                tile.get("title"),
                                tile.get("value_text"),
                                reason or "could not attribute",
                            )
                        )
                        continue

                    if tile.get("kind") == "scorecard":
                        value = tile.get("value")
                        if value is None or tile.get("abbreviated"):
                            unmapped.append(
                                Unmapped(
                                    page_slug,
                                    period_name,
                                    group,
                                    tile.get("index", -1),
                                    "scorecard",
                                    tile.get("title"),
                                    tile.get("value_text"),
                                    "value unreadable"
                                    if value is None
                                    else "Looker abbreviated the value (e.g. 12.3K)",
                                )
                            )
                            continue
                        clean = int(value) if float(value).is_integer() else value
                        existing = totals[group][channel][device]
                        if existing is not None and existing != clean:
                            # Two tiles claiming one cell means the attribution
                            # is wrong somewhere. Report both rather than let
                            # the last one silently win.
                            unmapped.append(
                                Unmapped(
                                    page_slug,
                                    period_name,
                                    group,
                                    tile.get("index", -1),
                                    "scorecard",
                                    tile.get("title"),
                                    tile.get("value_text"),
                                    f"collides with {existing} already mapped to "
                                    f"({channel}, {device}); left unmapped",
                                )
                            )
                            continue
                        totals[group][channel][device] = clean
                    elif tile.get("kind") == "table" and device in ("Desktop", "Mobile"):
                        table = tile.get("table") or {}
                        rows = _country_rows(table)
                        if rows:
                            countries[(group, channel, device)] = rows
                        pagination = table.get("pagination") or {}
                        if pagination.get("total") is not None:
                            row_counts[(group, channel, device)] = pagination["total"]

            body = "\n\n".join(
                [
                    HEADER.format(
                        stamp=stamp,
                        report=report_id,
                        page_title=page_def.title,
                        page_id=page_def.page_id,
                        start=period.start.isoformat(),
                        end=period.end.isoformat(),
                    )
                    + BASE_LISTS.format(
                        groups=LANDING_GROUPS,
                        channels=CHANNELS,
                        devices=DEVICES,
                        period=(period.start.isoformat(), period.end.isoformat()),
                        period_name=period_name,
                        stamp=stamp,
                    ),
                    _render_totals(totals_name, totals),
                    _render_keyed(counts_name, row_counts, "None"),
                    _render_keyed(countries_name, countries, "[]"),
                ]
            )
            target = out_dir / f"{stem}.py"
            target.write_text(body + "\n", encoding="utf-8")
            log.info("Wrote %s", target)

    # Drop any bytecode left by an earlier run over this directory. Python
    # served a stale __pycache__ here once and handed an analysis the previous
    # period's numbers, silently: the .py on disk held August, the .pyc held
    # the week before. Cheap to delete, and the alternative is a wrong readout
    # that looks perfectly plausible.
    cache = out_dir / "__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache, ignore_errors=True)
        log.info("Cleared stale bytecode in %s", cache)

    _write_unmapped(out_dir / "UNMAPPED.md", unmapped)
    return unmapped


def _write_unmapped(path: Path, unmapped: list[Unmapped]) -> None:
    if not unmapped:
        path.write_text(
            "# Unmapped tiles\n\nNone — every tile was attributed to a "
            "(channel, device).\n",
            encoding="utf-8",
        )
        return
    lines = [
        "# Unmapped tiles",
        "",
        "These tiles were captured but could not be attributed to a "
        "(channel, device) pair, so they are **missing** from the data*.py files.",
        "Nothing was guessed and nothing was defaulted to 0.",
        "",
        "Fix either by tuning `CHANNEL_PATTERNS` / `DEVICE_PATTERNS` in "
        "`looker_capture/config.py`, or by passing `--layout-map` with an "
        "explicit tile-index -> [channel, device] mapping per page.",
        "",
        "| page | period | landing group | tile | kind | title | value | why |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in unmapped:
        lines.append(
            f"| {item.page} | {item.period} | {item.group} | {item.tile_index} | "
            f"{item.kind} | {(item.title or '').replace('|', '/')[:40]} | "
            f"{(item.value_text or '')[:20]} | {item.reason} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.warning("%d tiles could not be attributed; see %s", len(unmapped), path)
