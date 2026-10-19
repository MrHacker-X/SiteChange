#!/usr/bin/env python3
"""SiteChange core logic."""
from __future__ import annotations

from .config import load_tool_data

import argparse
import difflib
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from rich.panel import Panel
from rich.syntax import Syntax

from .utils import (
    console,
    make_table,
    print_error,
    print_info,
    print_success,
    print_tool_header,
    print_warning,
    prompt_confirm,
    prompt_menu,
    prompt_text,
    safe_filename,
)

def _load_tool_data(filename: str) -> dict:
    """Thin alias: load this tool's own config via core/config.py."""
    return load_tool_data(filename)


@dataclass
class WebsiteSnapshot:
    snapshot_id: str
    url: str
    timestamp: str
    selector: Optional[str]
    ignore_selectors: List[str]
    html_content: str
    text_content: str
    html_sha256: str
    text_sha256: str
    snapshot_dir: Optional[str] = None


@dataclass
class SnapshotComparison:
    url: str
    old_snapshot_id: str
    new_snapshot_id: str
    old_timestamp: str
    new_timestamp: str
    text_changed: bool
    html_changed: bool
    added_text_lines: List[str] = field(default_factory=list)
    removed_text_lines: List[str] = field(default_factory=list)
    modified_text_count: int = 0
    added_html_lines: int = 0
    removed_html_lines: int = 0
    unified_text_diff: List[str] = field(default_factory=list)
    unified_html_diff: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return self.text_changed or self.html_changed


TOOL_DATA = _load_tool_data("monitor_profile.json")
DEFAULT_HEADERS = {
    "User-Agent": TOOL_DATA.get("user_agent", "SiteChange/1.0"),
    "Accept": TOOL_DATA.get("accept", "text/html,*/*"),
}
NOISE_TAGS = list(TOOL_DATA.get("noise_tags_to_strip", ["script", "style", "noscript", "template"]))


def _url_slug(url: str) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.netloc}{parsed.path}".strip("/") or "site"
    slug = safe_filename(raw.replace("/", "_"), default="site")
    short_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:48]}_{short_hash}"


def process_webpage_dom(
    raw_html: str,
    selector: Optional[str] = None,
    ignore_selectors: Optional[Sequence[str]] = None,
) -> Tuple[str, str]:
    """Apply ignore rules and optional CSS element selector, returning (normalized_html, visible_text)."""
    soup = BeautifulSoup(raw_html, "html.parser")

    # Always remove script/style/noscript noise from visible text extraction
    # First remove user-specified ignore selectors from DOM
    for ign in ignore_selectors or []:
        ign_clean = ign.strip()
        if not ign_clean:
            continue
        try:
            for matched in soup.select(ign_clean):
                matched.decompose()
        except Exception:
            pass

    if selector and selector.strip():
        selected_nodes = soup.select(selector.strip())
        container = BeautifulSoup("<div></div>", "html.parser").div
        for node in selected_nodes:
            container.append(node)
        target_root = container
    else:
        target_root = soup.body if soup.body else soup

    normalized_html = target_root.prettify() if target_root else ""

    # Clone to strip scripts/styles before extracting visible text
    text_soup = BeautifulSoup(normalized_html, "html.parser")
    for tag in text_soup(NOISE_TAGS):
        tag.decompose()

    raw_lines = [line.strip() for line in text_soup.get_text(separator="\n").splitlines()]
    visible_lines = [line for line in raw_lines if line]
    visible_text = "\n".join(visible_lines)
    return (normalized_html, visible_text)


