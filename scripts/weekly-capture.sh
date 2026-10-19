#!/bin/zsh
# Weekly unattended capture of the Suntransfers B2C YoY funnel report.
#
# Scheduled by ~/Library/LaunchAgents/com.suntransfers.looker-yoy-weekly.plist
# to run Tuesdays at 01:00. Captures the last completed Monday-Sunday week
# against the same weekdays a year earlier (-364 days, which is what keeps
# Monday aligned with Monday; -365 would compare a Monday with a Sunday).
#
# Each week writes to its own output dir. The capture merges into an existing
# data.json by design, so sharing one dir would silently mix two periods.
#
# Modes (first argument):
#   full     (default) both periods of the last completed week.
#   prior    Friday: only the prior year of the week that contains today. Last
#            year's data cannot change, so capturing it ahead of time halves
#            the Tuesday run. No workbook or gate: there is no current yet.
#   current  Tuesday: only the current period of the last completed week, plus
#            whatever prior combinations the Friday run did not leave ok, then
#            the workbook and the gate as in full mode.
# prior and current land in the same per-week dir, so the merge joins them.

set -u
MODE="${1:-full}"
case "$MODE" in
  full|prior|current) ;;
  *) echo "usage: weekly-capture.sh [full|prior|current]" >&2; exit 64 ;;
esac
ROOT="$HOME/looker-yoy-capture"
PY="$ROOT/.venv/bin/python"

read -r CUR_START CUR_END PRI_START PRI_END OUT_TAG <<<"$(MODE="$MODE" "$PY" - <<'PYEOF'
import os
from datetime import date, timedelta
# WEEKLY_TODAY=yyyy-mm-dd pretends to run on another day, for testing the dates.
t = date.fromisoformat(os.environ["WEEKLY_TODAY"]) if os.environ.get("WEEKLY_TODAY") else date.today()
if os.environ["MODE"] == "prior":
    sunday = t + timedelta(days=6 - t.weekday())     # Sunday of this week
else:
    sunday = t - timedelta(days=(t.weekday() + 1) % 7)   # last completed Sunday
cs, ce = sunday - timedelta(days=6), sunday
ps, pe = cs - timedelta(days=364), ce - timedelta(days=364)
f = lambda d: d.strftime("%d/%m/%Y")
print(f(cs), f(ce), f(ps), f(pe), f"{cs:%Y-%m-%d}_{ce:%Y-%m-%d}")
PYEOF
)"

OUT="$ROOT/output/weekly/$OUT_TAG"
LOG="$ROOT/logs/weekly-$OUT_TAG.log"
mkdir -p "$OUT"

notify() { /usr/bin/osascript -e "display notification \"$1\" with title \"Looker YoY capture\"" >/dev/null 2>&1 || true; }

# Only one capture at a time. Two of them race for Chrome's debugging port and
# the second dies with "Something is already listening on port 9222" - which is
# exactly what happened the first time this ran alongside a manual run. mkdir is
# atomic, so it works as a lock without needing flock (absent on stock macOS).
LOCK="$ROOT/.weekly-capture.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  OTHER=$(cat "$LOCK/pid" 2>/dev/null || echo "?")
  if [[ "$OTHER" != "?" ]] && kill -0 "$OTHER" 2>/dev/null; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') skipped: capture already running (pid $OTHER)" >>"$LOG"
    notify "Skipped: a capture is already running."
    exit 0
  fi
  # Lock left behind by a run that died without cleaning up.
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') clearing stale lock from pid $OTHER" >>"$LOG"
  rm -rf "$LOCK"
  mkdir "$LOCK" || { echo "cannot create lock $LOCK" >>"$LOG"; exit 1; }
fi
echo $$ >"$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT INT TERM

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') starting ($MODE)"
  echo "    current $CUR_START-$CUR_END   prior $PRI_START-$PRI_END"
  echo "    output  $OUT"
} >>"$LOG"

