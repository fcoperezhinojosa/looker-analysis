import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (CUR_LABEL, LY_LABEL, CUR_FULL, LY_FULL,
                    CUR_REFRESHED, LY_REFRESHED, OUT, EXTRA_NOTES)
from data import *
from data_ly import TOTALS_LY, COUNTRIES_LY, FULL_ROW_COUNTS_LY
from data_start_search import (STARTSEARCH_TOTALS, STARTSEARCH_COUNTRIES,
                               FULL_ROW_COUNTS_STARTSEARCH)
from data_start_search_ly import (STARTSEARCH_TOTALS_LY, STARTSEARCH_COUNTRIES_LY,
                                  FULL_ROW_COUNTS_STARTSEARCH_LY)
from data_search import SEARCH_TOTALS, SEARCH_COUNTRIES, FULL_ROW_COUNTS_SEARCH
from data_search_ly import (SEARCH_TOTALS_LY, SEARCH_COUNTRIES_LY,
                            FULL_ROW_COUNTS_SEARCH_LY)
from data_purchase import PURCHASE_TOTALS, PURCHASE_COUNTRIES, FULL_ROW_COUNTS_PURCHASE
from data_purchase_ly import (PURCHASE_TOTALS_LY, PURCHASE_COUNTRIES_LY,
                              FULL_ROW_COUNTS_PURCHASE_LY)
from data_select_item import (SELECTITEM_TOTALS, SELECTITEM_COUNTRIES,
                              FULL_ROW_COUNTS_SELECTITEM)
from data_select_item_ly import (SELECTITEM_TOTALS_LY, SELECTITEM_COUNTRIES_LY,
                                 FULL_ROW_COUNTS_SELECTITEM_LY)
from data_add_to_cart import (ADDTOCART_TOTALS, ADDTOCART_COUNTRIES,
                              FULL_ROW_COUNTS_ADDTOCART)
from data_add_to_cart_ly import (ADDTOCART_TOTALS_LY, ADDTOCART_COUNTRIES_LY,
                                 FULL_ROW_COUNTS_ADDTOCART_LY)
from data_begin_checkout import (BEGINCHECKOUT_TOTALS, BEGINCHECKOUT_COUNTRIES,
                                 FULL_ROW_COUNTS_BEGINCHECKOUT)
from data_begin_checkout_ly import (BEGINCHECKOUT_TOTALS_LY, BEGINCHECKOUT_COUNTRIES_LY,
                                    FULL_ROW_COUNTS_BEGINCHECKOUT_LY)
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as gcl
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule

F = "Arial"
NAVY, MID, LIGHT, BAND, YELL = "1F3864", "2E5395", "D9E2F3", "F2F5FA", "FFF2CC"
TEAL, PLUM, MOSS, SLATE = "1F6F6F", "5B2C6F", "0F5132", "7F4F24"
GOOD, BADF = "E2F0D9", "FCE4E4"

BLUE_IN = Font(name=F, size=10, color="0000FF")
GREEN_LNK = Font(name=F, size=10, color="008000")
BLACK = Font(name=F, size=10)
BOLD = Font(name=F, size=10, bold=True)
WHITE_B = Font(name=F, size=10, bold=True, color="FFFFFF")
TITLE = Font(name=F, size=14, bold=True, color=NAVY)
SUB = Font(name=F, size=9, italic=True, color="595959")
SECT = Font(name=F, size=11, bold=True, color=NAVY)

NUM = '#,##0'
DELTA = '#,##0;[Red]-#,##0;-'
PCT = '0.0%;[Red]-0.0%;-'
RATE = '0.0%'
RATE2 = '0.00%'
PP = '0.00" pp";[Red]-0.00" pp";-'

thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
TOPLINE = Border(top=Side(style="medium", color=NAVY))

# ---------------------------------------------------------------------
# metric block definition — the whole workbook is generated from this.
# off = column offset from the block origin; volumes take 4 columns
# (current period, prior period, Δ, % Δ); rates take 3 (current, prior, Δ pp).
# ---------------------------------------------------------------------
GOLD = "B45309"
# Column order mirrors the funnel itself: Sessions -> Start Search (engagement
# with the search form) -> Visit->Engagement rate -> Searches -> Visit->Search
# rate -> Purchases -> Search->Booking rate -> CR.
# Funnel order, left to right, with each step's own conversion rate between
# the volumes it joins. Offsets are laid out in that order (see the skill's
# "Column order conventions"): every volume takes 4 columns (LY, CUR, Δ, %Δ)
# and every rate takes 3 (LY, CUR, Δ pp).
VOL = [
    {"name": "Sessions",       "off": 0,  "fill": NAVY},
    {"name": "Start Search",   "off": 4,  "fill": GOLD},
    {"name": "Searches",       "off": 11, "fill": MID},
    {"name": "Select item",    "off": 18, "fill": TEAL},
    {"name": "Add to cart",    "off": 25, "fill": MOSS},
    {"name": "Begin checkout", "off": 32, "fill": SLATE},
    {"name": "Purchases",      "off": 39, "fill": PLUM},
]
RATES = [
    {"name": "Visit→Engagement",  "off": 8,  "fill": "C2410C", "num": 4,  "den": 0,  "fmt": RATE},
    {"name": "Visit→Search",      "off": 15, "fill": TEAL,      "num": 11, "den": 0,  "fmt": RATE},
    {"name": "Search→Select",     "off": 22, "fill": "1F6F6F", "num": 18, "den": 11, "fmt": RATE},
    {"name": "Select→Cart",       "off": 29, "fill": "0F5132", "num": 25, "den": 18, "fmt": RATE},
    {"name": "Cart→Checkout",     "off": 36, "fill": "7F4F24", "num": 32, "den": 25, "fmt": RATE},
    {"name": "Checkout→Purchase", "off": 43, "fill": "5B2C6F", "num": 39, "den": 32, "fmt": RATE},
    {"name": "Search→Booking",    "off": 46, "fill": MOSS,      "num": 39, "den": 11, "fmt": RATE2},
    {"name": "CR",                 "off": 49, "fill": SLATE,     "num": 39, "den": 0,  "fmt": RATE2},
]
BLOCKS = sorted(VOL + RATES, key=lambda b: b["off"])
BW = 52  # total metric columns (7 volumes x4 + 8 rates x3)
# The Funnel tab keeps its own separate, smaller layout (Sessions/Searches/
# Purchases + their 3 rates only) — Start Search and Visit->Engagement are
# additive detail that lives on Totals/Countries/L1-L4/Market Summary.
FUNNEL_VOL = [b for b in VOL if b["name"] in ("Sessions", "Searches", "Purchases")]
OFF2NAME = {b["off"]: b["name"] for b in VOL}  # resolve a RATE's num/den offset to a VOL name

wb = Workbook()
ALL_LG = LANDING_GROUPS + ["Other pages (derived)"]
GAPS = []


def hdr(ws, row, labels, start_col=1, fill=NAVY):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=lab)
        c.font = WHITE_B
        c.fill = PatternFill("solid", fgColor=fill)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BOX
    ws.row_dimensions[row].height = 30


def title(ws, text, note=None):
    ws["A1"] = text
    ws["A1"].font = TITLE
    if note:
        ws["A2"] = note
        ws["A2"].font = SUB


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def block_header(ws, row, labels, s0, label_span=2):
    """Two-row header: block names on `row`, sub-labels on row+1."""
    for b in BLOCKS:
        c0 = s0 + b["off"]
        span = 3 if "num" in b else 4
        ws.merge_cells(start_row=row, start_column=c0, end_row=row, end_column=c0 + span - 1)
        c = ws.cell(row=row, column=c0, value=b["name"])
        c.font = WHITE_B
        c.alignment = Alignment(horizontal="center", vertical="center")
        for k in range(span):
            cc = ws.cell(row=row, column=c0 + k)
            cc.fill = PatternFill("solid", fgColor=b["fill"])
            cc.border = BOX
        subs = [LY_LABEL, CUR_LABEL, "Δ pp"] if span == 3 else [LY_LABEL, CUR_LABEL, "Δ", "% Δ"]
        for k, s in enumerate(subs):
            c = ws.cell(row=row + 1, column=c0 + k, value=s)
            c.font = WHITE_B
            c.fill = PatternFill("solid", fgColor=b["fill"])
            c.alignment = Alignment(horizontal="center")
            c.border = BOX
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=1 + i, value=lab)
        c.font = WHITE_B
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1 + i, end_row=row + 1, end_column=1 + i)
        ws.cell(row=row + 1, column=1 + i).fill = PatternFill("solid", fgColor=NAVY)
        c.border = BOX
        ws.cell(row=row + 1, column=1 + i).border = BOX
    ws.row_dimensions[row].height = 18


