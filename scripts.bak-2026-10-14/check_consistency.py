"""Consistency gate for a capture workbook.

Two arithmetic identities must hold in any correct capture. Both have caught
real, silent errors that a plausible-looking xlsx hid completely:

  1. Mobile + Desktop <= Total, per landing group / channel / metric / year.
  2. The sum of the visible country rows <= Total, same keys. Looker only
     shows its top rows, so the sum can legitimately be lower - but never
     higher. A sum above the total means the tile was misread.

Also reports cells left empty, which is what a quota error looks like after
the fact: the workbook is still produced and still looks complete.

A prior-year figure that moves between two captures of the same period is
always a capture fault, since last year's data cannot change. That check
lives in compare_captures.py; this one needs only a single file.

  python scripts/check_consistency.py WORKBOOK.xlsx
"""
import sys
from pathlib import Path

import openpyxl

TOL = 1.02  # allow 2%: the workbook rounds, and tablet traffic sits outside M/D


def _columns(ws):
    """(metric, year-label) -> 1-based column, for the captured value columns."""
    row3 = [c.value for c in ws[3]]
    row4 = [c.value for c in ws[4]]
    metric, out = None, {}
    for i, (a, b) in enumerate(zip(row3, row4), 1):
        if a:
            metric = a
        if b and isinstance(b, str) and "Aug" not in str(b) and b in ("Δ", "% Δ"):
            continue
        if b and isinstance(b, str) and b not in ("Δ", "% Δ"):
            out.setdefault((metric, b), i)
    return out


def load(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    # Rates and deltas are formulas. openpyxl reports them as empty unless the
    # file has been opened in Excel, so counting them as missing data would
    # bury the cells that are genuinely absent under a few hundred false ones.
    formulas = openpyxl.load_workbook(path, data_only=False)
    totals, countries, empty = {}, {}, []
    ws = wb["Totals"]
    fws = formulas["Totals"]
    cols = _columns(ws)
    for row in ws.iter_rows(min_row=5):
        lg, ch, dev = (row[i].value for i in range(3))
        if not (lg and ch and dev):
            continue
        for key, i in cols.items():
            v = row[i - 1].value
            totals[(lg, ch, dev) + key] = v
            f = fws.cell(row=row[0].row, column=i).value
            is_formula = isinstance(f, str) and f.startswith("=")
            if v is None and not is_formula:
                empty.append(("Totals", lg, ch, dev) + key)
    ws = wb["Countries"]
    cols = _columns(ws)
    for row in ws.iter_rows(min_row=5):
        lg, ch, dev, co = (row[i].value for i in range(4))
        if not (lg and ch and dev and co):
            continue
        for key, i in cols.items():
            v = row[i - 1].value
            if isinstance(v, (int, float)):
                countries.setdefault((lg, ch, dev) + key, {})[co] = v
    return totals, countries, empty


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    totals, countries, empty = load(path)

    device_bad, country_bad = [], []

    for (lg, ch, dev, met, yr), v in totals.items():
        if dev != "Total" or not isinstance(v, (int, float)):
            continue
        mo = totals.get((lg, ch, "Mobile", met, yr))
        de = totals.get((lg, ch, "Desktop", met, yr))
        if isinstance(mo, (int, float)) and isinstance(de, (int, float)):
            if mo + de > v * TOL:
                device_bad.append((lg, ch, met, yr, v, mo + de))

    for key, rows in countries.items():
        tot = totals.get(key)
        if not isinstance(tot, (int, float)) or not rows:
            continue
        s = sum(rows.values())
        if s > tot * TOL:
            country_bad.append((key, tot, s))

    print(f"workbook: {path.name}\n")
    print(f"Mobile + Desktop <= Total : {len(device_bad)} violation(s)")
    for lg, ch, met, yr, tot, md in device_bad[:15]:
        print(f"    {lg} / {ch} / {met} [{yr}]: Total={tot:,} but M+D={md:,}")
    print(f"country sum <= Total      : {len(country_bad)} violation(s)")
    for key, tot, s in country_bad[:15]:
        lg, ch, dev, met, yr = key
        print(f"    {lg} / {ch} / {dev} / {met} [{yr}]: Total={tot:,} but countries={s:,}")
    print(f"empty captured cells      : {len(empty)}")
    by_metric = {}
    for e in empty:
        by_metric.setdefault((e[4], e[5]), 0)
        by_metric[(e[4], e[5])] += 1
    for (met, yr), n in sorted(by_metric.items(), key=lambda x: -x[1])[:10]:
        print(f"    {met} [{yr}]: {n} cell(s)")

    failed = bool(device_bad or country_bad or empty)
    print("\nRESULT:", "SUSPECT - re-capture the tiles named above" if failed else "CLEAN")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
