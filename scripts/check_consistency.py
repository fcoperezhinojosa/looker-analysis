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

  python scripts/check_consistency.py WORKBOOK.xlsx [--json RETRY.json]

--json writes the (page, period, landing group) combinations to re-capture,
as {"retry": [{"page": ..., "period": ..., "group": ...}]}, for the wrapper.
"""
import json
import re
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


def _group_slug(lg):
    first = str(lg).strip().lower().split()[0]
    return {"all": "all", "home": "home", "airport": "airport", "route": "route"}.get(first)


def _page_slug(metric):
    return str(metric).strip().lower().replace(" ", "_")


def _period_of(label, labels):
    """'current' for the latest year label seen in the workbook, else 'prior'."""
    def yr(x):
        m = re.search(r"(\d{2})$", str(x))
        return int(m.group(1)) if m else -1
    return "current" if yr(label) == max(yr(x) for x in labels) else "prior"


def retry_list(device_bad, country_bad, empty, year_labels):
    """Unique (page, period, group) combinations behind every flagged cell."""
    found = set()
    flagged = (
        [(lg, met, yr) for lg, _ch, met, yr, _t, _s in device_bad]
        + [(k[0], k[3], k[4]) for k, _t, _s in country_bad]
        + [(e[1], e[4], e[5]) for e in empty]
    )
    for lg, met, yr in flagged:
        g = _group_slug(lg)
        if g:
            found.add((_page_slug(met), _period_of(yr, year_labels), g))
    return [{"page": p, "period": per, "group": g} for p, per, g in sorted(found)]


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
    args = sys.argv[1:]
    json_out = None
    if "--json" in args:
        i = args.index("--json")
        if i + 1 >= len(args):
            sys.exit(__doc__)
        json_out = Path(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        sys.exit(__doc__)
    path = Path(args[0])
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
    for _sheet, lg, ch, dev, met, yr in empty[:30]:
        print(f"    {lg} / {ch} / {dev} / {met} [{yr}]")

    failed = bool(device_bad or country_bad or empty)
    if json_out:
        labels = {k[4] for k in totals}
        json_out.write_text(json.dumps(
            {"retry": retry_list(device_bad, country_bad, empty, labels)}, indent=2))
    print("\nRESULT:", "SUSPECT - re-capture the tiles named above" if failed else "CLEAN")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
