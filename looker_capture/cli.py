"""Command line entry point."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click
from playwright.async_api import async_playwright

from . import auth, export, workbook
from .capture import Runner, Settings
from .config import (
    DEFAULT_PAGES,
    DEFAULT_PAUSE_SECONDS,
    DEFAULT_QUOTA_RETRIES,
    DEFAULT_SETTLE_SECONDS,
    LANDING_GROUPS,
    PAGES,
    REPORT_ID,
    Period,
    parse_cli_range,
    resolve_group,
)
from .netcapture import NetworkRecorder

log = logging.getLogger("looker_capture")


def setup_logging(output_dir: Path, verbose: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers.clear()

    file_handler = logging.FileHandler(output_dir / "run.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.addHandler(console)

    logging.getLogger("asyncio").setLevel(logging.WARNING)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--current-range", "current_range", default="", help="dd/mm/yyyy-dd/mm/yyyy")
@click.option("--prior-range", "prior_range", default="", help="dd/mm/yyyy-dd/mm/yyyy")
@click.option(
    "--pages",
    "pages_arg",
    default=None,
    help=f"Comma-separated page slugs. Default: all ({', '.join(DEFAULT_PAGES)})",
)
@click.option(
    "--landing-groups",
    "groups_arg",
    default=None,
    help="Comma-separated groups. Default: all, home, airport, route",
)
@click.option("--headless/--no-headless", default=True, show_default=True)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("output"),
    show_default=True,
)
@click.option("--auth-file", type=click.Path(path_type=Path), default=Path("auth.json"))
@click.option(
    "--login",
    is_flag=True,
    help=(
        "Sign in by hand, once, in a real Chrome window on this tool's own profile, "
        "then exit. Needed because Google will not render its sign-in form in a "
        "Playwright-launched browser, and Chrome refuses remote debugging on your "
        "everyday profile."
    ),
)
@click.option(
    "--chrome-profile-dir",
    type=click.Path(path_type=Path),
    default=auth.DEFAULT_PROFILE_DIR,
    show_default=True,
    help=(
        "Dedicated Chrome profile this tool signs into and reuses. Must NOT be your "
        "everyday Chrome profile: Chrome 136+ refuses to open a debugging port on the "
        "default profile directory."
    ),
)
@click.option(
    "--cdp-port",
    type=int,
    default=auth.DEFAULT_CDP_PORT,
    show_default=True,
    help="Remote-debugging port used during --login.",
)
@click.option(
    "--restore-profile",
    is_flag=True,
    help=(
        "Restore the Chrome profile from the backup taken at last --login, then exit. "
        "Use if a run left the profile signed out."
    ),
)
@click.option("--account-index", default=0, show_default=True, help="The /u/N/ Google account.")
@click.option(
    "--browser-channel",
    default=auth.DEFAULT_CHANNEL,
    show_default=True,
    help=(
        "Playwright browser channel for capture runs: chrome, chromium, msedge. "
        "Real Chrome is the default; Playwright's bundled Chromium can render Looker "
        "unreliably."
    ),
)
@click.option("--dry-run", is_flag=True, help="Navigate and verify the chips; capture nothing.")
@click.option("--settle-seconds", default=DEFAULT_SETTLE_SECONDS, show_default=True)
@click.option("--pause-seconds", default=DEFAULT_PAUSE_SECONDS, show_default=True)
@click.option("--quota-retries", default=DEFAULT_QUOTA_RETRIES, show_default=True)
@click.option("--scale", default=2.0, show_default=True, help="Device scale factor for screenshots.")
@click.option("--tile-margin", default=8, show_default=True)
@click.option("--network-capture/--no-network-capture", default=True, show_default=True)
@click.option("--emit-data-files/--no-emit-data-files", default=True, show_default=True)
@click.option(
    "--layout-map",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="JSON mapping of page slug -> {tile index: [channel, device]}.",
)
@click.option(
    "--build-xlsx/--no-build-xlsx",
    default=True,
    show_default=True,
    help=(
        "Build the final Suntransfers_Funnel_YoY_*.xlsx from the captured data "
        "(needs --emit-data-files, on by default). Off during --dry-run regardless."
    ),
)
@click.option(
    "--xlsx-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Where to write the .xlsx. Defaults to --output-dir.",
)
@click.option(
    "--merge/--no-merge",
    default=True,
    show_default=True,
    help=(
        "Fold this run's results into an existing data.json in --output-dir "
        "instead of replacing it, so re-capturing a few failed pages does not "
        "discard the ones that already succeeded. A failed re-capture never "
        "overwrites a good earlier result."
    ),
)
@click.option("-v", "--verbose", is_flag=True)
def main(  # noqa: PLR0913 - a CLI is allowed its knobs
    current_range: str,
    prior_range: str,
    pages_arg: str | None,
    groups_arg: str | None,
    headless: bool,
    output_dir: Path,
    auth_file: Path,
    login: bool,
    chrome_profile_dir: Path,
    cdp_port: int,
    restore_profile: bool,
    account_index: int,
    browser_channel: str,
    dry_run: bool,
    settle_seconds: float,
    pause_seconds: float,
    quota_retries: int,
    scale: float,
    tile_margin: int,
    network_capture: bool,
    emit_data_files: bool,
    layout_map: Path | None,
    build_xlsx: bool,
    xlsx_dir: Path | None,
    merge: bool,
    verbose: bool,
) -> None:
    """Capture the Suntransfers B2C funnel report out of Looker Studio."""
    setup_logging(output_dir, verbose)

    if restore_profile:
        try:
            restored = auth.restore_profile(chrome_profile_dir)
        except auth.AuthError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Restored {restored} from its backup.")
        click.echo(f"Signed in: {auth.profile_is_signed_in(restored)}")
        return

    if login:
        try:
            asyncio.run(_login(auth_file, account_index, chrome_profile_dir, cdp_port))
        except auth.AuthError as exc:
            raise click.ClickException(str(exc)) from exc
        return

    if not current_range or not prior_range:
        raise click.UsageError("--current-range and --prior-range are both required")

    try:
        periods = [
            parse_cli_range("current", current_range),
            parse_cli_range("prior", prior_range),
        ]
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    slugs = [s.strip() for s in pages_arg.split(",")] if pages_arg else DEFAULT_PAGES
    unknown = [s for s in slugs if s not in PAGES]
    if unknown:
        raise click.UsageError(
            f"Unknown page(s): {', '.join(unknown)}. Known: {', '.join(DEFAULT_PAGES)}"
        )
    pages = [PAGES[s] for s in slugs]

    try:
        groups = (
            [resolve_group(g) for g in groups_arg.split(",")] if groups_arg else LANDING_GROUPS
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    mapping = json.loads(layout_map.read_text(encoding="utf-8")) if layout_map else None

    settings = Settings(
        output_dir=output_dir,
        auth_file=auth_file,
        account=account_index,
        settle_seconds=settle_seconds,
        pause_seconds=pause_seconds,
        quota_retries=quota_retries,
        tile_margin=tile_margin,
        dry_run=dry_run,
        viewport=auth.DEFAULT_VIEWPORT,
    )

    combos = len(pages) * len(periods) * len(groups)
    log.info(
        "Starting %s: %d page(s) x %d period(s) x %d group(s) = %d combinations",
        "dry run" if dry_run else "capture",
        len(pages),
        len(periods),
        len(groups),
        combos,
    )

    # Written after every combination, so a crash mid-run keeps what already
    # succeeded. Merged against whatever was on disk before this run started.
    baseline = export.load_data_json(output_dir / "data.json") if merge else {}
    partial_meta = {
        "captured_at": "in progress",
        "report_id": REPORT_ID,
        "dry_run": dry_run,
        "periods": {
            p.name: {"start": p.start.isoformat(), "end": p.end.isoformat()} for p in periods
        },
        "landing_groups": groups,
        "settle_seconds": settle_seconds,
    }

    def checkpoint(partial: dict) -> None:
        combined = export.merge_results(baseline, partial) if baseline else partial
        export.write_data_json(combined, output_dir / "data.json", partial_meta, quiet=True)

    try:
        results = asyncio.run(
            _run(
                settings,
                pages,
                periods,
                groups,
                headless,
                scale,
                network_capture,
                browser_channel,
                chrome_profile_dir,
                cdp_port,
                checkpoint,
            )
        )
    except auth.AuthError as exc:
        raise click.ClickException(str(exc)) from exc

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if merge and baseline:
        before = sum(
            len(pd.get("groups", {}))
            for pg in baseline.values()
            for pd in pg.get("periods", {}).values()
        )
        results = export.merge_results(baseline, results)
        log.info("Merged into %d existing combination(s) from a previous run", before)

    meta = {
        "captured_at": stamp,
        "report_id": REPORT_ID,
        "dry_run": dry_run,
        "periods": {
            p.name: {"start": p.start.isoformat(), "end": p.end.isoformat()} for p in periods
        },
        "landing_groups": groups,
        "settle_seconds": settle_seconds,
    }
    export.write_data_json(results, output_dir / "data.json", meta)

    xlsx_path: Path | None = None
    if emit_data_files and not dry_run:
        by_name: dict[str, Period] = {p.name: p for p in periods}
        unmapped = export.write_workbook_files(
            results, by_name, output_dir / "workbook", stamp, REPORT_ID, mapping
        )
        if build_xlsx:
            try:
                xlsx_path = workbook.build_xlsx(
                    output_dir / "workbook",
                    by_name["current"],
                    by_name["prior"],
                    xlsx_dir or output_dir,
                    captured_at=stamp,
                )
            except workbook.WorkbookBuildError as exc:
                log.error("Could not build the .xlsx: %s", exc)
                click.echo(f"\nWorkbook build failed: {exc}\n", err=True)
            else:
                click.echo(f"\nWrote {xlsx_path}")
                if unmapped:
                    click.echo(
                        f"({len(unmapped)} tile(s) could not be attributed — see "
                        f"{output_dir / 'workbook' / 'UNMAPPED.md'} before trusting every number)"
                    )

    _summarise(results, dry_run)


async def _login(auth_file: Path, account: int, profile_dir: Path, cdp_port: int) -> None:
    async with async_playwright() as playwright:
        await auth.login(
            playwright, auth_file, account, profile_dir=profile_dir, port=cdp_port
        )


async def _run(
    settings: Settings,
    pages,
    periods,
    groups,
    headless: bool,
    scale: float,
    network_capture: bool,
    channel: str,
    profile_dir: Path,
    cdp_port: int,
    checkpoint=None,
):
    async with async_playwright() as playwright:
        session = await auth.open_session(
            playwright,
            settings.auth_file,
            headless=headless,
            scale=scale,
            channel=channel,
            profile_dir=profile_dir,
            port=cdp_port,
        )
        recorder = NetworkRecorder(enabled=network_capture and not settings.dry_run)
        runner = Runner(session.context, settings, recorder, checkpoint=checkpoint)
        try:
            return await runner.run(pages, periods, groups)
        finally:
            await session.close()


def _summarise(results: dict, dry_run: bool) -> None:
    counts: dict[str, int] = {}
    failures: list[str] = []
    for page_slug, page_data in results.items():
        for period_name, period_data in page_data.get("periods", {}).items():
            for group, combo in period_data.get("groups", {}).items():
                status = combo.get("status", "unknown")
                counts[status] = counts.get(status, 0) + 1
                if status not in ("ok",):
                    reason = "; ".join(combo.get("errors", [])) or combo.get(
                        "filter_note"
                    ) or combo.get("date_note") or "no reason recorded"
                    failures.append(f"  {page_slug}/{period_name}/{group}: {status} — {reason}")

    click.echo("")
    click.echo("Dry run finished." if dry_run else "Capture finished.")
    for status, count in sorted(counts.items()):
        click.echo(f"  {status}: {count}")
    if failures:
        click.echo("\nCombinations that did not verify cleanly:")
        for line in failures:
            click.echo(line)
    click.echo("\nFull detail in run.log and data.json.")


if __name__ == "__main__":
    main()