def block_row(ws, r, s0, pairs, bold=False, rate_override=None):
    """pairs: list of (cy_formula_or_value, ly_formula_or_value) in VOL order.
    On the sheet, column index 0 of each block holds the PRIOR period (LY) and
    index 1 holds the CURRENT period — read left-to-right as 'where we were'
    to 'where we are'. Δ / % Δ / Δ pp are still current-minus-prior."""
    fnt_v = Font(name=F, size=10, bold=bold, color="008000")
    fnt_b = Font(name=F, size=10, bold=bold)
    for b, (cy, ly) in zip(VOL, pairs):
        c0 = s0 + b["off"]
        lyL, cyL = gcl(c0), gcl(c0 + 1)
        is_formula = isinstance(cy, str) and cy.startswith("=")
        for k, val in ((0, ly), (1, cy)):
            c = ws.cell(row=r, column=c0 + k, value=val)
            c.number_format = NUM
            c.font = fnt_v if is_formula else Font(name=F, size=10, bold=bold, color="0000FF")
            if val is None:
                c.fill = PatternFill("solid", fgColor=YELL)
        g = f'OR({cyL}{r}="",{lyL}{r}="",{lyL}{r}=0,{cyL}{r}=0)'
        c = ws.cell(row=r, column=c0 + 2, value=f'=IF({g},"",{cyL}{r}-{lyL}{r})')
        c.number_format, c.font = DELTA, fnt_b
        c = ws.cell(row=r, column=c0 + 3, value=f'=IF({g},"",{cyL}{r}/{lyL}{r}-1)')
        c.number_format, c.font = PCT, fnt_b
    for b in RATES:
        c0 = s0 + b["off"]
        for k in range(2):
            if rate_override:
                f = rate_override(b, k, r)
            else:
                num, den = f"{gcl(s0 + b['num'] + k)}{r}", f"{gcl(s0 + b['den'] + k)}{r}"
                f = f'=IF(OR({num}="",{den}="",{den}=0),"",{num}/{den})'
            c = ws.cell(row=r, column=c0 + k, value=f)
            c.number_format, c.font = b["fmt"], fnt_b
        lyZ, cyA = gcl(c0), gcl(c0 + 1)
        c = ws.cell(row=r, column=c0 + 2,
                    value=f'=IF(OR({cyA}{r}="",{lyZ}{r}=""),"",({cyA}{r}-{lyZ}{r})*100)')
        c.number_format, c.font = PP, fnt_b
    for k in range(BW):
        ws.cell(row=r, column=s0 + k).border = BOX


def trend_rules(ws, first_row, last_row, s0):
    if last_row < first_row:   # nothing to format (e.g. an empty market list) - skip rather than crash
        return
    for b in BLOCKS:
        col = s0 + b["off"] + (2 if "num" in b else 3)
        rng = f"{gcl(col)}{first_row}:{gcl(col)}{last_row}"
        ws.conditional_formatting.add(rng, CellIsRule(
            operator="greaterThan", formula=["0"], fill=PatternFill("solid", bgColor=GOOD)))
        ws.conditional_formatting.add(rng, CellIsRule(
            operator="lessThan", formula=["0"], fill=PatternFill("solid", bgColor=BADF)))
        if "num" in b:   # a rate above 100% cannot be real - flag it loudly
            for k in range(2):
                rr = f"{gcl(s0 + b['off'] + k)}{first_row}:{gcl(s0 + b['off'] + k)}{last_row}"
                ws.conditional_formatting.add(rr, CellIsRule(
                    operator="greaterThan", formula=["1"],
                    fill=PatternFill("solid", bgColor="FF9999")))


def shade(ws, r, s0, colour=LIGHT, from_col=1):
    for col in range(from_col, s0 + BW):
        ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=colour)


def sumifs(tab, val_col, pairs):
    crit = ",".join(f"{tab(c)},{v}" for c, v in pairs)
    return f'SUMIFS({tab(val_col)},{crit})'


def bz(expr):
    return f'=IF({expr}=0,"",{expr})'


# =====================================================================
# README
# =====================================================================
ws = wb.active
ws.title = "README"
ws.sheet_view.showGridLines = False
widths(ws, {"A": 3, "B": 30, "C": 108})
ws["B2"] = f"Suntransfers — {CUR_FULL} vs {LY_FULL} traffic & conversion"
ws["B2"].font = Font(name=F, size=16, bold=True, color=NAVY)
ws["B3"] = "Sessions · Searches · Purchases · Start Search · Visit→Search · Search→Booking · CR — by channel → landing page group → device → market"
ws["B3"].font = Font(name=F, size=11, color="595959")

lines = [
    ("STATUS", ""),
    ("Loaded", "Complete on all seven volume inputs: Sessions, Start Search, Searches, Select item, Add to cart, Begin checkout and Purchases, both years. Every YoY and rate cell calculates at scorecard level."),
    ("Remaining", "Country-level blanks only, where a market sits outside a Looker table's visible rows. All listed on 'Gaps to fill'."),
    ("", ""),
    ("METRIC DEFINITIONS", ""),
    ("Sessions", "GA4 sessions, as reported by the Looker scorecards."),
    ("Searches", "The 'Searches' tile — sessions that reached a listing view. The SR / visit-to-search numerator, not start_search."),
    ("Purchases", "Completed bookings (the 'Purchases' tile)."),
    ("Start Search", "The start_search event — an engagement signal (the search form was actually used), tracked separately from 'Searches' (which is the view_item_list-based visit-to-search numerator). Shown as its own volume metric on Totals, Countries, L1-L4 and Market Summary so you can read engagement by channel / landing page / device / country; it does not feed Visit→Search, Search→Booking or CR, and is not on the Funnel tab."),
    ("Select item", "The select_item event — a listing result was opened. First step after the listing view."),
    ("Add to cart", "The add_to_cart event — a transfer was put in the basket."),
    ("Begin checkout", "The begin_checkout event — the checkout flow was entered."),
    ("Visit→Search", "Searches ÷ Sessions. How many arrivals get as far as a listing."),
    ("Search→Select", "Select item ÷ Searches. How many listing-viewers open a result."),
    ("Select→Cart", "Add to cart ÷ Select item. How many openers add to the basket."),
    ("Cart→Checkout", "Begin checkout ÷ Add to cart. How many baskets enter checkout."),
    ("Checkout→Purchase", "Purchases ÷ Begin checkout. How many checkouts complete. The step where payment friction shows up."),
    ("Search→Booking", "Purchases ÷ Searches. How many listing-viewers book. The S2B in the weekly readouts."),
    ("CR", "Purchases ÷ Sessions. The end-to-end conversion rate, and the product of the two rates above."),
    ("", ""),
    ("HOW IT IS BUILT", ""),
    ("Inputs", "Two tabs hold every number: 'Totals' (scorecard) and 'Countries' (country detail). Nothing else is typed."),
    ("Views", "L1 → L4 and 'Market Summary' are formulas only. Do not type in them."),
    ("Row / column logic", f"Dimensions go down the rows; metrics go across in blocks. Volumes take four columns ({CUR_LABEL}, {LY_LABEL}, Δ, % Δ), rates take three ({CUR_LABEL}, {LY_LABEL}, Δ pp). Adding a KPI is one more block, not a new tab."),
    ("To refresh a new month", "Overwrite the blue numbers on 'Totals' and 'Countries' (or regenerate them from new screenshots), update config.py's period labels, and rebuild."),
    ("", ""),
    ("CELL COLOUR LEGEND", ""),
    ("Blue text", "Hard-coded input read off the Looker screenshots. The only cells to overwrite when refreshing."),
    ("Black text", "Formula calculated within the same tab."),
    ("Green text", "Formula pulling from another tab (Totals or Countries)."),
    ("Yellow fill", "Fill this in. On the input tabs it is a missing number — see 'Gaps to fill'. On 'L4 Market view' it is a dropdown control."),
    ("", ""),
    ("TABS", ""),
    ("Funnel", "READ THIS FIRST. Sessions → Searches → Bookings and the three rates, for the total, each channel, each landing page group, each device, each market, each market within the Direct channel, and each market within each channel on Desktop only. One row per segment. (Start Search is not on this tab — see Countries, L1-L4 and Market Summary.)"),
    ("Totals", "INPUT. Scorecard: landing page group × channel × device, all four volume metrics (Sessions, Searches, Purchases, Start Search). 'Other pages (derived)' = All − Home − Airport − Route."),
    ("Countries", "INPUT. Country detail as shown in the Looker tables, including Start Search engagement sessions."),
    ("Gaps to fill", "Worklist of every yellow cell: which market, which metric, which period, the exact cell to type into, and what it unblocks."),
    ("L1 Channel YoY", "Level 1 — channel × device, all landing pages, plus channel mix."),
    ("L2 Channel x Landing", "Level 2 — landing page group × channel, device = Total."),
    ("L3 Ch x Landing x Device", "Level 3 — landing page group × channel × device."),
    ("L4 Market view", "Level 4 — country rows, with dropdowns for landing page group, channel and device."),
    ("Market Summary", "Country × channel across all landing pages: one stacked table per metric/rate (Sessions, Searches, Purchases, Start Search, Visit→Search, Search→Booking, CR)."),
    ("", ""),
    ("DATA SOURCE", ""),
    ("Report", f"Looker Studio sessions / searches / purchases views. {CUR_FULL} refreshed {CUR_REFRESHED}; {LY_FULL} refreshed {LY_REFRESHED}."),
    ("Periods", f"The full month of {CUR_FULL} vs the full month of {LY_FULL}. Channels: Paid Search, Organic, Direct. Other channels (affiliate, referral, email) are not in these views, which is why totals here sit below the all-traffic figures."),
    ("", ""),
    ("READ THESE BEFORE QUOTING A NUMBER", ""),
    ("Country coverage", "Only the visible top rows of each Looker table are captured (10 rows, 9 for Direct). The full tables run far deeper depending on the cut, so country rows do NOT sum to the scorecard. Every market tab prints its coverage %."),
    ("Missing-market blanks", "A blank cell means that market was not in that table's visible rows — it is NOT a zero. Δ, % Δ and every rate stay blank when an input is missing, so no false −100% appears."),
    ("Comparability flag", "Market rows are flagged 'Like-for-like' or 'Partial — coverage differs'. Partial means the market is visible in a different number of tables in each year, so its YoY % is distorted. Directional only, not a real percentage."),
    ("Matched coverage on rates", "Every country-level rate counts a channel/device only where BOTH numerator and denominator exist. Without it a market visible in one table but not another pushes the rate over 100%. Scorecard rates on L1/L2/L3 are unaffected."),
    ("Direct channel", "Direct's desktop searches have shown bursts of growth that outrun its sessions in past pulls, a signature of bot or scraper traffic rather than real customers. Check Direct desktop's Visit→Search rate against last period before treating its search→booking rate as a benchmark — see the 'By market x channel — Desktop only' section on the Funnel tab."),
    ("Device residual", "Mobile + Desktop does not equal Total; the difference is tablet and unassigned. The Total row is authoritative."),
    ("Landing page groups", "Home + Airport + Route do not cover all traffic. The remainder is 'Other pages (derived)'."),
    ("Derived-residual warning", "The three named landing groups do not attribute identically across the sessions, searches and purchases views, so the derived residual can be nonsense (an implausible search→booking rate, for example). Any rate cell shaded red is above 100% and cannot be real — read the named landing groups, not the residual, for rates."),
]
if EXTRA_NOTES:
    lines.append(("THIS PERIOD'S NOTES", ""))
    lines.extend(EXTRA_NOTES)