# Pages that feed the workbook. kpis_by_route and booking_funnel are left out on
# purpose: they have no Landing Page Group control, so all 8 of their
# combinations fail on every run and only cost time.
PAGES=sessions,start_search,searches,purchases,select_item,add_to_cart,begin_checkout,horizontal
BASE=(--current-range "$CUR_START-$CUR_END" --prior-range "$PRI_START-$PRI_END" --headless)

# One capture invocation, appended to the log. Extra args select pages/groups.
capture() { "$PY" -m looker_capture "${BASE[@]}" --output-dir "$OUT" "$@" >>"$LOG" 2>&1 </dev/null; }

# WEEKLY_SMOKE_TEST=1 verifies the whole wrapper (dates, paths, auth, the
# Looker controls) in a couple of minutes instead of the full run.
if [[ "${WEEKLY_SMOKE_TEST:-0}" == "1" ]]; then
  echo "    SMOKE TEST: dry-run sessions/all" >>"$LOG"
  SMOKE=$(/usr/bin/mktemp -d)
  "$PY" -m looker_capture "${BASE[@]}" --output-dir "$SMOKE" --dry-run --pages sessions --landing-groups all >>"$LOG" 2>&1 </dev/null
  RC=$?
  rm -rf "$SMOKE"
  echo "=== smoke test exit $RC (no workbook expected)" >>"$LOG"
  exit $RC
fi

# Pre-flight: a dry run into a scratch dir fails within seconds if Google
# expired the session, instead of discovering it at the start of a long run.
PRE=$(/usr/bin/mktemp -d)
"$PY" -m looker_capture "${BASE[@]}" --output-dir "$PRE" --dry-run --pages sessions --landing-groups all >>"$LOG" 2>&1
RC=$?
rm -rf "$PRE"
[[ $RC -ne 0 ]] && echo "pre-flight failed (rc=$RC); full capture not started" >>"$LOG"

prior_gaps() { "$PY" "$ROOT/scripts/period_gaps.py" "$OUT/data.json" prior "$PAGES" 2>>"$LOG"; }

if [[ "$MODE" == "prior" ]]; then
  # Capture, then ONE pass over whatever is still not ok, then stop.
  if [[ $RC -eq 0 ]]; then
    capture --pages "$PAGES" --periods prior --no-build-xlsx
    RC=$?
    GAPS=$(prior_gaps)
    if [[ $RC -eq 0 && -n "$GAPS" ]]; then
      echo "=== $(date '+%Y-%m-%d %H:%M:%S') retrying prior: $(echo "$GAPS" | tr '\n' ';')" >>"$LOG"
      while read -r RPAGE RGROUP; do
        [[ -z "$RPAGE" ]] && continue
        capture --pages "$RPAGE" --landing-groups "$RGROUP" --periods prior --no-build-xlsx
      done <<<"$GAPS"
      GAPS=$(prior_gaps)
    fi
  fi
  if [[ $RC -ne 0 ]]; then
    if /usr/bin/grep -qi -e 'expired' -e 'sign.\?in' -e 'not authenticated' "$LOG"; then
      echo "FAILED rc=$RC - looks like the Google session expired; run: $PY -m looker_capture --login" >>"$LOG"
      notify "Prior-year capture: session expired. Run --login before Tuesday."
    else
      echo "FAILED rc=$RC - see $LOG" >>"$LOG"
      notify "Prior-year capture failed (rc=$RC). Tuesday will capture it instead."
    fi
  elif [[ -n "$GAPS" ]]; then
    echo "PRIOR INCOMPLETE $(date '+%H:%M:%S') - Tuesday will re-capture: $(echo "$GAPS" | tr '\n' ';')" >>"$LOG"
    notify "Prior year captured with gaps; Tuesday will fill them in."
    RC=2
  else
    echo "PRIOR OK $(date '+%H:%M:%S') - $PRI_START-$PRI_END ready in $OUT" >>"$LOG"
    notify "Prior year $PRI_START-$PRI_END captured."
  fi
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') exit $RC" >>"$LOG"
  exit $RC
fi