def capture_snapshot(
    url: str,
    storage_dir: Path | str = "sitechange_snapshots",
    selector: Optional[str] = None,
    ignore_selectors: Optional[Sequence[str]] = None,
    html_override: Optional[str] = None,
    timeout: int = 15,
    session: Optional[requests.Session] = None,
    save: bool = True,
) -> WebsiteSnapshot:
    """Fetch a webpage (or use html_override), extract HTML and visible text snapshots, and save to history."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if html_override is not None:
        raw_html = html_override
    else:
        sess = session or requests.Session()
        resp = sess.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.raise_for_status()
        raw_html = resp.text

    ign_list = [s.strip() for s in (ignore_selectors or []) if s.strip()]
    norm_html, norm_text = process_webpage_dom(raw_html, selector=selector, ignore_selectors=ign_list)

    now = datetime.now()
    snap_id = now.strftime("%Y%m%d_%H%M%S_%f")
    ts_iso = now.isoformat(timespec="seconds")
    html_hash = hashlib.sha256(norm_html.encode("utf-8")).hexdigest()
    text_hash = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()

    snap = WebsiteSnapshot(
        snapshot_id=snap_id,
        url=url,
        timestamp=ts_iso,
        selector=selector,
        ignore_selectors=ign_list,
        html_content=norm_html,
        text_content=norm_text,
        html_sha256=html_hash,
        text_sha256=text_hash,
    )

    if save:
        site_dir = Path(storage_dir).expanduser().resolve() / _url_slug(url)
        snap_folder = site_dir / snap_id
        snap_folder.mkdir(parents=True, exist_ok=True)
        (snap_folder / "snapshot.html").write_text(norm_html, encoding="utf-8")
        (snap_folder / "snapshot.txt").write_text(norm_text, encoding="utf-8")
        meta = {
            "snapshot_id": snap.snapshot_id,
            "url": snap.url,
            "timestamp": snap.timestamp,
            "selector": snap.selector,
            "ignore_selectors": snap.ignore_selectors,
            "html_sha256": snap.html_sha256,
            "text_sha256": snap.text_sha256,
        }
        (snap_folder / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        snap.snapshot_dir = str(snap_folder)

    return snap


def list_snapshot_history(url: str, storage_dir: Path | str = "sitechange_snapshots") -> List[WebsiteSnapshot]:
    """Load saved snapshots for a URL ordered chronologically (oldest to newest)."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    site_dir = Path(storage_dir).expanduser().resolve() / _url_slug(url)
    if not site_dir.is_dir():
        return []

    snapshots: List[WebsiteSnapshot] = []
    for sub in sorted(site_dir.iterdir()):
        if not sub.is_dir():
            continue
        meta_file = sub / "metadata.json"
        html_file = sub / "snapshot.html"
        txt_file = sub / "snapshot.txt"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            html_content = html_file.read_text(encoding="utf-8") if html_file.exists() else ""
            text_content = txt_file.read_text(encoding="utf-8") if txt_file.exists() else ""
            snapshots.append(
                WebsiteSnapshot(
                    snapshot_id=meta["snapshot_id"],
                    url=meta["url"],
                    timestamp=meta["timestamp"],
                    selector=meta.get("selector"),
                    ignore_selectors=meta.get("ignore_selectors", []),
                    html_content=html_content,
                    text_content=text_content,
                    html_sha256=meta.get("html_sha256", ""),
                    text_sha256=meta.get("text_sha256", ""),
                    snapshot_dir=str(sub),
                )
            )
        except Exception:
            pass
    return snapshots


