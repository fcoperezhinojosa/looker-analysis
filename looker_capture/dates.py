"""Reading dates back out of Looker's own chips.

The date-range chip never echoes the format you typed — it renders in the
report's locale ("1 Aug 2026 - 23 Aug 2026", "Aug 1, 2026 - Aug 23, 2026",
"01/08/2026 - 23/08/2026"...). Verification therefore compares parsed dates,
never strings.
"""

from __future__ import annotations

import re
from datetime import date

_MONTHS = {}
for _i, _names in enumerate(
    [
        ("jan", "january", "ene", "enero"),
        ("feb", "february", "febrero"),
        ("mar", "march", "marzo"),
        ("apr", "april", "abr", "abril"),
        ("may", "mayo"),
        ("jun", "june", "junio"),
        ("jul", "july", "julio"),
        ("aug", "august", "ago", "agosto"),
        ("sep", "sept", "september", "sep", "septiembre", "set"),
        ("oct", "october", "octubre"),
        ("nov", "november", "noviembre"),
        ("dec", "december", "dic", "diciembre"),
    ],
    start=1,
):
    for _n in _names:
        _MONTHS[_n] = _i

_MONTH_WORD = r"[A-Za-zÁÉÍÓÚÜáéíóúü]{3,10}\.?"

# One date, in any of the shapes Looker has been seen to render.
DATE_TOKEN = (
    r"(?:"
    rf"\d{{1,2}}\s+(?:de\s+)?{_MONTH_WORD}\s+(?:de\s+)?\d{{4}}"  # 1 Aug 2026 / 1 de ago de 2026
    rf"|{_MONTH_WORD}\s+\d{{1,2}},?\s+\d{{4}}"  # Aug 1, 2026
    r"|\d{1,2}/\d{1,2}/\d{2,4}"  # 01/08/2026
    r"|\d{4}-\d{2}-\d{2}"  # 2026-08-01
    r"|\d{8}"  # 20260801
    r")"
)

DATE_RANGE_RE = re.compile(rf"{DATE_TOKEN}\s*[-–—]\s*{DATE_TOKEN}")
_TOKEN_RE = re.compile(DATE_TOKEN)


def _month_from_word(word: str) -> int | None:
    return _MONTHS.get(word.strip(". ").lower())


def parse_date_candidates(token: str) -> list[date]:
    """All the dates a single token could plausibly mean.

    Numeric dd/mm vs mm/dd is genuinely ambiguous, so both readings come back
    and the caller decides (and logs the ambiguity).
    """
    token = token.strip()
    out: list[date] = []

    m = re.fullmatch(rf"(\d{{1,2}})\s+(?:de\s+)?({_MONTH_WORD})\s+(?:de\s+)?(\d{{4}})", token)
    if m:
        month = _month_from_word(m.group(2))
        if month:
            out.append(date(int(m.group(3)), month, int(m.group(1))))
        return out

    m = re.fullmatch(rf"({_MONTH_WORD})\s+(\d{{1,2}}),?\s+(\d{{4}})", token)
    if m:
        month = _month_from_word(m.group(1))
        if month:
            out.append(date(int(m.group(3)), month, int(m.group(2))))
        return out

    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", token)
    if m:
        out.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        return out

    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", token)
    if m:
        try:
            out.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass
        return out

    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", token)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        for day, month in ((a, b), (b, a)):  # day-first, then month-first
            try:
                candidate = date(y, month, day)
            except ValueError:
                continue
            if candidate not in out:
                out.append(candidate)
    return out


def parse_range(text: str) -> tuple[list[date], list[date]] | None:
    """Pull the two ends of a range out of arbitrary chip text."""
    tokens = _TOKEN_RE.findall(text or "")
    if len(tokens) < 2:
        return None
    start = parse_date_candidates(tokens[0])
    end = parse_date_candidates(tokens[1])
    if not start or not end:
        return None
    return start, end


def range_matches(text: str, start: date, end: date) -> tuple[bool, str]:
    """Does this chip text mean the range we asked for?

    Returns (matched, note). The note flags an ambiguous numeric chip that only
    matched under the non-day-first reading, so the log records the doubt
    instead of hiding it.
    """
    parsed = parse_range(text)
    if parsed is None:
        return False, f"no date range found in chip text {text!r}"
    starts, ends = parsed
    if start not in starts or end not in ends:
        return False, (
            f"chip reads {text!r} -> {starts}..{ends}, expected "
            f"{start.isoformat()}..{end.isoformat()}"
        )
    ambiguous = (len(starts) > 1 and starts[0] != start) or (
        len(ends) > 1 and ends[0] != end
    )
    if ambiguous:
        return True, f"matched, but chip {text!r} is numerically ambiguous (month-first reading)"
    return True, "matched"


def format_candidates(day: date) -> list[str]:
    """The formats to try typing into Looker's custom date inputs, in order."""
    return [
        day.strftime("%d/%m/%Y"),
        day.strftime("%m/%d/%Y"),
        day.strftime("%Y-%m-%d"),
        day.strftime("%-d %b %Y"),
        day.strftime("%b %-d, %Y"),
        day.strftime("%Y%m%d"),
    ]


# --- Material calendar helpers ---------------------------------------------
# Looker's date control is an Angular Material dialog: two mat-calendar grids
# whose day cells are buttons labelled "1 Aug 2026", above a period button
# reading "AUG 2026". Dates are clicked, never typed — there is no text input.

MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def day_cell_label(day: date) -> str:
    """The aria-label Material gives a day cell, e.g. "1 Aug 2026"."""
    return f"{day.day} {MONTH_ABBR[day.month - 1]} {day.year}"


def parse_month_year(text: str) -> tuple[int, int] | None:
    """Read a calendar period button ("AUG 2026") as (year, month)."""
    match = re.search(rf"([A-Za-z]{{3,10}})\.?\s+(\d{{4}})", text or "")
    if not match:
        return None
    month = _month_from_word(match.group(1))
    if not month:
        return None
    return int(match.group(2)), month
