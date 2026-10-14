"""Static configuration: the report, its pages, and the label vocabulary.

Everything that could change when Looker Studio's report is edited lives here,
so page IDs and label spellings never have to be chased through the logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

REPORT_ID = "fb949fdd-dd2f-4cdb-95db-16d82bd003e9"

# Always /edit — the view-mode URLs render a page that looks loaded but is
# missing the data, because the underlying sources are editor-only.
URL_TEMPLATE = (
    "https://lookerstudio.google.com/u/{account}/reporting/{report}/page/{page}/edit"
)


@dataclass(frozen=True)
class ReportPage:
    slug: str
    page_id: str
    title: str
    # Stem of the data file the suntransfers-yoy-funnel workbook expects, or
    # None for pages that have no place in that workbook.
    workbook_stem: str | None = None
    # Which metric this page's scorecards must name to count. Pages carry tiles
    # for OTHER metrics too — the Start Search page shows both "Desktop Start
    # Search - Org" and "Desktop Submit Search - Org", and without this filter
    # the second silently overwrote the first with a different number.
    metric_pattern: re.Pattern[str] | None = None

    def url(self, account: int) -> str:
        return URL_TEMPLATE.format(account=account, report=REPORT_ID, page=self.page_id)


PAGES: dict[str, ReportPage] = {
    p.slug: p
    for p in (
        ReportPage(
            "sessions", "p_caonnz955d", "Sessions", "data",
            re.compile(r"\bsessions\b", re.I),
        ),
        ReportPage(
            "start_search", "p_kyj34z885d", "Start Search", "data_start_search",
            # "Start Search" only — NOT the "Submit Search" tiles beside it.
            re.compile(r"\bstart\s*search\b", re.I),
        ),
        ReportPage(
            "searches", "p_is11jf365d", "Searches", "data_search",
            # "Searches" (plural); "Start Search" does not match.
            re.compile(r"\bsearches\b", re.I),
        ),
        ReportPage(
            "purchases", "p_2e6ltn365d", "Purchases", "data_purchase",
            # The report itself carries a typo, "Pruchase - Organic traffic",
            # so both spellings have to be accepted.
            re.compile(r"\b(purchase|pruchase)", re.I),
        ),
        # Mid-funnel steps. Captured (screenshots + data.json) but the
        # suntransfers-yoy-funnel workbook has no columns for them — its VOL
        # list is Sessions / Start Search / Searches / Purchases only — so they
        # carry no workbook_stem and are deliberately absent from the .xlsx.
        ReportPage(
            "select_item", "p_fc1gb3sl6d", "Select item", "data_select_item",
            re.compile(r"\bselect\s*item\b", re.I),
        ),
        ReportPage(
            "add_to_cart", "p_oxemlbtl6d", "Add to cart", "data_add_to_cart",
            re.compile(r"\badd\s*to\s*cart\b", re.I),
        ),
        ReportPage(
            # The report writes it "Begin Checkout"; matching is case-insensitive.
            "begin_checkout", "p_e2hegntl6d", "Begin checkout", "data_begin_checkout",
            re.compile(r"\bbegin\s*checkout\b", re.I),
        ),
        ReportPage("kpis_by_route", "p_diw3ey7n6d", "KPIs by Route"),
        ReportPage("booking_funnel", "p_a75y6vgl3d", "Booking Funnel Detail"),
        ReportPage("horizontal", "p_oyk5likyjd", "Horizontal funnel"),
    )
}

DEFAULT_PAGES = list(PAGES)


# --------------------------------------------------------------------------
# Landing Page Group
# --------------------------------------------------------------------------
# Canonical names are the ones the workbook's data files use (see
# suntransfers-yoy-funnel/references/data-schema.md rule 5 — these four strings
# must not drift). ALL is the unfiltered view: every box in the control ticked.

ALL_GROUPS = "All landing pages"
LANDING_GROUPS = [ALL_GROUPS, "Home page", "Airport page", "Route page"]

# What to look for in the Looker checklist. The control's own spelling has been
# seen as both "Home page" and "Home Page"; matching is case-insensitive.
GROUP_ROW_PATTERNS: dict[str, re.Pattern[str]] = {
    "Home page": re.compile(r"^\s*home\s*page\s*$", re.I),
    "Airport page": re.compile(r"^\s*airport\s*page\s*$", re.I),
    "Route page": re.compile(r"^\s*route\s*page\s*$", re.I),
}

# CLI conveniences: --landing-groups home,route
GROUP_ALIASES = {
    "all": ALL_GROUPS,
    "all landing pages": ALL_GROUPS,
    "todas": ALL_GROUPS,
    "home": "Home page",
    "home page": "Home page",
    "airport": "Airport page",
    "airport page": "Airport page",
    "route": "Route page",
    "route page": "Route page",
}


def resolve_group(raw: str) -> str:
    key = raw.strip().lower()
    if key in GROUP_ALIASES:
        return GROUP_ALIASES[key]
    raise ValueError(
        f"Unknown landing page group {raw!r}. Known: {', '.join(sorted(set(GROUP_ALIASES.values())))}"
    )


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "unnamed"


# --------------------------------------------------------------------------
# Periods
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Period:
    name: str  # "current" | "prior"
    start: date
    end: date

    @property
    def slug(self) -> str:
        return f"{self.start.isoformat()}_{self.end.isoformat()}"

    def __str__(self) -> str:
        return f"{self.name} ({self.start.isoformat()}..{self.end.isoformat()})"


_CLI_RANGE_RE = re.compile(
    r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*[-–—]\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$"
)


def parse_cli_range(name: str, raw: str) -> Period:
    """Parse a dd/mm/yyyy-dd/mm/yyyy CLI argument."""
    m = _CLI_RANGE_RE.match(raw)
    if not m:
        raise ValueError(
            f"--{name}-range must look like 01/08/2026-23/08/2026, got {raw!r}"
        )
    d1, m1, y1, d2, m2, y2 = (int(x) for x in m.groups())
    start, end = date(y1, m1, d1), date(y2, m2, d2)
    if end < start:
        raise ValueError(f"--{name}-range ends before it starts: {raw!r}")
    return Period(name, start, end)


# --------------------------------------------------------------------------
# Scorecard / table attribution
# --------------------------------------------------------------------------
# Used by export.py to work out which (channel, device) a tile belongs to.
# Tuned after the first real run rather than guessed at once — anything that
# does not match confidently is reported as unmapped, never assigned a default.

# Real scorecard labels shorten the channel: the Total tile reads
# "Total sessions - Paid Search traffic" but its Mobile/Desktop siblings read
# "Mobile Total sessions - Paid" and "Desktop Total sessions - Org", so these
# patterns have to accept the short forms too.
CHANNEL_PATTERNS: dict[str, re.Pattern[str]] = {
    "Paid Search": re.compile(r"\bpaid(\s*search)?\b|\bcpc\b|\bsem\b", re.I),
    "Organic": re.compile(r"\borganic\b|\borg\b", re.I),
    "Direct": re.compile(r"\bdirect\b", re.I),
}

# Channels the report shows that the workbook has no column for. They are
# matched only so their scorecards can anchor their own country tables — without
# this, a Newsletter table falls to the nearest *workbook* channel and its
# country data silently lands under Direct.
NON_WORKBOOK_CHANNEL_PATTERNS: dict[str, re.Pattern[str]] = {
    "Newsletter": re.compile(r"\bnewsletter\b|\bemail\b", re.I),
    "Referral": re.compile(r"\breferral\b", re.I),
    "Social": re.compile(r"\bsocial\b", re.I),
}

# Every channel label that can anchor a table, workbook or not.
ANCHOR_CHANNEL_PATTERNS: dict[str, re.Pattern[str]] = {
    **CHANNEL_PATTERNS,
    **NON_WORKBOOK_CHANNEL_PATTERNS,
}

# Device is decided by PRECEDENCE, not by uniqueness: "Mobile Total sessions"
# contains both "Mobile" and "Total", and treating that as ambiguous left every
# per-device scorecard unattributed. Mobile/Desktop win over Total.
DEVICE_PRECEDENCE: list[tuple[str, re.Pattern[str]]] = [
    ("Mobile", re.compile(r"\bmobile\b|\bmóvil\b", re.I)),
    ("Desktop", re.compile(r"\bdesktop\b|\bescritorio\b", re.I)),
    ("Total", re.compile(r"\btotal\b|\ball\s*devices\b", re.I)),
]

DEVICE_PATTERNS: dict[str, re.Pattern[str]] = dict(DEVICE_PRECEDENCE)

CHANNELS = ["Paid Search", "Organic", "Direct"]
DEVICES = ["Total", "Mobile", "Desktop"]


# --------------------------------------------------------------------------
# Timing defaults
# --------------------------------------------------------------------------

DEFAULT_SETTLE_SECONDS = 35.0  # the fixed 30-40s wait after any control change
DEFAULT_PAUSE_SECONDS = 10.0  # between combinations, to stay under the quota
DEFAULT_QUOTA_RETRIES = 3
QUOTA_BACKOFF_SECONDS = [45.0, 90.0, 180.0]
CONTROL_ATTEMPTS = 3
CONTROL_BACKOFF_SECONDS = [2.0, 5.0, 10.0]
