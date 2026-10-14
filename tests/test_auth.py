"""Auth checks that don't need an interactive Google sign-in.

Covers the things that actually went wrong while building this: a signed-in
check that was fooled by a Cookies file Chrome creates on any page load, and
"localhost" resolving to ::1 while Chrome binds IPv4 only.

Run: .venv/bin/python tests/test_auth.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from looker_capture import auth  # noqa: E402

FAILURES: list[str] = []


def check(label: str, got, expected) -> None:
    if got != expected:
        FAILURES.append(f"{label}: expected {expected!r}, got {got!r}")


# --- Chrome discovery ------------------------------------------------------

binary = auth.find_chrome()
check("find_chrome returns an existing binary", Path(binary).exists(), True)


# --- the dedicated profile must never be the everyday one ------------------

everyday = Path.home() / "Library/Application Support/Google/Chrome"
check(
    "default profile dir is not the everyday Chrome profile",
    auth.DEFAULT_PROFILE_DIR.expanduser() != everyday,
    True,
)


# --- signed-in detection ---------------------------------------------------

check(
    "a nonexistent profile is not signed in",
    auth.profile_is_signed_in(Path("/tmp/looker_no_such_profile_xyz")),
    False,
)

# A profile Chrome merely started in has a Cookies file but no Google session.
fresh = Path("/tmp/looker_auth_test_fresh")
shutil.rmtree(fresh, ignore_errors=True)
process = auth.launch_chrome(fresh, 9233, headless=True)
auth._terminate(process)
check("launch_chrome created the profile", (fresh / "Default").exists(), True)
check(
    "a fresh profile with a Cookies file is NOT reported as signed in",
    auth.profile_is_signed_in(fresh),
    False,
)
shutil.rmtree(fresh, ignore_errors=True)


# --- CDP reachability ------------------------------------------------------

check("an unused port is not reachable", auth.cdp_reachable(9299, timeout=1.0), False)

process = auth.launch_chrome(Path("/tmp/looker_auth_test_port"), 9234, headless=True)
try:
    check("launch_chrome opens the debugging port", auth.cdp_reachable(9234), True)
    # Refuse to hijack a port already in use rather than silently attaching.
    try:
        auth.launch_chrome(Path("/tmp/looker_auth_test_port2"), 9234, headless=True)
        FAILURES.append("launching on an occupied port should have raised AuthError")
    except auth.AuthError as exc:
        check("occupied port raises a clear error", "already listening" in str(exc), True)
finally:
    auth._terminate(process)
    shutil.rmtree("/tmp/looker_auth_test_port", ignore_errors=True)
    shutil.rmtree("/tmp/looker_auth_test_port2", ignore_errors=True)

check("port is released after terminate", auth.cdp_reachable(9234, timeout=1.0), False)


if FAILURES:
    print(f"{len(FAILURES)} failure(s):")
    for line in FAILURES:
        print(f"  - {line}")
    sys.exit(1)
print("all auth checks passed")
