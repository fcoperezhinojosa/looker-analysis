# looker-yoy-capture

Captures the Suntransfers B2C YoY funnel report out of Looker Studio
(`fb949fdd-dd2f-4cdb-95db-16d82bd003e9`) without a human clicking through every
page, date range, and Landing Page Group combination by hand.

For each `page x period x landing group` combination it:

- opens the report in `/edit` mode (view mode never loads the underlying data),
- sets the date range and isolates the landing group, verifying each one by
  reading the control's own chip back,
- waits for the charts to render and backs off through Looker's "Quota Error",
- takes a full-page screenshot plus one legible screenshot per tile,
- reads the numbers straight out of the DOM (scorecards and tables) so nobody
  has to retype them,
- archives Looker's own network responses as a secondary source,
- and writes `data.json`, per-table CSVs, and the `data*.py` files that the
  `suntransfers-yoy-funnel` skill's workbook builder expects.

Scraping a UI you don't control is inherently the most fragile way to get
these numbers — any redesign of Looker Studio can break the selectors in
`looker_capture/selectors.py`. `--dry-run` exists specifically to re-validate
those selectors in under a minute after a Looker UI change, without waiting
through a full capture. The durable fix, if this becomes a recurring pain, is
to pull the same metrics from the GA4 Data API directly — that's out of scope
here but worth knowing about.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m playwright install chromium
```

Python 3.10+ is required (built and tested on 3.12).

The tool drives your real, installed **Google Chrome** — it launches the
Chrome binary directly and attaches Playwright to it afterwards, rather than
letting Playwright launch a browser (see *Why it works this way* below). No
separate install step is needed if Chrome is already on the machine. The
`playwright install chromium` line above is only a fallback for a box with no
Chrome at all; note that Google's sign-in form does not render in the bundled
Chromium, so that fallback can only work against an already-signed-in
profile.

## First run: sign in once

The report requires a Google account with **edit** access. Run:

```bash
.venv/bin/python -m looker_capture --login
```

A real Chrome window opens on the report, signed out. Sign in by hand, then
**wait** — Looker Studio shows placeholder chart icons for 20-30 seconds
before the real scorecards and country tables render. Don't confirm until you
see actual numbers, not just the editor chrome around them. Then press Enter
in the terminal.

That's it — one time only. The signed-in profile is kept at
`~/.looker-yoy-capture/chrome-profile` and every capture run reuses it, so
they never see a sign-in page. A backup of the profile is taken at the same
time, so if a run ever leaves it signed out you recover with
`--restore-profile` instead of signing in again.

`auth.json` is also written, but it is a **diagnostic record only** — it
cannot restore a session. Google binds its session cookies to the browser
instance (device-bound credentials), so replaying them into another profile
lands on an accounts.google.com "Signed out" page. Tested, not assumed.

Re-run `--login` if the session ever expires — the tool detects that and
tells you.

### Why it works this way

Three things were tried and ruled out by testing, not assumption:

1. **Signing in inside a Playwright-launched browser** — Google serves a
   blank page. Stripping the automation flags (`--enable-automation`,
   `AutomationControlled`) is not enough; the CDP channel itself is detected.
2. **Borrowing your everyday Chrome profile** — Chrome 136+ hard-refuses:
   *"DevTools remote debugging requires a non-default data directory."*
3. **Copying that profile somewhere else** — Chrome loads it but lands on
   accounts.google.com in a "Signed out" state; the auth cookies don't
   survive the copy.

What does work, and what the tool does: launch the real Chrome binary as an
ordinary subprocess (not through Playwright) against a **dedicated** profile
with a debugging port. Google treats that as a normal browser, so the
sign-in form renders and you authenticate once; Playwright then attaches over
CDP only *after* you're signed in.

This is also why `--chrome-profile-dir` must not point at your everyday
Chrome profile — Chrome would refuse the debugging port, and it keeps this
tool out of a profile holding unrelated logins and saved passwords.

If the edit-access account isn't the first Google session in that profile,
pass `--account-index N` to select the `/u/N/` account, on both `--login` and
every capture run afterwards.

## Running a capture

```bash
.venv/bin/python -m looker_capture \
  --current-range 01/08/2026-23/08/2026 \
  --prior-range 01/08/2025-23/08/2025