r = 5
legend_rows = {}
for k, v in lines:
    if v == "" and k:
        c = ws.cell(row=r, column=2, value=k)
        c.font = SECT
        c.border = TOPLINE
        ws.cell(row=r, column=3).border = TOPLINE
    elif k:
        ws.cell(row=r, column=2, value=k).font = BOLD
        c = ws.cell(row=r, column=3, value=v)
        c.font = BLACK
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 28 if len(v) > 112 else 14
        legend_rows[k] = r
    r += 1

for k, colr, fill in (("Blue text", "0000FF", None), ("Black text", "000000", None),
                      ("Green text", "008000", None), ("Yellow fill", "000000", YELL)):
    c = ws.cell(row=legend_rows[k], column=2)
    c.font = Font(name=F, size=10, bold=True, color=colr)
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)

# =====================================================================
# Totals (input)   labels A:C, metric origin = column 4 (D)
# =====================================================================
ws = wb.create_sheet("Totals")
ws.sheet_view.showGridLines = False
widths(ws, {"A": 23, "B": 13, "C": 10})
TS0 = 4
for col in range(TS0, TS0 + BW):
    ws.column_dimensions[gcl(col)].width = 11
title(ws, "Scorecard — INPUT",
      "Blue = hard-coded from Looker. 'Other pages (derived)' rows are formulas. Rates are calculated. Overwrite the blue cells to refresh for a new period.")
block_header(ws, 3, ["Landing Page Group", "Channel", "Device"], TS0)

T0 = 5
# ORDER MATTERS: block_row does zip(VOL, pairs), so this must follow VOL
# exactly or every metric lands in the wrong column block.
SRC = ((TOTALS, TOTALS_LY),
       (STARTSEARCH_TOTALS, STARTSEARCH_TOTALS_LY),
       (SEARCH_TOTALS, SEARCH_TOTALS_LY),
       (SELECTITEM_TOTALS, SELECTITEM_TOTALS_LY),
       (ADDTOCART_TOTALS, ADDTOCART_TOTALS_LY),
       (BEGINCHECKOUT_TOTALS, BEGINCHECKOUT_TOTALS_LY),
       (PURCHASE_TOTALS, PURCHASE_TOTALS_LY))
for i, lg in enumerate(ALL_LG):
    for j, ch in enumerate(CHANNELS):
        for k, dev in enumerate(DEVICES):
            r = T0 + i * 9 + j * 3 + k
            is_tot = (dev == "Total")
            lf = BOLD if is_tot else BLACK
            for ci, val in ((1, lg), (2, ch), (3, dev)):
                ws.cell(row=r, column=ci, value=val).font = lf
                ws.cell(row=r, column=ci).border = BOX
            if lg == "Other pages (derived)":
                pairs = []
                for b in VOL:
                    pr = {}
                    for k2 in range(2):
                        col = gcl(TS0 + b["off"] + k2)
                        pr[k2] = "={0}{1}-{0}{2}-{0}{3}-{0}{4}".format(
                            col, T0 + j * 3 + k, T0 + 9 + j * 3 + k,
                            T0 + 18 + j * 3 + k, T0 + 27 + j * 3 + k)
                    pairs.append((pr[1], pr[0]))  # (cy, ly): col0=LY, col1=CUR physically
            else:
                pairs = [(cy[lg][ch][dev], ly[lg][ch][dev]) for cy, ly in SRC]
            block_row(ws, r, TS0, pairs, bold=is_tot)
            if is_tot:
                shade(ws, r, TS0)
T_LAST = T0 + len(ALL_LG) * 9 - 1
ws.freeze_panes = "D5"
ws.auto_filter.ref = f"A4:{gcl(TS0 + BW - 1)}{T_LAST}"
ws.cell(row=T_LAST + 2, column=1,
        value=f"Source: Looker Studio scorecards. {CUR_FULL} refreshed {CUR_REFRESHED}; {LY_FULL} refreshed {LY_REFRESHED}.").font = SUB
ws.cell(row=T_LAST + 3, column=1,
        value="Mobile + Desktop ≠ Total — the residual is tablet / unassigned device. The Total row is authoritative.").font = SUB


def T(col):
    return f"Totals!${col}$5:${col}${T_LAST}"


TCOL = {b["name"]: (gcl(TS0 + b["off"]), gcl(TS0 + b["off"] + 1)) for b in VOL}

# =====================================================================
# Countries (input)   labels A:D, metric origin = column 5 (E)
# =====================================================================
ws = wb.create_sheet("Countries")
ws.sheet_view.showGridLines = False
CS0 = 5
CMP = CS0 + BW          # comparability column
widths(ws, {"A": 23, "B": 13, "C": 10, "D": 17, gcl(CMP): 26})
for col in range(CS0, CS0 + BW):
    ws.column_dimensions[gcl(col)].width = 11
title(ws, "Country detail — INPUT",
      "Visible rows of each Looker table only. A yellow cell is a market present in one table but not another — its value is off-screen, not zero. See 'Gaps to fill'.")
block_header(ws, 3, ["Landing Page Group", "Channel", "Device", "Country"], CS0)
c = ws.cell(row=3, column=CMP, value="Comparability (sessions)")
c.font = WHITE_B
c.fill = PatternFill("solid", fgColor=NAVY)
c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
c.border = BOX
ws.merge_cells(start_row=3, start_column=CMP, end_row=4, end_column=CMP)
ws.cell(row=4, column=CMP).fill = PatternFill("solid", fgColor=NAVY)
ws.cell(row=4, column=CMP).border = BOX

CSRC = [("Sessions", COUNTRIES, COUNTRIES_LY),
        ("Start Search", STARTSEARCH_COUNTRIES, STARTSEARCH_COUNTRIES_LY),
        ("Searches", SEARCH_COUNTRIES, SEARCH_COUNTRIES_LY),
        ("Select item", SELECTITEM_COUNTRIES, SELECTITEM_COUNTRIES_LY),
        ("Add to cart", ADDTOCART_COUNTRIES, ADDTOCART_COUNTRIES_LY),
        ("Begin checkout", BEGINCHECKOUT_COUNTRIES, BEGINCHECKOUT_COUNTRIES_LY),
        ("Purchases", PURCHASE_COUNTRIES, PURCHASE_COUNTRIES_LY)]
CCOL = {b["name"]: (gcl(CS0 + b["off"]), gcl(CS0 + b["off"] + 1)) for b in VOL}

r = 5
for lg in LANDING_GROUPS:
    for ch in CHANNELS:
        for dev in ("Mobile", "Desktop"):
            key = (lg, ch, dev)
            maps = {name: (dict(cy[key]), dict(ly[key])) for name, cy, ly in CSRC}
            order, seen = [], set()
            for name, cy, ly in CSRC:
                for src in (cy[key], ly[key]):
                    for c_, _ in src:
                        if c_ not in seen:
                            seen.add(c_)
                            order.append(c_)
            for idx, country in enumerate(order):
                for ci, val in ((1, lg), (2, ch), (3, dev), (4, country)):
                    ws.cell(row=r, column=ci, value=val).font = BLACK
                    ws.cell(row=r, column=ci).border = BOX
                pairs = [(maps[b["name"]][0].get(country), maps[b["name"]][1].get(country))
                         for b in VOL]
                block_row(ws, r, CS0, pairs)
                have = {}
                for b in VOL:
                    have[(b["name"], 0)] = maps[b["name"]][0].get(country)
                    have[(b["name"], 1)] = maps[b["name"]][1].get(country)
                biggest = max((v for v in have.values() if v), default=None)
                for b in VOL:
                    for k2, period in ((0, CUR_FULL), (1, LY_FULL)):
                        if have[(b["name"], k2)] is not None:
                            continue
                        unblocks = []
                        if have[(b["name"], 1 - k2)] is not None:
                            unblocks.append(f'{b["name"]} YoY')
                        for rb in RATES:
                            other = OFF2NAME[rb["den"]]
                            numname = OFF2NAME[rb["num"]]
                            if b["name"] in (other, numname):
                                partner = numname if b["name"] == other else other
                                if have[(partner, k2)] is not None:
                                    unblocks.append(f'{rb["name"]} {period}')
                        GAPS.append(("Countries", r,
                                     # sheet column 0 = LY, column 1 = current (see block_row) —
                                     # k2 here is the python-side (0=current,1=LY) convention.
                                     f'{CCOL[b["name"]][1 - k2]}{r}', lg, ch, dev, country,
                                     b["name"], period, biggest,
                                     " + ".join(sorted(set(unblocks))) or "Completeness only"))
                sl, sc = CCOL["Sessions"]  # column 0 = LY (sl), column 1 = current (sc)
                c = ws.cell(row=r, column=CMP,
                            value=f'=IF(AND({sc}{r}<>"",{sl}{r}<>""),"Both years",'
                                  f'IF({sc}{r}<>"","{CUR_LABEL} rows only","{LY_LABEL} rows only"))')
                c.font = BLACK
                c.border = BOX
                if idx % 2 == 1:
                    for col in range(1, 5):
                        ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=BAND)
                r += 1
