"""Tests for period label formatting and the build.py handoff.

Run: .venv/bin/python tests/test_workbook.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from looker_capture import workbook  # noqa: E402
from looker_capture.config import parse_cli_range  # noqa: E402

FAILURES: list[str] = []


def check(label: str, got, expected) -> None:
    if got != expected:
        FAILURES.append(f"{label}: expected {expected!r}, got {got!r}")


same_month = parse_cli_range("current", "01/08/2026-23/08/2026")
check("same-month label", workbook.period_label(same_month), "1-23Aug26")
check("same-month full", workbook.period_full(same_month), "1-23 August 2026")

cross_month = parse_cli_range("current", "28/07/2026-03/08/2026")
check("cross-month label", workbook.period_label(cross_month), "28Jul-3Aug26")
check("cross-month full", workbook.period_full(cross_month), "28 July - 3 August 2026")

cross_year = parse_cli_range("current", "28/12/2025-03/01/2026")
check("cross-year label falls back to isoformat", workbook.period_label(cross_year), "2025-12-28_2026-01-03")

check("vendored build.py present", workbook._BUILD_SCRIPT.exists(), True)

single_day = parse_cli_range("current", "05/08/2026-05/08/2026")
check("single-day label", workbook.period_label(single_day), "5-5Aug26")

if FAILURES:
    print(f"{len(FAILURES)} failure(s):")
    for line in FAILURES:
        print(f"  - {line}")
    sys.exit(1)
print("all workbook checks passed")
