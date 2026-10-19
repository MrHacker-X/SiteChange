#!/usr/bin/env python3
"""
SiteChange - Website Change Detector.

Author  : MrHacker-X
Repo    : https://github.com/MrHacker-X/sitechange
Version : 1.0.0
"""
from __future__ import annotations

import argparse
import sys

from core.config import load_defaults
from core.engine import *  # noqa: F401,F403
from core.utils import *  # noqa: F401,F403

_defaults = load_defaults()
__version__ = str(_defaults.get("version", "1.0.0"))
TOOL_DESC = str(_defaults.get("description", "One or more website URLs to snapshot or check for changes"))
TOOL_NAME = str(_defaults.get("name", "SiteChange"))


def register_subparser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "urls",
        nargs="*",
        help="One or more website URLs to snapshot or check for changes",
    )
    parser.add_argument(
        "-a",
        "--action",
        choices=["check", "snapshot", "history"],
        default="check",
        help="Action: check (snapshot & compare with previous), snapshot (capture baseline only), history (list saved snapshots)",
    )
    parser.add_argument(
        "-s",
        "--selector",
        help="Optional CSS selector to monitor a specific page element (e.g. 'main', '#pricing')",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        nargs="+",
        default=[],
        help="CSS selectors to exclude/ignore (e.g. '.timestamp' '#ad-banner')",
    )
    parser.add_argument(
        "-d",
        "--storage-dir",
        default="sitechange_snapshots",
        help="Directory to store snapshot history (default: ./sitechange_snapshots)",
    )
    parser.add_argument(
        "-e",
        "--export-diff",
        help="Export comparison diff to TXT, HTML, or JSON file path",
    )
    parser.add_argument(
        "--batch-config",
        help="JSON config file containing multiple pages to check in batch",
    )
    parser.add_argument(
        "--unattended",
        action="store_true",
        help="Automation mode: non-interactive execution; exits with code 2 if changes are detected",
    )
    parser.set_defaults(func=run_cli)


def run_cli(args: argparse.Namespace) -> int:
    if not getattr(args, "urls", None) and not getattr(args, "batch_config", None):
        if getattr(args, "unattended", False):
            print_error("Unattended mode requires at least one URL or --batch-config.")
            return 1
        run_interactive()
        return 0

    print_tool_header("SiteChange", "Website Change Detector", icon="🔍")

    try:
        if args.batch_config:
            cfg_path = Path(args.batch_config).expanduser().resolve()
            raw_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            pages = raw_cfg if isinstance(raw_cfg, list) else raw_cfg.get("pages", [])
            batch_res = batch_check_websites(pages, storage_dir=args.storage_dir)
            any_changed = False
            for snap, comp, err in batch_res:
                if err:
                    print_error(f"{snap.url}: {err}")
                elif comp is None:
                    print_info(f"{snap.url}: Initial baseline snapshot captured ({snap.snapshot_id}).")
                else:
                    display_comparison_summary(comp)
                    if comp.has_changes:
                        any_changed = True
            return 2 if (args.unattended and any_changed) else 0

        any_changed = False
        for url in args.urls:
            if args.action == "history":
                hist = list_snapshot_history(url, storage_dir=args.storage_dir)
                if not hist:
                    print_warning(f"No snapshots stored yet for {url}")
                else:
                    rows = [
                        (s.snapshot_id, s.timestamp, s.selector or "full-page", s.text_sha256[:12], s.html_sha256[:12])
                        for s in hist
                    ]
                    console.print(
                        make_table(
                            title=f"Snapshot History - {url}",
                            columns=[
                                ("Snapshot ID", "bold cyan"),
                                ("Timestamp", "white"),
                                ("Selector", "magenta"),
                                ("Text Hash", "green"),
                                ("HTML Hash", "yellow"),
                            ],
                            rows=rows,
                        )
                    )
            elif args.action == "snapshot":
                snap = capture_snapshot(
                    url,
                    storage_dir=args.storage_dir,
                    selector=args.selector,
                    ignore_selectors=args.ignore,
                )
                print_success(f"Snapshot {snap.snapshot_id} saved to {snap.snapshot_dir}")
            else:
                snap, comp = check_website_for_changes(
                    url,
                    storage_dir=args.storage_dir,
                    selector=args.selector,
                    ignore_selectors=args.ignore,
                )
                if comp is None:
                    print_success(
                        f"Initial baseline snapshot captured for {snap.url} (ID: {snap.snapshot_id}). Run check again later to compare."
                    )
                else:
                    display_comparison_summary(comp)
                    if comp.has_changes:
                        any_changed = True
                    if args.export_diff:
                        saved = export_diff_report(comp, args.export_diff)
                        print_success(f"Diff exported to {saved}")

        if args.unattended and any_changed:
            return 2
        return 0
    except Exception as exc:
        print_error(f"SiteChange failed: {exc}")
        return 1