C_LAST = r - 1
ws.freeze_panes = "E5"
ws.auto_filter.ref = f"A4:{gcl(CMP)}{C_LAST}"
ws.cell(row=C_LAST + 2, column=1,
        value="Source: Looker Studio country tables. Only the visible top rows are captured, so these do not sum to the scorecard totals.").font = SUB

cov_r = C_LAST + 4
ws.cell(row=cov_r - 1, column=1, value="Countries in the full Looker table, per cut (context for coverage)").font = SECT
_COV_METRICS = ["Sessions", "Start Search", "Searches", "Select item",
                "Add to cart", "Begin checkout", "Purchases"]
hdr(ws, cov_r,
    ["Landing Page Group", "Channel", "Device"]
    + [f"{m} {lab}" for m in _COV_METRICS for lab in (LY_LABEL, CUR_LABEL)],
    fill=MID)
rr = cov_r + 1
# Same order as _COV_METRICS, LY first then CUR within each metric.
COUNTS = [FULL_ROW_COUNTS_LY, FULL_ROW_COUNTS,
          FULL_ROW_COUNTS_STARTSEARCH_LY, FULL_ROW_COUNTS_STARTSEARCH,
          FULL_ROW_COUNTS_SEARCH_LY, FULL_ROW_COUNTS_SEARCH,
          FULL_ROW_COUNTS_SELECTITEM_LY, FULL_ROW_COUNTS_SELECTITEM,
          FULL_ROW_COUNTS_ADDTOCART_LY, FULL_ROW_COUNTS_ADDTOCART,
          FULL_ROW_COUNTS_BEGINCHECKOUT_LY, FULL_ROW_COUNTS_BEGINCHECKOUT,
          FULL_ROW_COUNTS_PURCHASE_LY, FULL_ROW_COUNTS_PURCHASE]
for lg in LANDING_GROUPS:
    for ch in CHANNELS:
        for dev in ("Mobile", "Desktop"):
            for ci, val in ((1, lg), (2, ch), (3, dev)):
                ws.cell(row=rr, column=ci, value=val).font = BLACK
            for k2, d in enumerate(COUNTS):
                ws.cell(row=rr, column=4 + k2, value=d.get((lg, ch, dev))).font = BLUE_IN
            for col in range(1, 4 + len(COUNTS)):
                ws.cell(row=rr, column=col).border = BOX
            rr += 1


def K(col):
    return f"Countries!${col}$5:${col}${C_LAST}"


# =====================================================================
# L1 Channel YoY
# =====================================================================
S0 = 3
ws = wb.create_sheet("L1 Channel YoY")
ws.sheet_view.showGridLines = False
widths(ws, {"A": 20, "B": 11})
for col in range(S0, S0 + BW):
    ws.column_dimensions[gcl(col)].width = 11
title(ws, "Level 1 — Channel YoY",
      "All landing pages. Visit→Search × Search→Booking = CR. Source: Totals tab.")
block_header(ws, 4, ["Channel", "Device"], S0)

r = 6
L1_ROWS = {}
for ch in CHANNELS:
    for dev in DEVICES:
        is_tot = (dev == "Total")
        ws.cell(row=r, column=1, value=ch).font = BOLD if is_tot else BLACK
        ws.cell(row=r, column=2, value=dev).font = BOLD if is_tot else BLACK
        ws.cell(row=r, column=1).border = BOX
        ws.cell(row=r, column=2).border = BOX
        base = [("A", '"All landing pages"'), ("B", f'"{ch}"'), ("C", f'"{dev}"')]
        block_row(ws, r, S0,
                  [("=" + sumifs(T, TCOL[b["name"]][1], base),
                    "=" + sumifs(T, TCOL[b["name"]][0], base)) for b in VOL],
                  bold=is_tot)
        if is_tot:
            shade(ws, r, S0)
        L1_ROWS[(ch, dev)] = r
        r += 1
for dev in DEVICES:
    ws.cell(row=r, column=1, value="Total (3 channels)").font = BOLD
    ws.cell(row=r, column=2, value=dev).font = BOLD
    ws.cell(row=r, column=1).border = BOX
    ws.cell(row=r, column=2).border = BOX
    srcs = [L1_ROWS[(ch, dev)] for ch in CHANNELS]
    block_row(ws, r, S0,
              [tuple("=SUM({})".format(",".join(f"{gcl(S0 + b['off'] + k2)}{x}" for x in srcs))
                     for k2 in (1, 0)) for b in VOL],
              bold=True)
    shade(ws, r, S0)
    if dev == "Total":
        GRAND = r
    r += 1
L1_END = r - 1
trend_rules(ws, 6, L1_END, S0)

MX = L1_END + 3
ws.cell(row=MX - 1, column=1, value="Channel mix (share of the three channels, device = Total)").font = SECT
hdr(ws, MX, ["Channel", "", f"Sessions {LY_LABEL}", f"Sessions {CUR_LABEL}", "Δ pp",
             f"Purchases {LY_LABEL}", f"Purchases {CUR_LABEL}", "Δ pp"], fill=MID)
for i, ch in enumerate(CHANNELS):
    rr = MX + 1 + i
    src = L1_ROWS[(ch, "Total")]
    ws.cell(row=rr, column=1, value=ch).font = BLACK
    ws.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=2)
    for j, b in enumerate(("Sessions", "Purchases")):
        off = next(x["off"] for x in VOL if x["name"] == b)
        base_col = 3 + j * 3
        for k2 in range(2):
            cl = gcl(S0 + off + k2)
            c = ws.cell(row=rr, column=base_col + k2, value=f'=IFERROR({cl}{src}/{cl}{GRAND},"")')
            c.number_format, c.font = RATE, BLACK
        lyCol, cyCol = gcl(base_col), gcl(base_col + 1)
        c = ws.cell(row=rr, column=base_col + 2,
                    value=f'=IF(OR({lyCol}{rr}="",{cyCol}{rr}=""),"",({cyCol}{rr}-{lyCol}{rr})*100)')
        c.number_format, c.font = PP, BLACK
    for col in range(1, 9):
        ws.cell(row=rr, column=col).border = BOX
ws.freeze_panes = "C6"

# =====================================================================
# L2 Channel x Landing
# =====================================================================
ws = wb.create_sheet("L2 Channel x Landing")
ws.sheet_view.showGridLines = False
widths(ws, {"A": 23, "B": 13})
for col in range(S0, S0 + BW):
    ws.column_dimensions[gcl(col)].width = 11
title(ws, "Level 2 — Channel × landing page group",
      "Device = Total. 'Other pages' is the derived remainder (All − Home − Airport − Route). Source: Totals tab.")
block_header(ws, 4, ["Landing Page Group", "Channel"], S0)
r = 6
for lg in ALL_LG:
    for ch in CHANNELS:
        is_all = (lg == "All landing pages")
        ws.cell(row=r, column=1, value=lg).font = BOLD if is_all else BLACK
        ws.cell(row=r, column=2, value=ch).font = BOLD if is_all else BLACK
        ws.cell(row=r, column=1).border = BOX
        ws.cell(row=r, column=2).border = BOX
        base = [("A", f'"{lg}"'), ("B", f'"{ch}"'), ("C", '"Total"')]
        block_row(ws, r, S0,
                  [("=" + sumifs(T, TCOL[b["name"]][1], base),
                    "=" + sumifs(T, TCOL[b["name"]][0], base)) for b in VOL],
                  bold=is_all)
        if is_all:
            shade(ws, r, S0)
        r += 1
L2_END = r - 1
trend_rules(ws, 6, L2_END, S0)
ws.freeze_panes = "C6"
ws.cell(row=L2_END + 2, column=1,
        value="Watch the 'Other pages (derived)' rows: the three named landing groups do not attribute identically across the three metric views, so the residual can produce a rate above 100% (Direct reads 211 bookings from 83 searches). Any rate cell shaded red is implausible and should not be quoted.").font = SUB

# =====================================================================
# L3 Channel x Landing x Device
# =====================================================================
S3 = 4
ws = wb.create_sheet("L3 Ch x Landing x Device")
ws.sheet_view.showGridLines = False
widths(ws, {"A": 23, "B": 13, "C": 10})
for col in range(S3, S3 + BW):
    ws.column_dimensions[gcl(col)].width = 11
title(ws, "Level 3 — Channel × landing page group × device",
      "Mobile + Desktop < Total by the tablet / unassigned residual. Source: Totals tab.")
block_header(ws, 4, ["Landing Page Group", "Channel", "Device"], S3)
r = 6
for lg in ALL_LG:
    for ch in CHANNELS:
        for dev in DEVICES:
            is_tot = (dev == "Total")
            for ci, val in ((1, lg), (2, ch), (3, dev)):
                c = ws.cell(row=r, column=ci, value=val)
                c.font = BOLD if is_tot else BLACK
                c.border = BOX
            base = [("A", f'"{lg}"'), ("B", f'"{ch}"'), ("C", f'"{dev}"')]
            block_row(ws, r, S3,
                      [("=" + sumifs(T, TCOL[b["name"]][1], base),
                        "=" + sumifs(T, TCOL[b["name"]][0], base)) for b in VOL],
                      bold=is_tot)
            if is_tot:
                shade(ws, r, S3)
            r += 1
L3_END = r - 1
trend_rules(ws, 6, L3_END, S3)
ws.freeze_panes = "D6"

