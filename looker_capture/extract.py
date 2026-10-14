"""Pulling numbers out of the DOM rather than off a screenshot.

Looker Studio does NOT render its charts in iframes — the only iframe on the
report page is reCAPTCHA's. Every component (scorecard and table alike) is a
`div.lego-component-repeat` in the main document, and its `innerText` already
carries everything needed:

  scorecard: "Total sessions - Paid Search traffic 63,399 -27.6%"
  table:     "Country Device category Sessions % Δ 1. United Kingdom desktop
              6,044 -38.1% 2. Germany desktop 4,966 -20.5% ... 1 - 100 / 154"

An earlier version of this module walked page.frames looking for chart
iframes; it found only the reCAPTCHA frame, so every capture reported one
unreadable tile and the workbook came out empty.

The cardinal rule from the workbook's data-schema reference still holds: a
value that could not be read is None with a reason attached. It is never 0.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from playwright.async_api import Page

log = logging.getLogger(__name__)

COMPONENT_SELECTOR = ".lego-component-repeat"

# "1 - 100 / 155", "1-10 of 187", "1 - 95 / 95"
PAGINATION_RE = re.compile(
    r"(\d[\d.,\s]*?)\s*[-–—]\s*(\d[\d.,\s]*?)\s*(?:/|of|de)\s*(\d[\d.,\s]*)", re.I
)

# A table's header, which is what identifies a component as a country table.
TABLE_HEADER_RE = re.compile(r"country\s+device\s*categ", re.I)

# "1. United Kingdom desktop 6,044 -38.1%"  (delta may be "-", "N/A" or absent)
TABLE_ROW_RE = re.compile(
    r"(?P<rank>\d+)\.\s+"
    r"(?P<country>.+?)\s+"
    r"(?P<device>desktop|mobile|tablet)\s+"
    r"(?P<value>[\d.,]+)"
    r"(?:\s+(?P<delta>-?[\d.,]+%|N/A|-))?"
    r"(?=\s+\d+\.\s|\s*$|\s*\d[\d.,\s]*\s*[-–—])",
    re.I,
)

# "Total sessions - Paid Search traffic 63,399 -27.6%"
# The value may carry Looker's own abbreviation suffix ("12.3K"); it has to be
# accepted here so the tile is recognised at all, and parse_number then flags
# the lost precision rather than the tile being silently dropped.
SCORECARD_RE = re.compile(
    r"^(?P<label>.*?[A-Za-z].*?)\s+"
    r"(?P<value>\d[\d.,]*\s?[KkMmBb]?)"
    r"(?:\s+(?P<delta>-?[\d.,]+%|N/A))?\s*$"
)

_NUMBER_RE = re.compile(r"^-?[\d.,\s]+(?:[KkMmBb])?%?$")
_ABBREV = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}

_COMPONENTS_JS = """(selector) => {
  return [...document.querySelectorAll(selector)].map((e, i) => {
    const r = e.getBoundingClientRect();
    return {
      index: i,
      text: (e.innerText || '').replace(/\\s+/g, ' ').trim(),
      box: {x: r.x, y: r.y, width: r.width, height: r.height},
    };
  }).filter(c => c.text && c.box.width > 20 && c.box.height > 10);
}"""


@dataclass
class Table:
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    device: str | None = None
    pagination_text: str | None = None
    pagination: dict[str, int | None] | None = None


@dataclass
class Tile:
    index: int
    kind: str  # "scorecard" | "table" | "unknown"
    title: str | None = None
    value_text: str | None = None
    value: float | None = None
    delta_text: str | None = None
    abbreviated: bool = False
    channel: str | None = None  # resolved for tables by vertical alignment
    table: Table | None = None
    raw_text: str = ""
    box: dict[str, float] | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.table is None:
            data.pop("table")
        return data


def parse_number(text: str) -> tuple[float | None, bool, str | None]:
    """(value, was_abbreviated, reason_if_unparsed).

    Returns None rather than a guess whenever the text is not plainly a number —
    a missing value must stay missing all the way to the output files.
    """
    raw = (text or "").strip()
    if not raw or not _NUMBER_RE.match(raw):
        return None, False, f"not a plain number: {raw!r}"

    body = raw.rstrip("%").strip()
    multiplier = 1
    abbreviated = False
    if body and body[-1].lower() in _ABBREV:
        multiplier = _ABBREV[body[-1].lower()]
        abbreviated = True
        body = body[:-1].strip()

    body = body.replace(" ", "")
    if "," in body and "." in body:
        decimal = "," if body.rfind(",") > body.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        body = body.replace(thousands, "").replace(decimal, ".")
    elif "," in body:
        parts = body.split(",")
        body = body.replace(",", "") if len(parts[-1]) == 3 else body.replace(",", ".")
    elif body.count(".") > 1:
        body = body.replace(".", "")
    elif "." in body:
        parts = body.split(".")
        if len(parts[-1]) == 3:
            body = body.replace(".", "")

    try:
        return float(body) * multiplier, abbreviated, None
    except ValueError:
        return None, abbreviated, f"could not parse {raw!r} as a number"


def parse_pagination(text: str) -> tuple[str | None, dict[str, int | None] | None]:
    """Return the footer verbatim plus a parsed view of it."""
    matches = list(PAGINATION_RE.finditer(text or ""))
    if not matches:
        return None, None
    match = matches[-1]  # the footer is at the end, after all the rows
    verbatim = match.group(0).strip()
    first, _, _ = parse_number(match.group(1))
    last, _, _ = parse_number(match.group(2))
    total, _, _ = parse_number(match.group(3))
    return verbatim, {
        "first": int(first) if first is not None else None,
        "last": int(last) if last is not None else None,
        "total": int(total) if total is not None else None,
    }


def _strip_pagination(text: str) -> str:
    match = PAGINATION_RE.search(text)
    return text[: match.start()] if match else text


def parse_table(text: str) -> Table | None:
    """Parse a country table out of one component's flattened text."""
    if not TABLE_HEADER_RE.search(text):
        return None
    table = Table()
    table.pagination_text, table.pagination = parse_pagination(text)
    table.headers = ["Country", "Device category", "Value", "% Delta"]

    body = _strip_pagination(text)
    devices: set[str] = set()
    for match in TABLE_ROW_RE.finditer(body):
        country = match.group("country").strip()
        # The header words sit immediately before row 1; drop any leftover.
        country = re.sub(r"^.*?%\s*Δ\s*", "", country).strip()
        country = re.sub(r"^(Country|Device category|Sessions|% Δ)\s*", "", country).strip()
        if not country:
            continue
        device = match.group("device").lower()
        devices.add(device)
        table.rows.append(
            [country, device, match.group("value"), (match.group("delta") or "").strip()]
        )
    if not table.rows:
        return None
    # A table is a single (channel, device) view, so one device should dominate.
    table.device = devices.pop().capitalize() if len(devices) == 1 else None
    return table