def run_interactive() -> None:
    print_tool_header("SiteChange", "Website Change Detector", icon="🔍")
    while True:
        choice = prompt_menu(
            "Menu",
            [
                ("1", "Capture snapshot"),
                ("2", "Check for changes"),
                ("3", "Monitor CSS selector"),
                ("4", "Snapshot history"),
                ("5", "Compare snapshots"),
                ("6", "Batch check"),
                ("a", "About"),
            ],
        )
        if choice == "0":
            return
        if choice == "a":
            show_about_panel()
            console.input("[dim]Press Enter to return to the menu...[/dim]")
            continue

        storage_dir = "sitechange_snapshots"
        try:
            if choice == "6":
                raw_urls = prompt_text("Enter website URLs separated by commas")
                configs = [{"url": u.strip()} for u in raw_urls.split(",") if u.strip()]
                results = batch_check_websites(configs, storage_dir=storage_dir)
                for snap, comp, err in results:
                    if err:
                        print_error(f"{snap.url}: {err}")
                    elif comp is None:
                        print_success(f"{snap.url}: Baseline captured ({snap.snapshot_id})")
                    else:
                        display_comparison_summary(comp)
                continue

            url = prompt_text("Enter website URL")
            if choice == "1":
                snap = capture_snapshot(url, storage_dir=storage_dir)
                print_success(f"Captured HTML & Text snapshot {snap.snapshot_id} -> {snap.snapshot_dir}")
            elif choice in ("2", "3"):
                selector = None
                ignore: List[str] = []
                if choice == "3":
                    selector = prompt_text("CSS Selector to monitor (leave blank for entire page)", default="", required=False) or None
                    raw_ign = prompt_text("Ignore CSS selectors separated by commas (e.g. .ad,.clock)", default="", required=False)
                    ignore = [x.strip() for x in raw_ign.split(",") if x.strip()]
                snap, comp = check_website_for_changes(
                    url, storage_dir=storage_dir, selector=selector, ignore_selectors=ignore
                )
                if comp is None:
                    print_success(f"Baseline snapshot saved ({snap.snapshot_id}). Check again to compare!")
                else:
                    display_comparison_summary(comp)
                    if prompt_confirm("Export diff report (TXT / HTML / JSON)?", default=False):
                        out_p = prompt_text("Diff export path", default="site_diff.txt")
                        saved = export_diff_report(comp, out_p)
                        print_success(f"Saved diff to {saved}")
            elif choice == "4":
                hist = list_snapshot_history(url, storage_dir=storage_dir)
                if not hist:
                    print_warning("No snapshots recorded for this URL.")
                else:
                    rows = [(str(i), s.snapshot_id, s.timestamp, s.text_sha256[:12]) for i, s in enumerate(hist, 1)]
                    console.print(
                        make_table(
                            f"History for {url}",
                            [("#", "bold magenta"), ("Snapshot ID", "cyan"), ("Timestamp", "white"), ("Text Hash", "green")],
                            rows,
                        )
                    )
            elif choice == "5":
                hist = list_snapshot_history(url, storage_dir=storage_dir)
                if len(hist) < 2:
                    print_warning("At least 2 snapshots are needed to compare.")
                    continue
                comp = compare_snapshots(hist[-2], hist[-1])
                display_comparison_summary(comp)
                if prompt_confirm("Export diff report?", default=True):
                    out_p = prompt_text("Export path (.txt, .html, or .json)", default="diff_report.html")
                    saved = export_diff_report(comp, out_p)
                    print_success(f"Exported diff report to {saved}")
        except Exception as exc:
            print_error(f"SiteChange error: {exc}")



# ----------------------------------------------------------------------------
# CLI main
# ----------------------------------------------------------------------------



def build_arg_parser() -> argparse.ArgumentParser:
    """Build the standalone CLI parser for sitechange."""
    parser = argparse.ArgumentParser(
        prog="sitechange",
        description=TOOL_DESC,
        epilog=(
            "GitHub: https://github.com/MrHacker-X/sitechange - "
            "Run without flags to launch the interactive terminal menu."
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=TOOL_NAME + " " + __version__,
    )
    parser.add_argument(
        "-A",
        "--about",
        action="store_true",
        help="Show the About screen - overview, key features, version, author and contacts - and exit",
    )
    register_subparser(parser)
    return parser


def main(argv=None) -> int:
    """Entry point: parse flags and dispatch, or launch the interactive menu."""
    try:
        if argv is None:
            argv = sys.argv[1:]
        if not argv:
            # Plain `python sitechange.py` opens the interactive terminal menu.
            run_interactive()
            return 0
        parser = build_arg_parser()
        args = parser.parse_args(argv)
        if getattr(args, "about", False):
            show_about_panel()
            return 0
        func = getattr(args, "func", run_cli)
        result = func(args)
        return int(result) if isinstance(result, (int, float)) else 0
    except (KeyboardInterrupt, EOFError):
        return handle_keyboard_interrupt()


if __name__ == "__main__":
    raise SystemExit(main())
