#!/usr/bin/env python3
"""SiteChange configuration constants (built-in, self-contained)."""
from __future__ import annotations

_CONFIGS: dict = {
    "defaults.json": {
        "tool": "sitechange",
        "name": "SiteChange",
        "subtitle": "Website Change Detector",
        "version": "1.0.0",
        "description": "One or more website URLs to snapshot or check for changes",
        "homepage": "https://github.com/MrHacker-X/sitechange",
        "author": "MrHacker-X",
        "email": "contact@vritrasec.com",
        "website": "https://vritrasec.com",
        "network": "https://link.vritrasec.com",
        "about_overview": (
            "SiteChange is a website change detector built around clean text extraction: it snapshots a page with boilerplate stripped, can focus on specific CSS selectors, and reports exactly what changed since the last capture - including unattended mode with CI-ready exit codes."
        ),
        "about_features": [
            "Snapshot history with boilerplate-free page text",
            "Change detection between any two captures",
            "CSS selector targeting and ignore lists",
            "Diff export to TXT, HTML or JSON",
            "Batch monitoring via a JSON config file",
            "Unattended mode: exit code 2 when changes are detected",
        ]
    },
    "monitor_profile.json": {
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 SiteChange/1.0",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "default_storage_dir": "sitechange_snapshots",
        "default_timeout": 15,
        "noise_tags_to_strip": [
            "script",
            "style",
            "noscript",
            "template"
        ]
    }
}


def load_tool_data(filename: str) -> dict:
    """Return the built-in configuration table stored under `filename`."""
    return dict(_CONFIGS.get(filename, {}))


def load_defaults() -> dict:
    """Return the tool identity / defaults configuration."""
    return dict(_CONFIGS.get("defaults.json", {}))