# =====================================================================
# L4 Market view
# =====================================================================
def safe_sum(col, first, last):
    """SUM over a market/country range that might be empty (a channel or market
    cut with zero visible Looker rows this period) — an inverted range like
    SUM(C10:C9) is a #VALUE! error in LibreOffice, so fall back to a literal 0."""
    if last < first:
        return "=0"
    return f'=SUM({gcl(col)}{first}:{gcl(col)}{last})'


def build_country_list():
    weight, seen = {}, set()
    for key, rows in COUNTRIES.items():
        for c_, s in rows:
            if key[0] == "All landing pages":
                weight[c_] = weight.get(c_, 0) + s
    for src in (COUNTRIES, COUNTRIES_LY, SEARCH_COUNTRIES, SEARCH_COUNTRIES_LY,
                PURCHASE_COUNTRIES, PURCHASE_COUNTRIES_LY,
                STARTSEARCH_COUNTRIES, STARTSEARCH_COUNTRIES_LY):
        for key, rows in src.items():
            for c_, _ in rows:
                seen.add(c_)
    for c_ in seen:
        weight.setdefault(c_, 0)
    return sorted(weight, key=lambda c_: (-weight[c_], c_))


COUNTRY_LIST = build_country_list()

S4 = 2
L4CMP = S4 + BW
ws = wb.create_sheet("L4 Market view")
ws.sheet_view.showGridLines = False
widths(ws, {"A": 22, gcl(L4CMP): 28})
for col in range(S4, S4 + BW):
    ws.column_dimensions[gcl(col)].width = 11
title(ws, "Level 4 — Market YoY by channel, landing page group and device",
      "Pick the three dropdowns. Country rows are the Looker visible rows only — see the coverage line at the bottom.")
for i, (lab, val, opts) in enumerate((
        ("Landing page group:", "All landing pages", LANDING_GROUPS),
        ("Channel:", "Paid Search", CHANNELS),
        ("Device:", "Total", ["Total", "Mobile", "Desktop"]))):
    rr = 4 + i
    ws.cell(row=rr, column=1, value=lab).font = BOLD
    c = ws.cell(row=rr, column=2, value=val)
    c.font = Font(name=F, size=10, bold=True)
    c.fill = PatternFill("solid", fgColor=YELL)
    c.border = BOX
    dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(c)

H4 = 7
block_header(ws, H4, ["Country"], S4)
c = ws.cell(row=H4, column=L4CMP, value="Comparability (sessions)")
c.font = WHITE_B
c.fill = PatternFill("solid", fgColor=MID)
c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
c.border = BOX
ws.merge_cells(start_row=H4, start_column=L4CMP, end_row=H4 + 1, end_column=L4CMP)
ws.cell(row=H4 + 1, column=L4CMP).fill = PatternFill("solid", fgColor=MID)
ws.cell(row=H4 + 1, column=L4CMP).border = BOX
r0 = H4 + 2

CKEY = {b["name"]: (CCOL[b["name"]][0], CCOL[b["name"]][1]) for b in VOL}
OFF2NAME = {b["off"]: b["name"] for b in VOL}


def dev_switch(col, r, extra=None):
    crit = [("A", "$B$4"), ("B", "$B$5"), ("D", f"$A{r}")]
    if extra:
        crit.append(extra)
    crit_d = crit[:2] + [("C", "$B$6")] + crit[2:]
    a = sumifs(K, col, crit)
    b = sumifs(K, col, crit_d)
    return f'IF($B$6="Total",{a},{b})'


for i, country in enumerate(COUNTRY_LIST):
    r = r0 + i
    ws.cell(row=r, column=1, value=country).font = BLACK
    ws.cell(row=r, column=1).border = BOX

    def rate_override(b, k2, rr, _r=r):
        ncol = CKEY[OFF2NAME[b["num"]]][k2]
        dcol = CKEY[OFF2NAME[b["den"]]][k2]
        num = dev_switch(ncol, _r, (dcol, '">0"'))
        den = dev_switch(dcol, _r, (ncol, '">0"'))
        return f'=IF({den}=0,"",{num}/{den})'

    block_row(ws, r, S4,
              [tuple(bz(dev_switch(CKEY[b["name"]][k2], r)) for k2 in (1, 0)) for b in VOL],
              rate_override=rate_override)
    cnt = {}
    for tag, k2 in (("cy", 1), ("ly", 0)):
        col = CKEY["Sessions"][k2]
        a = f'COUNTIFS({K("A")},$B$4,{K("B")},$B$5,{K("D")},$A{r},{K(col)},">0")'
        b_ = f'COUNTIFS({K("A")},$B$4,{K("B")},$B$5,{K("C")},$B$6,{K("D")},$A{r},{K(col)},">0")'
        cnt[tag] = f'IF($B$6="Total",{a},{b_})'
    c = ws.cell(row=r, column=L4CMP,
                value=f'=IF(AND({cnt["cy"]}=0,{cnt["ly"]}=0),"",'
                      f'IF({cnt["cy"]}=0,"{LY_LABEL} rows only",'
                      f'IF({cnt["ly"]}=0,"{CUR_LABEL} rows only",'
                      f'IF({cnt["cy"]}={cnt["ly"]},"Like-for-like","Partial — coverage differs"))))')
    c.font = BLACK
    c.border = BOX
    if i % 2 == 1:
        ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=BAND)
L4_END = r0 + len(COUNTRY_LIST) - 1
trend_rules(ws, r0, L4_END, S4)
if L4_END >= r0:
    ws.conditional_formatting.add(f"{gcl(L4CMP)}{r0}:{gcl(L4CMP)}{L4_END}", CellIsRule(
        operator="equal", formula=['"Partial — coverage differs"'],
        fill=PatternFill("solid", bgColor=YELL)))

SUM_R, SCO_R, COV_R = L4_END + 1, L4_END + 2, L4_END + 3
ws.cell(row=SUM_R, column=1, value="Sum of listed countries").font = BOLD
ws.cell(row=SCO_R, column=1, value="Scorecard total (Totals tab)").font = BOLD
ws.cell(row=COV_R, column=1, value="Coverage of listed countries").font = BOLD


def sum_rate(b, k2, rr):
    ncol = CKEY[OFF2NAME[b["num"]]][k2]
    dcol = CKEY[OFF2NAME[b["den"]]][k2]
    num = dev_switch(ncol, "$A", (dcol, '">0"')).replace('{"$A"}', "")
    return None


def matched_total(b, k2):
    ncol = CKEY[OFF2NAME[b["num"]]][k2]
    dcol = CKEY[OFF2NAME[b["den"]]][k2]

    def side(val_col, filt_col):
        crit = [("A", "$B$4"), ("B", "$B$5"), (filt_col, '">0"')]
        crit_d = crit[:2] + [("C", "$B$6")] + crit[2:]
        return f'IF($B$6="Total",{sumifs(K, val_col, crit)},{sumifs(K, val_col, crit_d)})'
    return f'=IF({side(dcol, ncol)}=0,"",{side(ncol, dcol)}/{side(dcol, ncol)})'


block_row(ws, SUM_R, S4,
          [tuple(safe_sum(S4 + b["off"] + k2, r0, L4_END)
                 for k2 in (1, 0)) for b in VOL],
          bold=True, rate_override=lambda b, k2, rr: matched_total(b, k2))
sco_base = [("A", "$B$4"), ("B", "$B$5"), ("C", "$B$6")]
block_row(ws, SCO_R, S4,
          [("=" + sumifs(T, TCOL[b["name"]][1], sco_base),
            "=" + sumifs(T, TCOL[b["name"]][0], sco_base)) for b in VOL],
          bold=True)
for b in VOL:
    for k2 in range(2):
        cl = gcl(S4 + b["off"] + k2)
        c = ws.cell(row=COV_R, column=S4 + b["off"] + k2,
                    value=f'=IFERROR({cl}{SUM_R}/{cl}{SCO_R},"")')
        c.number_format, c.font = RATE, BOLD
for rr in (SUM_R, SCO_R, COV_R):
    for col in range(1, S4 + BW + 1):
        ws.cell(row=rr, column=col).fill = PatternFill("solid", fgColor=LIGHT)
        ws.cell(row=rr, column=col).border = BOX
ws.freeze_panes = "B9"
ws.cell(row=COV_R + 2, column=1,
        value="A blank cell means that market was not in the Looker visible rows for the selected cut — it is not a zero.").font = SUB
ws.cell(row=COV_R + 3, column=1,
        value="Rates use matched coverage: a channel/device counts only where both numerator and denominator exist.").font = SUB

# =====================================================================
# Market Summary — one stacked channel matrix per metric
# =====================================================================
ws = wb.create_sheet("Market Summary")
ws.sheet_view.showGridLines = False
widths(ws, {"A": 20})
for col in range(2, 18):
    ws.column_dimensions[gcl(col)].width = 11
title(ws, "Market summary — all landing pages, Mobile + Desktop",
      "Country × channel, one table per metric. Visible-rows coverage only; rates use matched coverage. Source: Countries tab.")
CH_GROUPS = [("Paid Search", 2), ("Organic", 6), ("Direct", 10), ("Total", 14)]


def channel_header(ws, row, subs, fill):
    for name, c0 in CH_GROUPS:
        ws.merge_cells(start_row=row, start_column=c0, end_row=row, end_column=c0 + 3)
        c = ws.cell(row=row, column=c0, value=name)
        c.font = WHITE_B
        c.alignment = Alignment(horizontal="center")
        for k in range(4):
            cc = ws.cell(row=row, column=c0 + k)
            cc.fill = PatternFill("solid", fgColor=fill if name != "Total" else MID)
            cc.border = BOX
        for k, s in enumerate(subs):
            c = ws.cell(row=row + 1, column=c0 + k, value=s)
            c.font = WHITE_B
            c.fill = PatternFill("solid", fgColor=MID)
            c.alignment = Alignment(horizontal="center")
            c.border = BOX
    c = ws.cell(row=row, column=1, value="Country")
    c.font = WHITE_B
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.border = BOX
    ws.merge_cells(start_row=row, start_column=1, end_row=row + 1, end_column=1)
    ws.cell(row=row + 1, column=1).fill = PatternFill("solid", fgColor=NAVY)
    ws.cell(row=row + 1, column=1).border = BOX