def parse_scorecard(text: str) -> tuple[str | None, str | None, str | None]:
    """(label, value_text, delta_text) from a scorecard's flattened text."""
    match = SCORECARD_RE.match(text)
    if not match:
        return None, None, None
    return (
        match.group("label").strip(),
        match.group("value"),
        (match.group("delta") or "").strip() or None,
    )


def _looks_like_a_control(text: str) -> bool:
    """Date-range and filter controls are components too; skip them."""
    lowered = text.lower()
    return (
        "arrow_drop_down" in lowered
        or lowered.startswith("landing page group")
        or bool(re.match(r"^\d{1,2}\s+\w{3,}\s+\d{4}\s*[-–]", text))
    )


def _channel_of(text: str) -> str | None:
    """The channel a scorecard label names, if any.

    Uses ANCHOR_CHANNEL_PATTERNS (workbook channels plus Newsletter etc.) so a
    non-workbook channel still anchors its own tables instead of letting them
    drift onto the nearest workbook channel.
    """
    from .config import ANCHOR_CHANNEL_PATTERNS

    hits = [
        name for name, pattern in ANCHOR_CHANNEL_PATTERNS.items() if pattern.search(text)
    ]
    return hits[0] if len(hits) == 1 else None


def _assign_table_channels(tiles: list[Tile]) -> None:
    """Give each table the channel of the scorecard block it sits beside.

    Table components carry no channel of their own — on the page each channel is
    a row: its scorecards down the left, its Desktop and Mobile country tables to
    the right. So a table takes the channel of the vertically nearest channel
    scorecard, and its device comes from its own rows.
    """
    anchors = [
        (tile.box["y"] + tile.box["height"] / 2, tile.channel)
        for tile in tiles
        if tile.kind == "scorecard" and tile.channel and tile.box
    ]
    if not anchors:
        return
    for tile in tiles:
        if tile.kind != "table" or not tile.box:
            continue
        centre = tile.box["y"] + tile.box["height"] / 2
        nearest = min(anchors, key=lambda a: abs(a[0] - centre))
        tile.channel = nearest[1]
        tile.notes.append(
            f"channel {nearest[1]!r} taken from the nearest scorecard block "
            f"({abs(nearest[0] - centre):.0f}px away)"
        )


async def collect(page: Page) -> list[Tile]:
    """Read every report component out of the main document."""
    try:
        components = await page.evaluate(_COMPONENTS_JS, COMPONENT_SELECTOR)
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not enumerate report components: %s", exc)
        return []

    tiles: list[Tile] = []
    for item in components:
        text = item["text"]
        if _looks_like_a_control(text):
            continue

        tile = Tile(index=item["index"], kind="unknown", raw_text=text, box=item["box"])

        table = parse_table(text)
        if table is not None:
            tile.kind = "table"
            tile.table = table
            tile.title = f"country table ({table.device or 'device unknown'})"
            tiles.append(tile)
            continue

        label, value_text, delta_text = parse_scorecard(text)
        if label and value_text:
            tile.kind = "scorecard"
            tile.title = label
            tile.value_text = value_text
            tile.delta_text = delta_text
            tile.value, tile.abbreviated, reason = parse_number(value_text)
            tile.channel = _channel_of(label)
            if reason:
                tile.notes.append(reason)
            if tile.abbreviated:
                tile.notes.append(
                    f"value {value_text!r} is abbreviated by Looker; exact figure unavailable"
                )
            tiles.append(tile)
            continue

        tile.notes.append("neither a scorecard nor a country table")
        tiles.append(tile)

    _assign_table_channels(tiles)
    log.info(
        "Extracted %d component(s): %d scorecard(s), %d table(s)",
        len(tiles),
        sum(1 for t in tiles if t.kind == "scorecard"),
        sum(1 for t in tiles if t.kind == "table"),
    )
    return tiles


def pagination_texts(tiles: list[Tile]) -> list[str]:
    return [t.table.pagination_text for t in tiles if t.table and t.table.pagination_text]


PAGINATION_NOTE = "pagination footers are stored exactly as Looker renders them"