```

By default this runs headless, captures every report page, all four landing
groups (All / Home / Airport / Route), and writes everything under `./output`.

Useful flags:

| Flag | Default | Purpose |
|---|---|---|
| `--pages` | all 7 | comma-separated slugs: `sessions,start_search,searches,purchases,kpis_by_route,booking_funnel,horizontal` |
| `--landing-groups` | all 4 | comma-separated: `all,home,airport,route` |
| `--headless` / `--no-headless` | headless | watch it run with `--no-headless` |
| `--browser-channel` | `chrome` | Playwright channel for capture runs (`chrome`, `chromium`, `msedge`) |
| `--chrome-profile-dir` | `~/.looker-yoy-capture/chrome-profile` | the dedicated signed-in profile; must not be your everyday Chrome profile |
| `--cdp-port` | 9222 | remote-debugging port for the Chrome it launches |
| `--restore-profile` | — | restore the profile from its last `--login` backup, then exit |
| `--output-dir` | `./output` | where everything is written |
| `--dry-run` | off | navigate + verify chips, capture nothing — for re-checking selectors fast |
| `--settle-seconds` | 35 | fixed wait after any date/filter change (30–40s range) |
| `--pause-seconds` | 10 | pause between combinations, to avoid triggering Quota Error |
| `--quota-retries` | 3 | retries (with backoff) when a Quota Error appears |
| `--scale` | 2 | screenshot device-scale factor, for legible tiles |
| `--no-network-capture` | on | skip archiving Looker's internal data responses |
| `--no-emit-data-files` | on | skip writing the workbook's `data*.py` files |
| `--layout-map <file.json>` | — | manual tile→(channel,device) overrides, see below |
| `-v` | off | verbose logging |

## Re-validating selectors after a Looker UI change

```bash
.venv/bin/python -m looker_capture --dry-run --no-headless \
  --pages sessions --current-range 01/08/2026-23/08/2026 \
  --prior-range 01/08/2025-23/08/2025
```

This navigates, sets the date and landing-group controls, and reports whether
each chip verified — no screenshots, no DOM extraction. Check `output/run.log`
for `date_chip=OK` / `filter_chip=OK` on all four groups.

## Output

```
output/
  run.log              # one line per step, with timestamps
  data.json             # everything captured, structured
  workbook/
    data.py  data_ly.py
    data_start_search.py  data_start_search_ly.py
    data_search.py        data_search_ly.py
    data_purchase.py      data_purchase_ly.py
    UNMAPPED.md          # tiles that could not be attributed to a (channel, device)
  raw/<page>/<period>/<group>/net_*.json   # Looker's own responses, archived
  <page>/<period>/<group>/
    full.png             # full-page screenshot
    canvas.png            # just the report canvas
    tile_00.png ...        # one legible screenshot per tile, index-paired with data.json
    table_02.csv ...       # one CSV per table tile
  Suntransfers_Funnel_YoY_<cur>_vs_<ly>.xlsx   # the final workbook
