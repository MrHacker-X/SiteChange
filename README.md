<div align="center">

# ⃤ S I T E C H A N G E ⃤

### *Detect what changed on a website - one command.*

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![OS](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Stars](https://img.shields.io/github/stars/MrHacker-X/sitechange?style=flat-square&color=orange)
![Forks](https://img.shields.io/github/forks/MrHacker-X/sitechange?style=flat-square&color=cyan)

</div>

---

## 📋 Table of Contents

- [🎯 Why SiteChange?](#-why-sitechange)
- [🧭 What It Does](#-what-it-does)
- [🚀 Quick Start](#-quick-start)
- [🖼️ Preview](#-preview)
- [📦 Installation](#-installation)
- [✨ Features](#-features)
- [⌨️ Usage](#%EF%B8%8F-usage)
- [⚙️ Configuration](#%EF%B8%8F-configuration)
- [🧰 Tech Stack](#-tech-stack)
- [⚠️ Disclaimer](#%EF%B8%8F-disclaimer)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)
- [👨‍💻 Developer](#-developer)

---

## 🎯 Why SiteChange?

> Waiting for a price drop, a signup to open, or a doc page to update shouldn't mean hitting refresh all day. **SiteChange watches it for you in two commands**: take a snapshot of a page today, compare it tomorrow, and get exactly what changed - text, structure, and raw diff - without a browser, a cron service, or a build step.
>
> **It's built for precise, local monitoring.** Snapshots strip noise (scripts, styles, ads) before comparing, so you see real content changes instead of tracking scripts.

---

## 🧭 What It Does

| # | Task | What it gives you |
|---|------|-------------------|
| 1️⃣ | Snapshot & check a page | Cleaned page text saved to `sitechange_snapshots/`, compared against the previous capture |
| 2️⃣ | Target specific elements | CSS selectors to watch (`#pricing`, `main`) and selectors to ignore (`.timestamp`, `#ad-banner`) |
| 3️⃣ | Batch monitoring | A JSON config checking many pages in one run, with unattended/CI exit codes |
| 4️⃣ | Export the diff | Save the full change report as TXT/HTML/JSON for records or CI |

---

## 🚀 Quick Start

```bash
git clone https://github.com/MrHacker-X/sitechange.git
cd sitechange
pip install -r requirements.txt
python sitechange.py                 # interactive menu
```

---

## 🖼️ Preview

<div align="center">

![SiteChange Preview](https://i.ibb.co/5XynLTWV/sitechange.png)

</div>

---

## 📦 Installation

```bash
# 1. clone
git clone https://github.com/MrHacker-X/sitechange.git
cd sitechange

# 2. install dependencies
pip install -r requirements.txt

# 3. run
python sitechange.py
```

### Supported Systems

| OS | Status | Notes |
|----|--------|-------|
| 🐧 Linux | ✅ Fully supported | Any distro with Python 3.8+ |
| 🪟 Windows | ✅ Fully supported | Python from python.org, then the steps above |
| 🍎 macOS | ✅ Fully supported | `brew install python`, then the steps above |
| 📱 Termux (Android) | ✅ Fully supported | `pkg install python`, then the steps above |

> 💡 Snapshots are cleaned before storage - scripts, styles, and ads are stripped so diffs contain real content changes, not tracking noise.

---

## ✨ Features

| | Feature | Description |
|---|---------|-------------|
| 📸 | **Noise-free snapshots** | `<script>`, `<style>`, `<noscript>`, and ad trails are stripped before storing text |
| 🔍 | **Real diff detection** | Line-level comparison showing added / removed / modified text between snapshots |
| 🕒 | **Timestamped history** | Every snapshot is dated so you can diff any two points in time |
| 📄 | **Exportable reports** | Save change reports as JSON/text for records, CI, or notification hooks |
| 🎛️ | **Two modes** | A guided interactive menu or a fully flag-driven direct CLI |
| 🛡️ | **Browser-like requests** | Sends a real User-Agent so bot-hostile CDNs don't serve you a block page |
| 🧱 | **Graceful failures** | A down or redirected page produces one clear message, not a broken snapshot |
| 🪶 | **Minimal dependencies** | `requests` + `beautifulsoup4` + `rich`, nothing else |

---

## ⌨️ Usage

```bash
python sitechange.py                 # interactive menu
python sitechange.py -h              # help
python sitechange.py -v              # version
```

### Direct CLI

```bash
# check a page now (baselines the first run, diffs every run after)
python sitechange.py https://example.com/pricing

# capture a baseline only, or watch just a page section
python sitechange.py https://example.com/pricing -a snapshot
python sitechange.py https://example.com/pricing -s "#pricing" -i ".timestamp"

# export the diff and run unattended (exit 2 when changes detected, for CI)
python sitechange.py https://example.com/pricing -e changes.json --unattended
```

| Option | Values / Example | Meaning |
|--------|------------------|---------|
| `urls` | one or more (positional) | Pages to snapshot or check |
| `-a` / `--action` | `check` / `snapshot` / `history` | Operation (default `check`) |
| `-s` / `--selector` | CSS selector | Watch a specific element instead of the whole page |
| `-i` / `--ignore` | CSS selectors | Elements excluded from the comparison |
| `-d` / `--storage-dir` | directory (default `sitechange_snapshots/`) | Where snapshots are stored |
| `-e` / `--export-diff` | a filename | Save the diff (extension decides format) |
| `--batch-config` | a JSON file | Check many pages in one run |
| `--unattended` | flag | Non-interactive mode; exits 2 on detected changes |

---

## ⚙️ Configuration

Detection behavior lives in [`core/config.py`](core/config.py):

| Setting | Default | Effect |
|---------|---------|--------|
| Noise tags | `script`, `style`, `noscript`, … | DOM elements stripped before comparison |
| Request headers | browser-like User-Agent | Keeps CDNs from serving a block page |
| Default timeout | short | Seconds each page fetch waits before giving up |
| Storage root | `sitechange_snapshots/` | Where snapshots and metadata are kept |

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.8+ |
| HTTP | `requests` (page fetching) |
| Parsing | `beautifulsoup4` (DOM cleaning & text extraction) |
| Diffing | Python standard library `difflib` |
| UI | `rich` (menus, colored tables, prompts) |

---

## ⚠️ Disclaimer

> ### Read this before using SiteChange.
>
> 1. **Watch pages you're allowed to.** Monitoring sites you don't control should respect their terms of service and robots.txt. Keep your polling frequency reasonable - SiteChange doesn't enforce rate limits on your behalf.
> 2. **Rendering differences aren't errors.** JavaScript-rendered pages, geo/AB variants, and dynamic content can produce false diffs. Snapshot a stable page or expect some noise.
> 3. **Snapshots store page content locally.** Saved text is a copy of a possibly copyrighted page - keep it for personal/monitoring use and don't republish it.
> 4. **No warranty.** SiteChange is provided "as is", with no warranty of any kind. The author is **not liable** for misuse or missed changes from using this tool.

---

## 🤝 Contributing

Contributions are welcome!

```bash
# 1. fork it
# 2. create your branch
git checkout -b feature/amazing-feature
# 3. commit
git commit -m "Add amazing feature"
# 4. push
git push origin feature/amazing-feature
# 5. open a Pull Request
```

---

## 📜 License

SiteChange is the original project by MrHacker-X - see the [`LICENSE`](https://github.com/MrHacker-X/sitechange) file in the upstream repository for details.

---

## 👨‍💻 Developer

| | |
|---|---|
| **Dev** | MrHacker-X |
| **GitHub** | [github.com/MrHacker-X](https://github.com/MrHacker-X) |
| **Email** | [contact@vritrasec.com](mailto:contact@vritrasec.com) |
| **Website** | [vritrasec.com](https://vritrasec.com) |
| **Network** | [link.vritrasec.com](https://link.vritrasec.com) |

---

<div align="center">

### ⭐ Star the repo if SiteChange kept you ahead of the changes ⭐

*Built by MrHacker-X - snapshot responsibly, monitor politely.*

</div>
