"""Print the (page, landing group) pairs of one period that are not captured ok.

Unlike retry_plan.py, this also reports combinations that are missing from
data.json altogether, which is what a skipped or crashed Friday run leaves:
the Tuesday run uses it to fill in whatever the prior year still lacks.

  python scripts/period_gaps.py DATA.json PERIOD PAGE[,PAGE...]
"""
import json
import sys
from pathlib import Path

from retry_plan import GROUP_SLUGS


def gaps(data, period, pages):
    out = []
    for page in pages:
        groups = (
            data.get("pages", {}).get(page, {}).get("periods", {}).get(period, {}).get("groups", {})
        )
        for group, slug in GROUP_SLUGS.items():
            if groups.get(group, {}).get("status") != "ok":
                out.append((page, slug))
    return out


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    data = json.loads(path.read_text()) if path.exists() else {}
    for page, group in gaps(data, sys.argv[2], sys.argv[3].split(",")):
        print(page, group)


if __name__ == "__main__":
    main()
