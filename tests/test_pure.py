"""Tests for the parts that can be checked without a browser.

Run: .venv/bin/python tests/test_pure.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from looker_capture import dates, export, extract, selectors  # noqa: E402
from looker_capture.config import parse_cli_range, resolve_group  # noqa: E402

FAILURES: list[str] = []


def check(label: str, got, expected) -> None:
    if got != expected:
        FAILURES.append(f"{label}: expected {expected!r}, got {got!r}")


# --- CLI ranges ------------------------------------------------------------

period = parse_cli_range("current", "01/08/2026-23/08/2026")
check("cli range start", period.start, date(2026, 8, 1))
check("cli range end", period.end, date(2026, 8, 23))
check("period slug", period.slug, "2026-08-01_2026-08-23")

for bad in ("2026-08-01", "01/08/2026", "23/08/2026-01/08/2026"):
    try:
        parse_cli_range("current", bad)
        FAILURES.append(f"cli range {bad!r} should have been rejected")
    except ValueError:
        pass


# --- chip parsing ----------------------------------------------------------

CHIPS = [
    ("1 Aug 2026 - 23 Aug 2026", True),
    ("Aug 1, 2026 - Aug 23, 2026", True),
    ("01/08/2026 - 23/08/2026", True),
    ("2026-08-01 - 2026-08-23", True),
    ("1 ago 2026 - 23 ago 2026", True),
    ("Date range", False),
    ("1 Jan 2026 - 23 Jan 2026", False),
]
for text, expected in CHIPS:
    matched, note = dates.range_matches(text, date(2026, 8, 1), date(2026, 8, 23))
    check(f"chip {text!r}", matched, expected)

# A US-style chip must NOT silently pass as the day-first range we asked for.
matched, _ = dates.range_matches("08/01/2026 - 08/23/2026", date(2026, 8, 1), date(2026, 8, 23))
check("us-style chip matches via month-first fallback", matched, True)
matched, note = dates.range_matches("08/01/2026 - 08/23/2026", date(2026, 8, 1), date(2026, 8, 23))
check("ambiguity is flagged in the note", "ambiguous" in note, True)

# A chip that means January must fail when we asked for August.
matched, _ = dates.range_matches("8 Jan 2026 - 23 Jan 2026", date(2026, 8, 1), date(2026, 8, 23))
check("january chip rejected", matched, False)


# --- number parsing --------------------------------------------------------

NUMBERS = [
    ("1,234", 1234.0, False),
    ("1.234", 1234.0, False),
    ("30548", 30548.0, False),
    ("12.5%", 12.5, False),
    ("1,234.56", 1234.56, False),
    ("1.234,56", 1234.56, False),
    ("12.3K", 12300.0, True),
]
for text, expected_value, expected_abbrev in NUMBERS:
    value, abbrev, reason = extract.parse_number(text)
    check(f"number {text!r} value", value, expected_value)
    check(f"number {text!r} abbreviated", abbrev, expected_abbrev)

for text in ("", "United Kingdom", "-", "n/a"):
    value, _abbrev, reason = extract.parse_number(text)
    check(f"number {text!r} is unreadable", value, None)
    check(f"number {text!r} has a reason", bool(reason), True)


# --- pagination ------------------------------------------------------------

for text, expected_total in [
    ("1 - 100 / 155", 155),
    ("1-10 of 187", 187),
    ("1–10 de 187", 187),
    ("1 - 100 / 1,234", 1234),
]:
    verbatim, parsed = extract.parse_pagination(f"Country\nUK\n{text}")
    check(f"pagination {text!r} verbatim kept", verbatim is not None, True)
    check(f"pagination {text!r} total", parsed["total"], expected_total)

verbatim, parsed = extract.parse_pagination("no footer here")
check("missing pagination", (verbatim, parsed), (None, None))


# --- landing group chips ---------------------------------------------------

CHIP_CASES = [
    # Real applied-filters-bar text observed on the live report.
    ("Add filter Landing Page Group Home page (1)", "Home page", True),
    ("Add filter Landing Page Group Airport page (1)", "Airport page", True),
    ("Add filter Landing Page Group Route page (1)", "Route page", True),
    ("Add filter Landing Page Group Home page (1)", "Airport page", False),
    # Nothing filtered == the unfiltered/all-groups view.
    ("Add filter", "All landing pages", True),
    ("Add filter Landing Page Group Home page (1)", "All landing pages", False),
    # A named group with no count is not a confirmed isolation.
    ("Add filter Landing Page Group Home page", "Home page", False),
    # An empty read proves nothing, for either case.
    ("", "All landing pages", False),
    ("", "Home page", False),
    ("   ", "All landing pages", False),
    # Truncated chip still matches on the name prefix.
    ("Landing Page Group: Home pa... (1)", "Home page", True),
]
for chip, group, expected in CHIP_CASES:
    ok, note = selectors.verify_group_chip(chip, group)
    check(f"group chip {chip!r} vs {group!r}", ok, expected)


# --- checklist state helpers ----------------------------------------------
# The bug these guard against: "is the target group ticked?" is trivially true
# when every row starts ticked, so it reported success with no filter applied.

from looker_capture.selectors import _select_all_key, _ticked_groups  # noqa: E402

ALL_ON = {
    "Landing Page Group (Select all)": True,
    "Home page": True,
    "Airport page": True,
    "Route page": True,
    "(not set)": True,
}
ONLY_HOME = {
    "Landing Page Group (Select all)": False,
    "Home page": True,
    "Airport page": False,
    "Route page": False,
    "(not set)": False,
}
NONE_ON = dict.fromkeys(ALL_ON, False)

check("select-all row is identified", _select_all_key(ALL_ON), "Landing Page Group (Select all)")
check("select-all row excluded from ticked list", "Landing Page Group (Select all)" not in _ticked_groups(ALL_ON), True)
check("all ticked is not an isolated group", _ticked_groups(ALL_ON) == ["Home page"], False)
check("isolated home reads as exactly one group", _ticked_groups(ONLY_HOME), ["Home page"])
check("nothing ticked reads as empty", _ticked_groups(NONE_ON), [])
check("all-on lists every real group", len(_ticked_groups(ALL_ON)), 4)


# --- group aliases ---------------------------------------------------------

check("alias home", resolve_group("home"), "Home page")
check("alias Route Page", resolve_group("Route Page"), "Route page")
check("alias all", resolve_group("all"), "All landing pages")
try:
    resolve_group("nonsense")
    FAILURES.append("resolve_group should reject unknown groups")
except ValueError:
    pass


# --- country rows: never invent a zero -------------------------------------

# Rows are [country, device, value, % delta] as extract.py emits them. The
# metric is the VALUE column: reading the last column instead would file the
# % change as the session count.
rows = export._country_rows(
    {
        "rows": [
            ["United Kingdom", "desktop", "30,548", "-38.1%"],
            ["(not set)", "desktop", "12", "-"],
            ["Broken", "desktop", "—", "1.0%"],
            ["Total", "desktop", "99999", "0.0%"],
            ["Germany", "desktop", "19.154", "12.5%"],
        ]
    }
)
check("country rows keep readable values", rows[0], ("United Kingdom", 30548))
check("country rows keep (not set)", rows[1], ("(not set)", 12))
check("country rows drop unreadable", [r[0] for r in rows], ["United Kingdom", "(not set)", "Germany"])
check("country rows drop the total row", any(r[0] == "Total" for r in rows), False)
check(
    "country rows take the value column, not the trailing % delta",
    export._country_rows({"rows": [["Spain", "mobile", "1,916", "-41.7%"]]}),
    [("Spain", 1916)],
)
check(
    "a row without a value column is dropped rather than misread",
    export._country_rows({"rows": [["Spain", "mobile"]]}),
    [],
)


# --- scorecard attribution guards ------------------------------------------
# Each of these encodes a bug that silently produced WRONG numbers.

from looker_capture.config import PAGES as _PAGES  # noqa: E402


def _score(title, channel=None):
    return {"kind": "scorecard", "title": title, "raw_text": title, "channel": channel}


# 1. A channel tile naming no device is the channel total. The Searches page
#    labels its top tile "Searches - Paid Search traffic" with no "Total", and
#    treating that as unresolved left Paid Search and Organic empty.
ch, dev, why = export.classify(
    _score("Searches - Paid Search traffic", "Paid Search"),
    None,
    _PAGES["searches"].metric_pattern,
)
check("searches total tile resolves channel", ch, "Paid Search")
check("searches total tile defaults to Total", dev, "Total")

# 2. Mobile/Desktop must beat Total when both words are present.
ch, dev, _ = export.classify(
    _score("Mobile Total sessions - Paid", "Paid Search"), None,
    _PAGES["sessions"].metric_pattern,
)
check("mobile beats total", (ch, dev), ("Paid Search", "Mobile"))

# 3. A tile for a DIFFERENT metric on the same page must be refused. The Start
#    Search page carries "Desktop Submit Search - Org" beside the real
#    "Desktop Start Search - Org"; without this filter the impostor overwrote
#    the real value.
ss = _PAGES["start_search"].metric_pattern
ch, dev, why = export.classify(_score("Desktop Start Search - Org", "Organic"), None, ss)
check("the real Start Search tile is accepted", (ch, dev), ("Organic", "Desktop"))
ch, dev, why = export.classify(_score("Desktop Submit Search - Org", "Organic"), None, ss)
check("the Submit Search impostor is refused", ch, None)
check("refusal names the expected metric", "not this page's metric" in why, True)

# 4. The report's own typo must still map.
ch, dev, _ = export.classify(
    _score("Pruchase - Organic traffic", "Organic"), None,
    _PAGES["purchases"].metric_pattern,
)
check("the 'Pruchase' typo still maps", (ch, dev), ("Organic", "Total"))

# 5. A non-workbook channel is refused with a reason, never folded into one of
#    the three real channels.
ch, dev, why = export.classify(
    _score("Total sessions - Newsletter traffic", "Newsletter"), None,
    _PAGES["sessions"].metric_pattern,
)
check("newsletter is refused", ch, None)
check("newsletter refusal explains itself", "no column" in why, True)


# --- workbook emission -----------------------------------------------------

results = {
    "sessions": {
        "title": "Sessions",
        "periods": {
            "current": {
                "range": {"start": "2026-08-01", "end": "2026-08-23"},
                "groups": {
                    "Home page": {
                        "tiles": [
                            {
                                "index": 0,
                                "kind": "scorecard",
                                "title": "Mobile Total sessions - Paid",
                                "raw_text": "Mobile Total sessions - Paid 1,234",
                                "channel": "Paid Search",
                                "value": 1234,
                                "abbreviated": False,
                            },
                            {
                                "index": 1,
                                "kind": "scorecard",
                                "title": "Sessions",
                                "raw_text": "Sessions 9,999",
                                "value": 9999,
                                "abbreviated": False,
                            },
                            {
                                "index": 2,
                                "kind": "table",
                                "title": "country table (Desktop)",
                                "raw_text": "Country Device category Sessions % Δ 1. United Kingdom desktop 3,000 1.0% 1 - 10 / 155",
                                # A table's channel is resolved by extract.py
                                # from its position on the page, and its device
                                # from its own rows — neither is in the text.
                                "channel": "Organic",
                                "table": {
                                    "headers": ["Country", "Device category", "Value", "% Delta"],
                                    "rows": [["United Kingdom", "desktop", "3,000", "1.0%"]],
                                    "device": "Desktop",
                                    "pagination": {"first": 1, "last": 10, "total": 155},
                                    "pagination_text": "1 - 10 / 155",
                                },
                            },
                        ]
                    }
                },
            }
        },
    }
}

out = Path("/tmp/looker_capture_selftest")
import shutil  # noqa: E402

shutil.rmtree(out, ignore_errors=True)
unmapped = export.write_workbook_files(
    results, {"current": period}, out, "2026-08-26 10:00:00", "report-id"
)
emitted = (out / "data.py").read_text()

namespace: dict = {}
exec(compile(emitted, "data.py", "exec"), namespace)  # noqa: S102 - it is our own output

check("TOTALS mapped scorecard", namespace["TOTALS"]["Home page"]["Paid Search"]["Mobile"], 1234)
check(
    "TOTALS unknown cell is None, not 0",
    namespace["TOTALS"]["Home page"]["Organic"]["Total"],
    None,
)
check(
    "TOTALS keeps the full skeleton build.py indexes into",
    sorted(namespace["TOTALS"]),
    sorted(namespace["LANDING_GROUPS"]),
)
check(
    "COUNTRIES mapped table",
    namespace["COUNTRIES"][("Home page", "Organic", "Desktop")],
    [("United Kingdom", 3000)],
)
check(
    "FULL_ROW_COUNTS from the pagination footer",
    namespace["FULL_ROW_COUNTS"][("Home page", "Organic", "Desktop")],
    155,
)
check("unattributed tile reported", [u.tile_index for u in unmapped], [1])
check("UNMAPPED.md written", (out / "UNMAPPED.md").exists(), True)
check(
    "no fabricated zeros anywhere in TOTALS",
    any(
        v == 0
        for group in namespace["TOTALS"].values()
        for channel in group.values()
        for v in channel.values()
    ),
    False,
)

# An explicit layout map rescues the tile that could not be attributed.
shutil.rmtree(out, ignore_errors=True)
unmapped = export.write_workbook_files(
    results,
    {"current": period},
    out,
    "2026-08-26 10:00:00",
    "report-id",
    layout_map={"sessions": {"1": ["Direct", "Total"]}},
)
namespace = {}
exec(compile((out / "data.py").read_text(), "data.py", "exec"), namespace)  # noqa: S102
check("layout map applied", namespace["TOTALS"]["Home page"]["Direct"]["Total"], 9999)
shutil.rmtree(out, ignore_errors=True)


# --- report ----------------------------------------------------------------

if FAILURES:
    print(f"{len(FAILURES)} failure(s):")
    for line in FAILURES:
        print(f"  - {line}")
    sys.exit(1)
print("all pure-logic checks passed")


# --- merging a partial re-run ----------------------------------------------
# A one-hour run that dies near the end must not cost the combinations that
# already succeeded, and a failed re-capture must never blank a good result.

_existing = {"purchases": {"title": "P", "periods": {"current": {"groups": {
    "Home page": {"status": "ok", "tiles": [{"index": 0, "value": 100}]},
    "Route page": {"status": "failed", "tiles": []}}}}}}
_fresh = {"purchases": {"title": "P", "periods": {"current": {"groups": {
    "Home page": {"status": "failed", "tiles": []},
    "Route page": {"status": "ok", "tiles": [{"index": 0, "value": 55}]}}}}}}
_m = export.merge_results(_existing, _fresh)["purchases"]["periods"]["current"]["groups"]
check("a failed re-capture keeps the earlier ok result", _m["Home page"]["status"], "ok")
check("and keeps its value", _m["Home page"]["tiles"][0]["value"], 100)
check("a successful re-capture replaces a failure", _m["Route page"]["status"], "ok")
check("with the new value", _m["Route page"]["tiles"][0]["value"], 55)

_with_other = dict(_existing)
_with_other["sessions"] = {"title": "S", "periods": {"current": {"groups": {"Home page": {"status": "ok"}}}}}
check(
    "pages absent from the re-run survive untouched",
    sorted(export.merge_results(_with_other, _fresh)),
    ["purchases", "sessions"],
)
check("merging into nothing is a no-op passthrough", export.merge_results({}, _fresh), _fresh)