```

`workbook/*.py` follows exactly the shape
`suntransfers-yoy-funnel/references/data-schema.md` expects: unread values are
`None`/omitted, never `0`; country names are copied verbatim; `LANDING_GROUPS`
/ `CHANNELS` / `DEVICES` are untouched.

**The `.xlsx` is built automatically**, as the last step of a capture run (on
by default; turn it off with `--no-build-xlsx`, or send it somewhere other
than `--output-dir` with `--xlsx-dir`). It runs a vendored copy of the
`suntransfers-yoy-funnel` skill's own `build.py` against the `workbook/*.py`
files this tool just wrote — same generator, same ten sheets (README, Funnel,
Gaps to fill, Totals, Countries, L1-L4, Market Summary), same conventions
(LY-before-CUR columns, blank-not-zero, top-10 countries). The filename
follows that skill's own pattern:
`Suntransfers_Funnel_YoY_<current label>_vs_<prior label>.xlsx`, e.g.
`Suntransfers_Funnel_YoY_1-23Aug26_vs_1-23Aug25.xlsx` for a 1-23 Aug range.

If the build fails (missing data, a bad EXTRA_NOTES edit, whatever), the
capture itself is not lost — `output/data.json` and `output/workbook/*.py`
are already on disk; only the last step needs retrying, which you can do
directly:

```bash
.venv/bin/python -c "
from pathlib import Path
from looker_capture import workbook
from looker_capture.config import Period
from datetime import date
cur = Period('current', date(2026,8,1), date(2026,8,23))
prior = Period('prior', date(2025,8,1), date(2025,8,23))
workbook.build_xlsx(Path('output/workbook'), cur, prior, Path('output'))
"
```

If you'd rather build it through the skill directly instead (e.g. to hand-edit
`EXTRA_NOTES` for a data-quality caveat, or to get the stakeholder readout via
`/suntransfers-funnel-readout` afterwards), copy the eight `workbook/*.py`
files over the templates in that skill's own working folder and run
`/suntransfers-yoy-funnel` as usual — nothing here requires using the
built-in build step.

**Always check `workbook/UNMAPPED.md` before trusting a fresh capture.** A
tile the classifier couldn't confidently attribute to a (channel, device) is
listed there and is *missing* from the data files rather than guessed at. Fix
it either by tuning `CHANNEL_PATTERNS` / `DEVICE_PATTERNS` in
`looker_capture/config.py`, or by passing `--layout-map` with an explicit
mapping, e.g.:

```json
{ "sessions": { "7": ["Direct", "Total"] } }
```

(page slug → tile index → `[channel, device]`, tile indices come from
`data.json`).

## How the two controls actually work

Worked out by inspecting the live report; both are Angular Material, and
neither behaves like a plain form field.

**Edit mode needs two clicks.** The first click on a control only *selects*
the component (and opens the editor's Properties panel); a second click opens
its dropdown. Whether a given click selects or opens depends on whether the
component was already selected, so the code clicks and re-checks rather than
assuming (`open_control`).

**Date range** is a draggable dialog (`ng2-date-picker-dialog`) holding two
`mat-calendar` grids, `.start-date-picker` and `.end-date-picker`. Dates are
**clicked, not typed** — day cells are buttons labelled `1 Aug 2026`, and the
month is paged with `[aria-label="Previous month"]` / `"Next month"` while
reading the period button (`AUG 2026`) to know where you are. There is no text
input anywhere in it. An earlier version tried to type into
`input[aria-label*="start"]`, which silently matched the Properties panel's
**"start date offset"** number box instead — a completely different control.

After Apply, the code waits for the dialog to actually disappear: it is a cdk
overlay, and while it lingers it invisibly intercepts every later click, which
shows up as an inexplicable 30-second click timeout on a plainly visible
control.

**Landing Page Group** is a checklist of `md-checkbox` elements inside the
report iframe (not the main document's overlay), addressed by `aria-label`:
`"Home page"`, `"Airport page"`, `"Route page"`, `"(not set)"`, plus a dozen
more, and `"Landing Page Group (Select all)"`. Checked state is the
**`md-checked` class** — there is no `aria-checked` to read. Isolation uses the
`span.only` link that appears on row hover, falling back to clearing via
(Select all) and ticking the one box.

The chip is read with JS across frames rather than from the aria-labelled
element, because that element is a wrapper whose own `innerText` is empty —
which previously produced a blank chip that then wrongly "verified" as
all-groups-selected. An empty chip is now always a verification failure.

## Known failure modes

- **Quota Error.** Looker throttles a data source hit too rapidly. The tool
  detects it inside the chart iframes, backs off (45s → 90s → 180s), and
  reapplies the date/filter controls before retrying — Looker sometimes resets
  them on its own during recovery. After `--quota-retries` the combination is
  marked `quota_error` with no fabricated data, and the run moves on.
- **A control doesn't respond.** Each control gets 3 attempts with backoff. If
  it still doesn't verify, the exact reason is logged and that one combination
  is marked `failed` — the run continues with the rest.
- **Session expired.** Detected on the first navigation; the tool stops and
  tells you to re-run `--login`, rather than silently capturing empty pages.
- **A number Looker abbreviates (e.g. "12.3K").** Recorded but flagged — the
  exact figure isn't recoverable from the DOM, so it's excluded from
  `workbook/*.py` and listed in `UNMAPPED.md` instead of being written as a
  rounded guess.