if [[ $RC -eq 0 && "$MODE" == "current" ]]; then
  capture --pages "$PAGES" --periods current
  RC=$?
  # Fill in whatever the Friday run did not leave ok (all of it if it never ran).
  GAPS=$(prior_gaps)
  if [[ $RC -eq 0 && -n "$GAPS" ]]; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') prior not ready, capturing: $(echo "$GAPS" | tr '\n' ';')" >>"$LOG"
    while read -r RPAGE RGROUP; do
      [[ -z "$RPAGE" ]] && continue
      capture --pages "$RPAGE" --landing-groups "$RGROUP" --periods prior
    done <<<"$GAPS"
  fi
elif [[ $RC -eq 0 ]]; then
  capture --pages "$PAGES"
  RC=$?
fi

XLSX=$(/bin/ls -1 "$OUT"/*.xlsx 2>/dev/null | /usr/bin/head -1)
GATE_RC=""
GATE_SUMMARY=""

# Gate, then ONE targeted re-capture of whatever is not ok or is flagged
# (quota errors leave silent gaps in an otherwise complete-looking workbook),
# then the gate again. A single pass, so a persistent fault cannot loop.
if [[ $RC -eq 0 && -n "$XLSX" ]]; then
  GATE_JSON="$OUT/gate-retry.json"
  "$PY" "$ROOT/scripts/check_consistency.py" "$XLSX" --json "$GATE_JSON" >>"$LOG" 2>&1
  RETRIES=$("$PY" "$ROOT/scripts/retry_plan.py" "$OUT/data.json" "$GATE_JSON" 2>>"$LOG")
  if [[ -n "$RETRIES" ]]; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') retrying: $(echo "$RETRIES" | tr '\n' ';')" >>"$LOG"
    while read -r RPAGE RGROUP; do
      [[ -z "$RPAGE" ]] && continue
      capture --pages "$RPAGE" --landing-groups "$RGROUP"
    done <<<"$RETRIES"
    XLSX=$(/bin/ls -1 "$OUT"/*.xlsx 2>/dev/null | /usr/bin/head -1)
  fi
  GATE_OUT=$("$PY" "$ROOT/scripts/check_consistency.py" "$XLSX" 2>&1)
  GATE_RC=$?
  echo "$GATE_OUT" >>"$LOG"
  GATE_SUMMARY=$(echo "$GATE_OUT" | /usr/bin/grep -E '^\s+.* / .* \[' | /usr/bin/head -5 | tr '\n' ';')
fi

if [[ $RC -ne 0 ]]; then
  # The usual cause is Google having expired the session: it needs a real
  # browser window, so it cannot be fixed unattended.
  if /usr/bin/grep -qi -e 'expired' -e 'sign.\?in' -e 'not authenticated' "$LOG"; then
    echo "FAILED rc=$RC - looks like the Google session expired; run: $PY -m looker_capture --login" >>"$LOG"
    notify "Session expired. Run --login to re-authenticate."
  else
    echo "FAILED rc=$RC - see $LOG" >>"$LOG"
    notify "Capture failed (rc=$RC). See logs/weekly-$OUT_TAG.log"
  fi
elif [[ -z "$XLSX" ]]; then
  echo "FINISHED rc=0 but no .xlsx was produced - check $LOG and $OUT/workbook/UNMAPPED.md" >>"$LOG"
  notify "Finished but produced no workbook. Check the log."
elif [[ "$GATE_RC" != "0" ]]; then
  echo "SUSPECT $(date '+%H:%M:%S') -> $XLSX - gate failed after retry: $GATE_SUMMARY" >>"$LOG"
  notify "Workbook SUSPECT after retry. Do not use until re-captured. See log."
  RC=2
else
  echo "OK $(date '+%H:%M:%S') gate CLEAN -> $XLSX" >>"$LOG"
  notify "Done and CLEAN: $CUR_START-$CUR_END captured."
fi

echo "=== $(date '+%Y-%m-%d %H:%M:%S') exit $RC" >>"$LOG"
exit $RC
