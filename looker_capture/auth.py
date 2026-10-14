"""Getting an authenticated Looker Studio session, and keeping it.

Why this is more involved than "log in with Playwright":

  * Google refuses to render its sign-in form in any browser Playwright
    launches itself — the page comes up blank. Stripping the automation flags
    (--enable-automation, AutomationControlled) is not enough; Google detects
    the CDP channel itself.
  * You cannot borrow the session from your everyday Chrome profile either.
    Chrome 136+ hard-refuses remote debugging on the default profile
    ("DevTools remote debugging requires a non-default data directory"), and
    copying the profile elsewhere loses the auth cookies — the copy lands in
    an accounts.google.com "Signed out" state.

What does work, and what this module does: launch the real Chrome binary as
an ordinary subprocess (not through Playwright) against a **dedicated**
profile directory, with a remote-debugging port. Google is happy with that
browser, so the sign-in form renders and you sign in by hand exactly once.
That profile then persists, and subsequent capture runs reuse it directly, so
they never touch a sign-in page at all.

All of the above was verified against this report, not assumed.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
)

from .config import PAGES, ReportPage

log = logging.getLogger(__name__)

DEFAULT_VIEWPORT = {"width": 1680, "height": 2400}
DEFAULT_CHANNEL = "chrome"
DEFAULT_CDP_PORT = 9222

# A profile of our own. Never the everyday one: Chrome will not expose a
# debugging port on the default profile, and sharing it would also mean this
# tool ran inside a profile holding unrelated logins and saved passwords.
DEFAULT_PROFILE_DIR = Path.home() / ".looker-yoy-capture" / "chrome-profile"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta",
]

# Flags that keep the launched browser looking like an ordinary one.
STEALTH_ARGS = ["--disable-blink-features=AutomationControlled"]
IGNORED_DEFAULT_ARGS = ["--enable-automation"]


class AuthError(RuntimeError):
    """No usable session: not signed in yet, expired, or no access."""


@dataclass
class Session:
    """A live browser context plus whatever needs closing behind it."""

    context: BrowserContext
    browser: Browser | None = None
    process: subprocess.Popen | None = None

    async def close(self) -> None:
        try:
            await self.context.close()
        except Exception:  # noqa: BLE001 - already gone is fine
            pass
        if self.browser is not None:
            try:
                await self.browser.close()
            except Exception:  # noqa: BLE001
                pass
        if self.process is not None:
            _terminate(self.process)


# ---------------------------------------------------------------------------
# Chrome as a plain subprocess
# ---------------------------------------------------------------------------


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("google-chrome") or shutil.which("chrome")
    if found:
        return found
    raise AuthError(
        "Could not find Google Chrome. Install it, or pass --browser-channel chromium "
        "to fall back to Playwright's bundled browser (note: Google's sign-in form does "
        "not render in that one, so it only works once a session already exists)."
    )


def cdp_reachable(port: int, timeout: float = 2.0) -> bool:
    # 127.0.0.1, never "localhost": localhost can resolve to ::1 while Chrome
    # binds IPv4 only, which surfaces as a confusing ECONNREFUSED ::1:<port>.
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/json/version", timeout=timeout
        ) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _wait_for_cdp(port: int, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cdp_reachable(port):
            return
        time.sleep(0.5)
    raise AuthError(
        f"Chrome did not open a debugging port on {port} within {timeout:.0f}s. "
        "If it logged 'remote debugging requires a non-default data directory', the "
        "profile directory being used is your everyday Chrome profile — pass a "
        "different --chrome-profile-dir."
    )


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def launch_chrome(
    profile_dir: Path,
    port: int,
    headless: bool,
    binary: str | None = None,
    extra_args: list[str] | None = None,
) -> subprocess.Popen:
    """Start real Chrome on its own profile with a debugging port open."""
    profile_dir = profile_dir.expanduser()
    profile_dir.mkdir(parents=True, exist_ok=True)
    if cdp_reachable(port):
        raise AuthError(
            f"Something is already listening on port {port}. Close it, or pass a "
            "different --cdp-port."
        )

    args = [
        binary or find_chrome(),
        f"--user-data-dir={profile_dir}",
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-dev-shm-usage",
        *STEALTH_ARGS,
        *(extra_args or []),
    ]
    if headless:
        args.append("--headless=new")
    args.append("about:blank")

    log.info("Launching Chrome on profile %s (debug port %d)", profile_dir, port)
    process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _wait_for_cdp(port)
    except AuthError:
        _terminate(process)
        raise
    return process


# ---------------------------------------------------------------------------
# Interactive sign-in
# ---------------------------------------------------------------------------


async def login(
    playwright: Playwright,
    auth_file: Path,
    account: int = 0,
    landing_page: ReportPage | None = None,
    profile_dir: Path | None = None,
    port: int = DEFAULT_CDP_PORT,
    channel: str = DEFAULT_CHANNEL,  # noqa: ARG001 - kept for CLI compatibility
) -> None:
    """Sign in by hand, once, in a real visible Chrome on our own profile."""
    profile_dir = (profile_dir or DEFAULT_PROFILE_DIR).expanduser()
    page_def = landing_page or PAGES["sessions"]
    target = page_def.url(account)

    process = launch_chrome(profile_dir, port, headless=False)
    browser: Browser | None = None
    page: Page | None = None
    try:
        browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()
        await page.goto(target, wait_until="domcontentloaded", timeout=90_000)

        print()
        print("=" * 72)
        print("  A Chrome window is open on the Looker Studio report.")
        print("  Sign in with the Google account that has EDIT access.")
        print()
        print("  This is a dedicated profile for this tool, separate from your")
        print("  everyday Chrome — so it starts signed out, and you only have")
        print("  to do this once.")
        print()
        print("  Looker Studio is slow: after sign-in it shows placeholder")
        print("  chart icons for 20-30 seconds before the real numbers appear.")
        print("  Wait for actual figures and country tables, not just the")
        print("  editor chrome around them, before confirming below.")
        print()
        print(f"  Target URL: {target}")
        print("=" * 72)
        await asyncio.get_running_loop().run_in_executor(
            None, input, "Press Enter once the report is visible with real numbers... "
        )

        if "accounts.google.com" in page.url:
            raise AuthError(
                f"Still on a Google sign-in page ({page.url[:90]}...). The sign-in did "
                "not complete — nothing was saved. Re-run and finish signing in first."
            )

        auth_file.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(auth_file))
        log.info("Saved storage state to %s", auth_file)
    finally:
        if page is not None:
            try:
                await page.close()
            except Exception:  # noqa: BLE001
                pass
        if browser is not None:
            try:
                await browser.close()  # detaches CDP; Chrome itself keeps running
            except Exception:  # noqa: BLE001
                pass
        _terminate(process)

    # Chrome has exited, so the profile on disk is consistent and safe to copy.
    # This is the only thing that can actually restore the session: Google binds
    # its session cookies to the browser instance (device-bound credentials), so
    # the cookies in auth.json CANNOT be replayed into another profile — tested,
    # they come back as "Signed out". A whole-profile snapshot restored to the
    # same path on the same machine is the real safety net.
    backup = backup_profile(profile_dir)

    print(f"\nSigned-in profile kept at {profile_dir}")
    if backup is not None:
        print(f"Backup of it taken at {backup}")
        print("If a run ever signs the profile out, restore with --restore-profile.")
    print(f"({auth_file} was also written, but it is a diagnostic record only —")
    print(" Google's session cookies are device-bound and cannot be replayed.)")
    print("Capture runs reuse the profile directly, so they never see a sign-in page.")


# ---------------------------------------------------------------------------
# Sessions for capture runs
# ---------------------------------------------------------------------------


def backup_path(profile_dir: Path) -> Path:
    profile_dir = profile_dir.expanduser()
    return profile_dir.with_name(profile_dir.name + "-backup")


def backup_profile(profile_dir: Path) -> Path | None:
    """Snapshot a signed-in profile so a bad run cannot cost the session.

    Only ever called with Chrome stopped — copying a live profile yields a
    Cookies database with uncommitted WAL data, which is exactly how an earlier
    attempt at this ended up in a signed-out state.
    """
    profile_dir = profile_dir.expanduser()
    if not profile_is_signed_in(profile_dir):
        log.debug("Not backing up %s: no Google session in it", profile_dir)
        return None
    target = backup_path(profile_dir)
    try:
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(profile_dir, target, symlinks=True, ignore_dangling_symlinks=True)
    except OSError as exc:
        log.warning("Could not back up the profile to %s: %s", target, exc)
        return None
    log.info("Backed up the signed-in profile to %s", target)
    return target


def restore_profile(profile_dir: Path) -> Path:
    """Put a backed-up profile back, replacing whatever is there now."""
    profile_dir = profile_dir.expanduser()
    source = backup_path(profile_dir)
    if not source.exists():
        raise AuthError(
            f"No profile backup at {source}. Nothing to restore — run with --login."
        )
    if cdp_reachable(DEFAULT_CDP_PORT):
        raise AuthError(
            "A Chrome with a debugging port is still running. Quit it before restoring, "
            "or the restored profile will be overwritten again."
        )
    shutil.rmtree(profile_dir, ignore_errors=True)
    shutil.copytree(source, profile_dir, symlinks=True, ignore_dangling_symlinks=True)
    log.info("Restored the profile at %s from %s", profile_dir, source)
    return profile_dir


# Google's session cookies. Presence of any one of these means a real signed-in
# session; the mere existence of a Cookies file does not, since Chrome creates
# one as soon as any page loads.
GOOGLE_AUTH_COOKIES = ("SID", "SSID", "HSID", "APISID", "SAPISID", "__Secure-1PSID")


def profile_is_signed_in(profile_dir: Path) -> bool:
    """Does this profile hold a real Google session?

    Checks for Google's session cookies by name only — the encrypted values are
    never read, and no decryption is attempted.
    """
    cookies_db = profile_dir.expanduser() / "Default" / "Cookies"
    if not cookies_db.exists():
        return False
    placeholders = ",".join("?" for _ in GOOGLE_AUTH_COOKIES)
    query = (
        f"SELECT COUNT(*) FROM cookies WHERE name IN ({placeholders}) "  # noqa: S608 - fixed-arity placeholders
        "AND host_key LIKE '%google.com'"
    )
    try:
        # Read-only, and immutable=1 so a lock held by a running Chrome cannot
        # block or be disturbed by this check.
        uri = f"file:{cookies_db}?mode=ro&immutable=1"
        with sqlite3.connect(uri, uri=True, timeout=2) as connection:
            (count,) = connection.execute(query, GOOGLE_AUTH_COOKIES).fetchone()
        return count > 0
    except sqlite3.Error as exc:
        log.debug("Could not inspect %s for a Google session: %s", cookies_db, exc)
        return False


async def open_session(
    playwright: Playwright,
    auth_file: Path,  # noqa: ARG001 - kept as a portable record, not used to authenticate
    headless: bool = True,
    scale: float = 2.0,
    viewport: dict | None = None,
    channel: str = DEFAULT_CHANNEL,  # noqa: ARG001 - real Chrome is launched directly
    profile_dir: Path | None = None,
    port: int = DEFAULT_CDP_PORT,
) -> Session:
    """Open a capture session on the dedicated signed-in profile.

    Chrome is launched as a plain subprocess and Playwright attaches over CDP,
    exactly as the login flow does. Letting Playwright launch the browser
    itself does NOT work here even with valid cookies in the profile: Google
    bounces the session straight to a sign-in page (observed with
    launch_persistent_context on this very profile). Attaching after launch
    keeps the session Google already trusts.

    Because the context comes from a browser we attached to, viewport and
    device scale cannot be set per-context — they go in as Chrome launch flags
    instead, and the per-page viewport is applied by the caller.
    """
    profile_dir = (profile_dir or DEFAULT_PROFILE_DIR).expanduser()
    if not profile_is_signed_in(profile_dir):
        raise AuthError(
            f"No signed-in Google session in {profile_dir}.\n"
            "Run with --login first — it opens a real Chrome window so you can sign in "
            "by hand (Google will not accept a sign-in performed through automation)."
        )

    box = viewport or DEFAULT_VIEWPORT
    process = launch_chrome(
        profile_dir,
        port,
        headless=headless,
        extra_args=[
            f"--force-device-scale-factor={scale}",
            f"--window-size={box['width']},{box['height']}",
            "--no-sandbox",
        ],
    )

    try:
        browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    except PlaywrightError as exc:
        _terminate(process)
        raise AuthError(f"Could not attach to the Chrome we just launched: {exc}") from exc

    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    context.set_default_timeout(30_000)
    log.info("Attached to Chrome on the signed-in profile at %s", profile_dir)
    return Session(context=context, browser=browser, process=process)


async def assert_authenticated(page: Page, auth_file: Path) -> None:
    """Fail loudly on an expired session instead of capturing empty pages."""
    url = page.url
    if "accounts.google.com" in url or "signin" in url.lower():
        raise AuthError(
            f"Redirected to a Google sign-in page ({url[:90]}...). The stored session "
            "has expired — re-run with --login."
        )
    if "/edit" not in url:
        raise AuthError(
            f"Landed on {url[:90]}... instead of an /edit URL. Either the account lacks "
            "edit access to this report, or Looker bounced the request."
        )
    try:
        body = await page.locator("body").inner_text(timeout=15_000)
    except Exception:  # noqa: BLE001 - a slow shell is not an auth failure
        return
    lowered = body.lower()
    for marker in ("you need access", "request access", "no tienes acceso", "solicitar acceso"):
        if marker in lowered:
            raise AuthError(
                f"Looker says the signed-in account has no access to this report "
                f"({marker!r} on the page). Use an account with edit access and re-run "
                "with --login."
            )
