"""Print the (page, landing group) pairs worth re-capturing, one "page group" per line.

Combines two sources, deduplicated:
  - data.json combinations whose status is not "ok" (quota_error, failed)
  - the gate's --json output (empty cells, arithmetic violations)

The CLI re-captures a page/group for both periods, so the period is dropped.

  python scripts/retry_plan.py DATA.json [GATE.json]
"""
import json
import sys
from pathlib import Path

GROUP_SLUGS = {
    "All landing pages": "all",
    "Home page": "home",
    "Airport page": "airport",
    "Route page": "route",
}


def plan(data, gate=None):
    pairs = set()
    for page, body in data.get("pages", {}).items():
        for period in body.get("periods", {}).values():
            for group, res in period.get("groups", {}).items():
                if res.get("status") != "ok" and group in GROUP_SLUGS:
                    pairs.add((page, GROUP_SLUGS[group]))
    for item in (gate or {}).get("retry", []):
        pairs.add((item["page"], item["group"]))
    return sorted(pairs)


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    data = json.loads(Path(sys.argv[1]).read_text())
    gate = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) == 3 else None
    for page, group in plan(data, gate):
        print(page, group)


if __name__ == "__main__":
    main()