def volume_table(ws, start, b):
    ws.cell(row=start - 1, column=1, value=b["name"]).font = SECT
    channel_header(ws, start, [LY_LABEL, CUR_LABEL, "Δ", "% Δ"], b["fill"])
    first = start + 2
    ly_col, cy_col = CCOL[b["name"]]
    for i, country in enumerate(COUNTRY_LIST):
        r = first + i
        ws.cell(row=r, column=1, value=country).font = BLACK
        ws.cell(row=r, column=1).border = BOX
        for name, c0 in CH_GROUPS:
            lyL, cyL = gcl(c0), gcl(c0 + 1)
            if name == "Total":
                ly = bz("SUM({})".format(",".join(f"{gcl(c)}{r}" for _, c in CH_GROUPS[:3])))
                cy = bz("SUM({})".format(",".join(f"{gcl(c + 1)}{r}" for _, c in CH_GROUPS[:3])))
            else:
                base = [("A", '"All landing pages"'), ("B", f'"{name}"'), ("D", f"$A{r}")]
                ly = bz(sumifs(K, ly_col, base))
                cy = bz(sumifs(K, cy_col, base))
            for k, val in ((0, ly), (1, cy)):
                c = ws.cell(row=r, column=c0 + k, value=val)
                c.number_format, c.font = NUM, GREEN_LNK
            g = f'OR({cyL}{r}="",{lyL}{r}="",{lyL}{r}=0,{cyL}{r}=0)'
            c = ws.cell(row=r, column=c0 + 2, value=f'=IF({g},"",{cyL}{r}-{lyL}{r})')
            c.number_format, c.font = DELTA, BLACK
            c = ws.cell(row=r, column=c0 + 3, value=f'=IF({g},"",{cyL}{r}/{lyL}{r}-1)')
            c.number_format, c.font = PCT, BLACK
            for k in range(4):
                ws.cell(row=r, column=c0 + k).border = BOX
        if i % 2 == 1:
            ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=BAND)
    last = first + len(COUNTRY_LIST) - 1
    if last >= first:
        for _, c0 in CH_GROUPS:
            rng = f"{gcl(c0 + 3)}{first}:{gcl(c0 + 3)}{last}"
            ws.conditional_formatting.add(rng, CellIsRule(
                operator="lessThan", formula=["0"], fill=PatternFill("solid", bgColor=BADF)))
            ws.conditional_formatting.add(rng, CellIsRule(
                operator="greaterThan", formula=["0"], fill=PatternFill("solid", bgColor=GOOD)))
    return last


def rate_table(ws, start, b):
    ws.cell(row=start - 1, column=1, value=b["name"]).font = SECT
    channel_header(ws, start, [LY_LABEL, CUR_LABEL, "Δ pp", ""], b["fill"])
    first = start + 2
    ncols = CCOL[OFF2NAME[b["num"]]]
    dcols = CCOL[OFF2NAME[b["den"]]]
    for i, country in enumerate(COUNTRY_LIST):
        r = first + i
        ws.cell(row=r, column=1, value=country).font = BLACK
        ws.cell(row=r, column=1).border = BOX
        for name, c0 in CH_GROUPS:
            crit = [("A", '"All landing pages"'), ("D", f"$A{r}")]
            if name != "Total":
                crit.insert(1, ("B", f'"{name}"'))
            for k in range(2):
                num = sumifs(K, ncols[k], crit + [(dcols[k], '">0"')])
                den = sumifs(K, dcols[k], crit + [(ncols[k], '">0"')])
                c = ws.cell(row=r, column=c0 + k, value=f'=IF({den}=0,"",{num}/{den})')
                c.number_format, c.font = b["fmt"], BLACK
            lyC, cyC = gcl(c0), gcl(c0 + 1)
            c = ws.cell(row=r, column=c0 + 2,
                        value=f'=IF(OR({lyC}{r}="",{cyC}{r}=""),"",({cyC}{r}-{lyC}{r})*100)')
            c.number_format, c.font = PP, BLACK
            for k in range(4):
                ws.cell(row=r, column=c0 + k).border = BOX
        if i % 2 == 1:
            ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=BAND)
    last = first + len(COUNTRY_LIST) - 1
    if last >= first:
        for _, c0 in CH_GROUPS:
            rng = f"{gcl(c0 + 2)}{first}:{gcl(c0 + 2)}{last}"
            ws.conditional_formatting.add(rng, CellIsRule(
                operator="lessThan", formula=["0"], fill=PatternFill("solid", bgColor=BADF)))
            ws.conditional_formatting.add(rng, CellIsRule(
                operator="greaterThan", formula=["0"], fill=PatternFill("solid", bgColor=GOOD)))
    return last


pos = 5
for b in BLOCKS:
    pos = (volume_table(ws, pos, b) if "num" not in b else rate_table(ws, pos, b)) + 4
ws.freeze_panes = "B7"
ws.cell(row=pos, column=1,
        value="Blank = market not in that table's visible Looker rows, not a zero. 'Total' columns cover the three channels shown only.").font = SUB


# =====================================================================
# Funnel — one row per segment, volumes then rates, left to right
# =====================================================================
ws = wb.create_sheet("Funnel")
ws.sheet_view.showGridLines = False
FS0 = 3
FW = 18   # 6 blocks x 3 columns
widths(ws, {"A": 26, "B": 12})
for col in range(FS0, FS0 + FW):
    ws.column_dimensions[gcl(col)].width = 11
title(ws, f"Funnel at a glance — {CUR_FULL} vs {LY_FULL}",
      "Sessions → Searches → Bookings, then the three rates. Paid Search + Organic + Direct only. Source: Totals and Countries tabs.")

FBLOCKS = [("Sessions", 0, NAVY, "vol"), ("Searches", 3, MID, "vol"),
           ("Bookings", 6, PLUM, "vol"), ("Visit→Search", 9, TEAL, "rate"),
           ("Search→Booking", 12, MOSS, "rate"), ("CR", 15, SLATE, "rate")]
FMT = {"Visit→Search": RATE, "Search→Booking": RATE2, "CR": RATE2}


def funnel_header(ws, row):
    for name, off, fill, kind in FBLOCKS:
        c0 = FS0 + off
        ws.merge_cells(start_row=row, start_column=c0, end_row=row, end_column=c0 + 2)
        c = ws.cell(row=row, column=c0, value=name)
        c.font = WHITE_B
        c.alignment = Alignment(horizontal="center", vertical="center")
        for k in range(3):
            cc = ws.cell(row=row, column=c0 + k)
            cc.fill = PatternFill("solid", fgColor=fill)
            cc.border = BOX
        subs = [LY_LABEL, CUR_LABEL, "% Δ"] if kind == "vol" else [LY_LABEL, CUR_LABEL, "Δ pp"]
        for k, sx in enumerate(subs):
            c = ws.cell(row=row + 1, column=c0 + k, value=sx)
            c.font = WHITE_B
            c.fill = PatternFill("solid", fgColor=fill)
            c.alignment = Alignment(horizontal="center")
            c.border = BOX
    for i, lab in enumerate(("Segment", "Split")):
        c = ws.cell(row=row, column=1 + i, value=lab)
        c.font = WHITE_B
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="left", vertical="center")
        ws.merge_cells(start_row=row, start_column=1 + i, end_row=row + 1, end_column=1 + i)
        ws.cell(row=row + 1, column=1 + i).fill = PatternFill("solid", fgColor=NAVY)
        c.border = BOX
        ws.cell(row=row + 1, column=1 + i).border = BOX
    ws.row_dimensions[row].height = 18


def funnel_row(ws, r, label, split, vols, bold=False, rates=None):
    """vols: [(sess_cy, sess_ly), (srch_cy, srch_ly), (book_cy, book_ly)] as formulas."""
    fv = Font(name=F, size=10, bold=bold, color="008000")
    fb = Font(name=F, size=10, bold=bold)
    c = ws.cell(row=r, column=1, value=label); c.font = BOLD if bold else BLACK; c.border = BOX
    c = ws.cell(row=r, column=2, value=split); c.font = BOLD if bold else BLACK; c.border = BOX
    for (name, off, fill, kind), (cy, ly) in zip(FBLOCKS[:3], vols):
        c0 = FS0 + off
        lyL, cyL = gcl(c0), gcl(c0 + 1)
        ws.cell(row=r, column=c0, value=ly).number_format = NUM
        ws.cell(row=r, column=c0).font = fv
        ws.cell(row=r, column=c0 + 1, value=cy).number_format = NUM
        ws.cell(row=r, column=c0 + 1).font = fv
        c = ws.cell(row=r, column=c0 + 2,
                    value=f'=IF(OR({lyL}{r}="",{cyL}{r}="",{cyL}{r}=0,{lyL}{r}=0),"",{cyL}{r}/{lyL}{r}-1)')
        c.number_format, c.font = PCT, fb
    pairs = (("Visit→Search", 3, 0), ("Search→Booking", 6, 3), ("CR", 6, 0))
    for (nm, numoff, denoff) in pairs:
        off = next(o for n, o, _f, _k in FBLOCKS if n == nm)
        c0 = FS0 + off
        for k in range(2):
            if rates:
                f = rates(nm, k, r)
            else:
                num, den = f"{gcl(FS0 + numoff + k)}{r}", f"{gcl(FS0 + denoff + k)}{r}"
                f = f'=IF(OR({num}="",{den}="",{den}=0),"",{num}/{den})'
            c = ws.cell(row=r, column=c0 + k, value=f)
            c.number_format, c.font = FMT[nm], fb
        lyL, cyL = gcl(c0), gcl(c0 + 1)
        c = ws.cell(row=r, column=c0 + 2,
                    value=f'=IF(OR({lyL}{r}="",{cyL}{r}=""),"",({cyL}{r}-{lyL}{r})*100)')
        c.number_format, c.font = PP, fb
    for k in range(FW):
        ws.cell(row=r, column=FS0 + k).border = BOX