def compare_snapshots(old_snap: WebsiteSnapshot, new_snap: WebsiteSnapshot) -> SnapshotComparison:
    """Compare two WebsiteSnapshot instances and compute text and HTML diffs."""
    old_text_lines = old_snap.text_content.splitlines()
    new_text_lines = new_snap.text_content.splitlines()

    old_html_lines = old_snap.html_content.splitlines()
    new_html_lines = new_snap.html_content.splitlines()

    text_diff = list(
        difflib.unified_diff(
            old_text_lines,
            new_text_lines,
            fromfile=f"text@{old_snap.snapshot_id}",
            tofile=f"text@{new_snap.snapshot_id}",
            lineterm="",
        )
    )
    html_diff = list(
        difflib.unified_diff(
            old_html_lines,
            new_html_lines,
            fromfile=f"html@{old_snap.snapshot_id}",
            tofile=f"html@{new_snap.snapshot_id}",
            lineterm="",
        )
    )

    added_txt: List[str] = []
    removed_txt: List[str] = []
    modified_txt_count = 0

    matcher = difflib.SequenceMatcher(None, old_text_lines, new_text_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added_txt.extend(new_text_lines[j1:j2])
        elif tag == "delete":
            removed_txt.extend(old_text_lines[i1:i2])
        elif tag == "replace":
            removed_txt.extend(old_text_lines[i1:i2])
            added_txt.extend(new_text_lines[j1:j2])
            modified_txt_count += max(i2 - i1, j2 - j1)

    added_html = sum(
        1 for line in html_diff if line.startswith("+") and not line.startswith("+++")
    )
    removed_html = sum(
        1 for line in html_diff if line.startswith("-") and not line.startswith("---")
    )

    return SnapshotComparison(
        url=new_snap.url,
        old_snapshot_id=old_snap.snapshot_id,
        new_snapshot_id=new_snap.snapshot_id,
        old_timestamp=old_snap.timestamp,
        new_timestamp=new_snap.timestamp,
        text_changed=(old_snap.text_sha256 != new_snap.text_sha256),
        html_changed=(old_snap.html_sha256 != new_snap.html_sha256),
        added_text_lines=added_txt,
        removed_text_lines=removed_txt,
        modified_text_count=modified_txt_count,
        added_html_lines=added_html,
        removed_html_lines=removed_html,
        unified_text_diff=text_diff,
        unified_html_diff=html_diff,
    )


def check_website_for_changes(
    url: str,
    storage_dir: Path | str = "sitechange_snapshots",
    selector: Optional[str] = None,
    ignore_selectors: Optional[Sequence[str]] = None,
    html_override: Optional[str] = None,
    timeout: int = 15,
    session: Optional[requests.Session] = None,
) -> Tuple[WebsiteSnapshot, Optional[SnapshotComparison]]:
    """Capture a new snapshot and compare it against the most recent previous snapshot if one exists."""
    history = list_snapshot_history(url, storage_dir=storage_dir)
    previous = history[-1] if history else None

    current = capture_snapshot(
        url=url,
        storage_dir=storage_dir,
        selector=selector,
        ignore_selectors=ignore_selectors,
        html_override=html_override,
        timeout=timeout,
        session=session,
        save=True,
    )

    if previous is None:
        return (current, None)

    comparison = compare_snapshots(previous, current)
    return (current, comparison)


def export_diff_report(
    comparison: SnapshotComparison,
    output_path: Path | str,
    fmt: Optional[str] = None,
) -> Path:
    """Export comparison diff results as TXT, HTML, or JSON."""
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    export_fmt = (fmt or out.suffix.lstrip(".") or "txt").lower()

    if export_fmt == "json":
        payload = asdict(comparison)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    elif export_fmt == "html":
        html_differ = difflib.HtmlDiff(wrapcolumn=90)
        old_lines = [
            line[1:]
            for line in comparison.unified_text_diff
            if not line.startswith(("+++", "---", "@@"))
        ]
        table_html = html_differ.make_file(
            comparison.removed_text_lines or ["(no removed lines)"],
            comparison.added_text_lines or ["(no added lines)"],
            fromdesc=f"Previous ({comparison.old_timestamp})",
            todesc=f"Current ({comparison.new_timestamp})",
        )
        out.write_text(table_html, encoding="utf-8")
    else:
        lines = [
            f"SiteChange Comparison Report - {comparison.url}",
            f"Previous Snapshot: {comparison.old_snapshot_id} ({comparison.old_timestamp})",
            f"Current Snapshot : {comparison.new_snapshot_id} ({comparison.new_timestamp})",
            f"Text Changed     : {comparison.text_changed} (+{len(comparison.added_text_lines)} / -{len(comparison.removed_text_lines)} / ~{comparison.modified_text_count} modified)",
            f"HTML Changed     : {comparison.html_changed} (+{comparison.added_html_lines} / -{comparison.removed_html_lines})",
            "=" * 80,
            "\n--- TEXT UNIFIED DIFF ---",
            "\n".join(comparison.unified_text_diff) or "(No visible text changes)",
            "\n--- HTML UNIFIED DIFF ---",
            "\n".join(comparison.unified_html_diff[:200]) or "(No HTML markup changes)",
        ]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def batch_check_websites(
    configs: Sequence[Dict[str, Any]],
    storage_dir: Path | str = "sitechange_snapshots",
    timeout: int = 15,
    session: Optional[requests.Session] = None,
) -> List[Tuple[WebsiteSnapshot, Optional[SnapshotComparison], Optional[str]]]:
    """Check multiple configured websites in one execution.

    Each config item can be {"url": "...", "selector": "...", "ignore": [...]}.
    Returns list of (snapshot, comparison_or_none, error_or_none).
    """
    results: List[Tuple[WebsiteSnapshot, Optional[SnapshotComparison], Optional[str]]] = []
    for item in configs:
        u = str(item.get("url", "")).strip()
        if not u:
            continue
        sel = item.get("selector")
        ign = item.get("ignore") or item.get("ignore_selectors") or []
        try:
            snap, comp = check_website_for_changes(
                url=u,
                storage_dir=storage_dir,
                selector=sel,
                ignore_selectors=ign,
                timeout=timeout,
                session=session,
            )
            results.append((snap, comp, None))
        except Exception as exc:
            dummy = WebsiteSnapshot(
                snapshot_id="error",
                url=u,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                selector=sel,
                ignore_selectors=list(ign),
                html_content="",
                text_content="",
                html_sha256="",
                text_sha256="",
            )
            results.append((dummy, None, str(exc)))
    return results


def display_comparison_summary(comp: SnapshotComparison) -> None:
    status_str = (
        "[bold yellow]CHANGES DETECTED[/bold yellow]"
        if comp.has_changes
        else "[bold green]NO CHANGES[/bold green]"
    )
    rows = [
        ("Website URL", comp.url),
        ("Overall Status", status_str),
        ("Previous Snapshot", f"{comp.old_snapshot_id} ({comp.old_timestamp})"),
        ("Current Snapshot", f"{comp.new_snapshot_id} ({comp.new_timestamp})"),
        (
            "Visible Text Changes",
            f"Changed: {comp.text_changed} | [green]+{len(comp.added_text_lines)} added[/green], [red]-{len(comp.removed_text_lines)} removed[/red], [yellow]~{comp.modified_text_count} modified[/yellow]",
        ),
        (
            "HTML Markup Changes",
            f"Changed: {comp.html_changed} | [green]+{comp.added_html_lines} lines[/green], [red]-{comp.removed_html_lines} lines[/red]",
        ),
    ]
    console.print()
    console.print(
        make_table(
            title=f"SiteChange Summary - {comp.url}",
            columns=[("Metric", "bold cyan"), ("Details", "white")],
            rows=rows,
        )
    )

    if comp.unified_text_diff:
        diff_preview = "\n".join(comp.unified_text_diff[:40])
        console.print(
            Panel(
                Syntax(diff_preview, "diff", theme="monokai", word_wrap=True),
                title="Visible Text Diff Preview",
                border_style="cyan",
            )
        )