def fsection(ws, r, text):
    c = ws.cell(row=r, column=1, value=text)
    c.font = SECT
    return r + 1


def safe_sum(col, first, last):
    """SUM over a market/country range that might be empty (a channel or market
    cut with zero visible Looker rows this period) — an inverted range like
    SUM(C10:C9) is a #VALUE! error in LibreOffice, so fall back to a literal 0."""
    if last < first:
        return "=0"
    return f'=SUM({gcl(col)}{first}:{gcl(col)}{last})'


FH = 4
funnel_header(ws, FH)
r = FH + 2
FIRST = r


def tot_pair(name, lg, ch, dev):
    base = [("A", lg), ("B", ch), ("C", dev)]
    return ("=" + sumifs(T, TCOL[name][1], base), "=" + sumifs(T, TCOL[name][0], base))


def tot_sum(name, lg, chans, dev):
    return tuple("=" + "+".join(sumifs(T, TCOL[name][k], [("A", lg), ("B", f'"{c}"'), ("C", dev)])
                                for c in chans) for k in (1, 0))


ALLCH = CHANNELS
# --- total
funnel_row(ws, r, "TOTAL — 3 channels", "All",
           [tot_sum(b["name"], '"All landing pages"', ALLCH, '"Total"') for b in FUNNEL_VOL], bold=True)
shade(ws, r, FS0)
r += 2
# --- by channel
r = fsection(ws, r, "By channel  (all landing pages, all devices)")
for ch in CHANNELS:
    funnel_row(ws, r, ch, "Total",
               [tot_pair(b["name"], '"All landing pages"', f'"{ch}"', '"Total"') for b in FUNNEL_VOL])
    r += 1
r += 1
# --- by landing page
r = fsection(ws, r, "By landing page group  (3 channels combined, all devices)")
for lg in ALL_LG:
    funnel_row(ws, r, lg, "Total",
               [tot_sum(b["name"], f'"{lg}"', ALLCH, '"Total"') for b in FUNNEL_VOL],
               bold=(lg == "All landing pages"))
    if lg == "All landing pages":
        shade(ws, r, FS0)
    r += 1
r += 1
# --- by device
r = fsection(ws, r, "By device  (3 channels combined, all landing pages)")
for dev in DEVICES:
    funnel_row(ws, r, "All traffic", dev,
               [tot_sum(b["name"], '"All landing pages"', ALLCH, f'"{dev}"') for b in FUNNEL_VOL],
               bold=(dev == "Total"))
    r += 1
r += 1
# --- by channel x device
r = fsection(ws, r, "By channel × device")
for ch in CHANNELS:
    for dev in ("Mobile", "Desktop"):
        funnel_row(ws, r, ch, dev,
                   [tot_pair(b["name"], '"All landing pages"', f'"{ch}"', f'"{dev}"') for b in FUNNEL_VOL])
        r += 1
r += 1
# --- by market
r = fsection(ws, r, "By market  (all landing pages, all channels, Mobile + Desktop — Looker visible rows only)")
MKT_FIRST = r
_present = set()
for _src in (COUNTRIES, COUNTRIES_LY, SEARCH_COUNTRIES, SEARCH_COUNTRIES_LY,
             PURCHASE_COUNTRIES, PURCHASE_COUNTRIES_LY):
    for _key, _rws in _src.items():
        if _key[0] == "All landing pages":
            for _c, _v in _rws:
                _present.add(_c)
FUNNEL_MARKETS = [c for c in COUNTRY_LIST if c in _present]


def mkt_rates(nm, k, rr):
    num_name = "Searches" if nm == "Visit→Search" else "Purchases"
    den_name = "Sessions" if nm in ("Visit→Search", "CR") else "Searches"
    ncol, dcol = CCOL[num_name][k], CCOL[den_name][k]
    crit = [("A", '"All landing pages"'), ("D", f"$A{rr}")]
    num = sumifs(K, ncol, crit + [(dcol, '">0"')])
    den = sumifs(K, dcol, crit + [(ncol, '">0"')])
    return f'=IF({den}=0,"",{num}/{den})'


for country in FUNNEL_MARKETS:
    funnel_row(ws, r, country, "All",
               [tuple(bz(sumifs(K, CCOL[b["name"]][k],
                                [("A", '"All landing pages"'), ("D", f"$A{r}")])) for k in (1, 0))
                for b in FUNNEL_VOL],
               rates=mkt_rates)
    r += 1
MKT_LAST = r - 1
funnel_row(ws, r, "Sum of listed markets", "All",
           [tuple(safe_sum(FS0 + o + k, MKT_FIRST, MKT_LAST) for k in (1, 0))
            for _n, o, _f, _k in FBLOCKS[:3]], bold=True)
shade(ws, r, FS0)
COVSUM = r
r += 1
funnel_row(ws, r, "Scorecard total (3 channels)", "All",
           [tot_sum(b["name"], '"All landing pages"', ALLCH, '"Total"') for b in FUNNEL_VOL], bold=True)
shade(ws, r, FS0)
SCOR = r
r += 1
c = ws.cell(row=r, column=1, value="Coverage of listed markets"); c.font = BOLD; c.border = BOX
ws.cell(row=r, column=2).border = BOX
for _n, o, _f, _k in FBLOCKS[:3]:
    for k in range(2):
        cl = gcl(FS0 + o + k)
        cc = ws.cell(row=r, column=FS0 + o + k, value=f'=IFERROR({cl}{COVSUM}/{cl}{SCOR},"")')
        cc.number_format, cc.font = RATE, BOLD
for k in range(FW):
    ws.cell(row=r, column=FS0 + k).border = BOX
shade(ws, r, FS0)
r += 2

# --- by market, Direct channel only
r = fsection(ws, r, "By market — Direct channel only  (all landing pages, Mobile + Desktop — Looker visible rows only)")
DMKT_FIRST = r
_direct_present = set()
for _src in (COUNTRIES, COUNTRIES_LY, SEARCH_COUNTRIES, SEARCH_COUNTRIES_LY,
             PURCHASE_COUNTRIES, PURCHASE_COUNTRIES_LY):
    for _key, _rws in _src.items():
        if _key[0] == "All landing pages" and _key[1] == "Direct":
            for _c, _v in _rws:
                _direct_present.add(_c)
DIRECT_MARKETS = [c for c in COUNTRY_LIST if c in _direct_present]


def direct_mkt_rates(nm, k, rr):
    num_name = "Searches" if nm == "Visit→Search" else "Purchases"
    den_name = "Sessions" if nm in ("Visit→Search", "CR") else "Searches"
    ncol, dcol = CCOL[num_name][k], CCOL[den_name][k]
    crit = [("A", '"All landing pages"'), ("B", '"Direct"'), ("D", f"$A{rr}")]
    num = sumifs(K, ncol, crit + [(dcol, '">0"')])
    den = sumifs(K, dcol, crit + [(ncol, '">0"')])
    return f'=IF({den}=0,"",{num}/{den})'


for country in DIRECT_MARKETS:
    funnel_row(ws, r, country, "Direct",
               [tuple(bz(sumifs(K, CCOL[b["name"]][k],
                                [("A", '"All landing pages"'), ("B", '"Direct"'), ("D", f"$A{r}")]))
                      for k in (1, 0))
                for b in FUNNEL_VOL],
               rates=direct_mkt_rates)
    r += 1
DMKT_LAST = r - 1
funnel_row(ws, r, "Sum of listed markets", "Direct",
           [tuple(safe_sum(FS0 + o + k, DMKT_FIRST, DMKT_LAST) for k in (1, 0))
            for _n, o, _f, _k in FBLOCKS[:3]], bold=True)
shade(ws, r, FS0)
DCOVSUM = r
r += 1
funnel_row(ws, r, "Scorecard total (Direct)", "All",
           [tot_pair(b["name"], '"All landing pages"', '"Direct"', '"Total"') for b in FUNNEL_VOL], bold=True)
shade(ws, r, FS0)
DSCOR = r
r += 1
c = ws.cell(row=r, column=1, value="Coverage of listed markets"); c.font = BOLD; c.border = BOX
ws.cell(row=r, column=2).border = BOX
for _n, o, _f, _k in FBLOCKS[:3]:
    for k in range(2):
        cl = gcl(FS0 + o + k)
        cc = ws.cell(row=r, column=FS0 + o + k, value=f'=IFERROR({cl}{DCOVSUM}/{cl}{DSCOR},"")')
        cc.number_format, cc.font = RATE, BOLD
for k in range(FW):
    ws.cell(row=r, column=FS0 + k).border = BOX
shade(ws, r, FS0)
r += 2

# --- by market x channel, Desktop only
r = fsection(ws, r, "By market x channel — Desktop only  (all landing pages — Looker visible rows only)")
for ch in CHANNELS:
    r = fsection(ws, r, f"{ch} — Desktop")
    ch_first = r
    _ch_present = set()
    for _src in (COUNTRIES, COUNTRIES_LY, SEARCH_COUNTRIES, SEARCH_COUNTRIES_LY,
                 PURCHASE_COUNTRIES, PURCHASE_COUNTRIES_LY):
        for _c, _v in _src.get(("All landing pages", ch, "Desktop"), []):
            _ch_present.add(_c)
    ch_markets = [c for c in COUNTRY_LIST if c in _ch_present]

    def ch_desk_rates(nm, k, rr, _ch=ch):
        num_name = "Searches" if nm == "Visit→Search" else "Purchases"
        den_name = "Sessions" if nm in ("Visit→Search", "CR") else "Searches"
        ncol, dcol = CCOL[num_name][k], CCOL[den_name][k]
        crit = [("A", '"All landing pages"'), ("B", f'"{_ch}"'), ("C", '"Desktop"'), ("D", f"$A{rr}")]
        num = sumifs(K, ncol, crit + [(dcol, '">0"')])
        den = sumifs(K, dcol, crit + [(ncol, '">0"')])
        return f'=IF({den}=0,"",{num}/{den})'

    for country in ch_markets:
        funnel_row(ws, r, country, ch,
                   [tuple(bz(sumifs(K, CCOL[b["name"]][k],
                                    [("A", '"All landing pages"'), ("B", f'"{ch}"'),
                                     ("C", '"Desktop"'), ("D", f"$A{r}")]))
                          for k in (1, 0))
                    for b in FUNNEL_VOL],
                   rates=ch_desk_rates)
        r += 1
    ch_last = r - 1
    funnel_row(ws, r, "Sum of listed markets", ch,
               [tuple(safe_sum(FS0 + o + k, ch_first, ch_last) for k in (1, 0))
                for _n, o, _f, _k in FBLOCKS[:3]], bold=True)
    shade(ws, r, FS0)
    ch_covsum = r
    r += 1
    funnel_row(ws, r, "Scorecard total", ch,
               [tot_pair(b["name"], '"All landing pages"', f'"{ch}"', '"Desktop"') for b in FUNNEL_VOL], bold=True)
    shade(ws, r, FS0)
    ch_scor = r
    r += 1
    c = ws.cell(row=r, column=1, value="Coverage of listed markets"); c.font = BOLD; c.border = BOX
    ws.cell(row=r, column=2).border = BOX
    for _n, o, _f, _k in FBLOCKS[:3]:
        for k in range(2):
            cl = gcl(FS0 + o + k)
            cc = ws.cell(row=r, column=FS0 + o + k, value=f'=IFERROR({cl}{ch_covsum}/{cl}{ch_scor},"")')
            cc.number_format, cc.font = RATE, BOLD
    for k in range(FW):
        ws.cell(row=r, column=FS0 + k).border = BOX
    shade(ws, r, FS0)
    r += 2
r -= 1
LASTF = r

trend_rules_f = [(FS0 + 2, PCT), (FS0 + 5, PCT), (FS0 + 8, PCT),
                 (FS0 + 11, PP), (FS0 + 14, PP), (FS0 + 17, PP)]
for col, _f in trend_rules_f:
    rng = f"{gcl(col)}{FIRST}:{gcl(col)}{LASTF}"
    ws.conditional_formatting.add(rng, CellIsRule(
        operator="greaterThan", formula=["0"], fill=PatternFill("solid", bgColor=GOOD)))
    ws.conditional_formatting.add(rng, CellIsRule(
        operator="lessThan", formula=["0"], fill=PatternFill("solid", bgColor=BADF)))
    ws.conditional_formatting.add(rng, CellIsRule(
        operator="greaterThan", formula=["1"], fill=PatternFill("solid", bgColor="FF9999")))

ws.freeze_panes = "C6"
ws.cell(row=LASTF + 2, column=1,
        value="Market rows come from the Looker country tables, which show only the top rows — they cover roughly 70-80% of sessions and less of bookings, so they do not sum to the scorecard. Rates use matched coverage.").font = SUB
ws.cell(row=LASTF + 3, column=1,
        value="A market can show more searches than sessions where it sits inside one table's visible rows but outside another's. The rate columns correct for that (matched coverage); the volume columns do not.").font = SUB
ws.cell(row=LASTF + 4, column=1,
        value="'Other pages (derived)' = All − Home − Airport − Route. Its rates are unreliable — the three views attribute the landing group differently — so read the named groups instead.").font = SUB
ws.cell(row=LASTF + 5, column=1,
        value="Markets with no data at the all-landing-pages level are omitted here; the full 32-market list is on 'L4 Market view' and 'Market Summary'.").font = SUB
ws.cell(row=LASTF + 6, column=1,
        value="Direct-channel market rows: the Looker Direct tables show only 9 visible rows (vs 10 for Paid Search/Organic), so coverage is naturally lower — see 'Coverage of listed markets' just above.").font = SUB
ws.cell(row=LASTF + 7, column=1,
        value="Direct's search→booking rate can be diluted by bot or scraper traffic, especially on desktop — see the README's Direct-channel note before treating any single Direct market's rate as a benchmark.").font = SUB
ws.cell(row=LASTF + 8, column=1,
        value="'By market x channel — Desktop only' is the place to look whenever a device's booking change looks out of step with its session change: compare each channel's 'Scorecard total' row to see which channel carries most of the gap.").font = SUB
ws.cell(row=LASTF + 9, column=1,
        value="Within each channel block, a market whose booking % change roughly tracks its session % change is a volume story. A market where the search→booking rate itself moves several points is a genuine conversion change, worth investigating first since it does not need more traffic to fix.").font = SUB
wb.move_sheet("Funnel", offset=-(len(wb.sheetnames) - 2))

# =====================================================================
# Gaps to fill
# =====================================================================
ws = wb.create_sheet("Gaps to fill")
ws.sheet_view.showGridLines = False
widths(ws, {"A": 11, "B": 12, "C": 10, "D": 22, "E": 13, "F": 10, "G": 17,
            "H": 12, "I": 11, "J": 11, "K": 26, "L": 44, "M": 15})
title(ws, "Gaps to fill",
      "Each row is a yellow cell on an input tab. Look the value up in Looker, type it into that cell, and every view updates. Type on the input tab, not here.")
ws["A3"] = ("All six metric columns are loaded. Every row below is a market visible in one Looker "
            "table but not another — its value is off-screen, not zero.")
ws["A3"].font = Font(name=F, size=10, bold=True, color=TEAL)
hdr(ws, 5, ["Tab", "Cell to fill", "Input row", "Landing Page Group", "Channel", "Device",
            "Country", "Market rank", "Metric", "Period", "Largest value in the same row",
            "What it unblocks", "Status"])

order_lg = {lg: i for i, lg in enumerate(LANDING_GROUPS)}
order_ch = {ch: i for i, ch in enumerate(CHANNELS)}
RANK = {c_: i + 1 for i, c_ in enumerate(COUNTRY_LIST)}
GAPS_SORTED = sorted(GAPS, key=lambda g: (g[10] == "Completeness only",
                                          RANK.get(g[6], 99),
                                          order_lg.get(g[3], 9), order_ch.get(g[4], 9),
                                          g[5], g[7], g[8]))
gr = 6
for (tab, row_ref, cell, lg, ch, dev, country, metric, period, known, blocks) in GAPS_SORTED:
    vals = [tab, cell, row_ref, lg, ch, dev, country, RANK.get(country),
            metric, period, known, blocks]
    for i, v in enumerate(vals):
        c = ws.cell(row=gr, column=1 + i, value=v)
        c.font = BLACK
        c.border = BOX
        if i == 10 and isinstance(v, int):
            c.number_format = NUM
    c = ws.cell(row=gr, column=13, value=f'=IF({tab}!{cell}="","STILL MISSING","Filled ✓")')
    c.font = BLACK
    c.border = BOX
    if (gr - 6) % 2 == 1:
        for col in range(1, 13):
            ws.cell(row=gr, column=col).fill = PatternFill("solid", fgColor=BAND)
    gr += 1
G_LAST = gr - 1
if G_LAST >= 6:
    ws.conditional_formatting.add(f"M6:M{G_LAST}", CellIsRule(
        operator="equal", formula=['"STILL MISSING"'], fill=PatternFill("solid", bgColor=YELL)))
    ws.conditional_formatting.add(f"M6:M{G_LAST}", CellIsRule(
        operator="equal", formula=['"Filled ✓"'], fill=PatternFill("solid", bgColor=GOOD)))
top10 = sum(1 for g in GAPS_SORTED if RANK.get(g[6], 99) <= 10)
ws.cell(row=G_LAST + 2, column=1, value="Still missing:").font = BOLD
c = ws.cell(row=G_LAST + 2, column=2, value=f'=COUNTIF(M6:M{G_LAST},"STILL MISSING")')
c.font = BOLD
ws.cell(row=G_LAST + 2, column=4,
        value=f"of {len(GAPS_SORTED)} listed gaps — {top10} of them in a top-10 market").font = BLACK
ws.cell(row=G_LAST + 4, column=1,
        value="Why a gap exists: Looker shows only the top rows of each table, so a market inside the top 10 for sessions can fall below the cut for searches or purchases. Its value is off-screen, not zero.").font = SUB
ws.cell(row=G_LAST + 5, column=1,
        value="Start with 'Market rank' ≤ 10 — those are the markets that actually move the read. Column L names what each missing cell unblocks; 'Completeness only' rows change nothing and sit at the bottom.").font = SUB
ws.freeze_panes = "A6"
ws.auto_filter.ref = f"A5:M{G_LAST}"
wb.move_sheet("Gaps to fill", offset=-(len(wb.sheetnames) - 3))

wb.save(OUT)
print("saved:", OUT)
print("countries:", len(COUNTRY_LIST), "| Totals 5..%d" % T_LAST,
      "| Countries 5..%d" % C_LAST, "| gaps:", len(GAPS_SORTED))
