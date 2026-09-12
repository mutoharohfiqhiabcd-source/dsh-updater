# DeepSeek Harness Updater

> English overview. The full documentation is in Chinese:
> [README.md](README.md) · [源码版更新与GitHub同步说明.md](源码版更新与GitHub同步说明.md)

A small Windows desktop tool that manages **DeepSeek Harness** installations on
your machine: detect what is installed, compare against the official release,
scan plugins/skills, update in one click, and keep local data safe.

---

## Features

| Capability | Description |
|---|---|
| **Auto-detect** | Scans source checkouts, npm global installs and `.dsh` runtime profiles |
| **Version compare** | Source checkouts are compared against GitHub `master`; npm/profile against npm `latest` |
| **One-click update** | Source edition: download the official source zip → back up → replace the whole directory |
| **Local data kept** | `node_modules` and `.git` are preserved and moved back after the swap |
| **Plugin / skill scan** | Lists enabled plugins and skills under `.dsh\skills`, with sizes and install times |
| **Skill sync** | Runs `git pull --ff-only` for skills that have a `.git` directory |
| **Rollback** | Creates a `*.dsh-bak-<timestamp>` backup before updating; rolls back automatically on failure |
| **Multi-language** | 简体中文 / 繁體中文 / English / 日本語 / 한국어, auto-detected from the system language |
| **Detect-result cache** | Shows the previous scan result (with its timestamp) immediately on startup, then refreshes in the background |
| **Download source** | Opens an item's source (npm package page for plugins, git remote for skills) and remembers it for later update checks |

---

## Two editions

| | Source edition | EXE edition |
|---|---|---|
| How to start | Run `python updater_gui.pyw`, or double-click `启动更新器.bat` | Double-click `DeepSeekHarnessUpdater.exe` |
| Requirements | Python 3.10+ with tkinter | None |
| Best for | Reading/debugging the code, quick local tests | Handing to someone else |

Both are attached to every GitHub Release, together with `SHA256.txt` so you can
verify the download.

---

## Quick start

```bat
:: Source edition
python updater_gui.pyw

:: EXE edition — just double-click DeepSeekHarnessUpdater.exe
```

Requirements:

* **Updating DSH source:** DeepSeek Harness **must be closed** (the updater aborts
  if `127.0.0.1:3080` is in use).
* `pnpm` is optional — you can tick "run pnpm install after replacing" to sync
  dependencies.

---

## Where local data is stored

Everything lives in a single "player preferences"-style file:

```
%APPDATA%\dsh-updater\preferences.json
├─ settings   your preferences (language, GPU toggle)
├─ cache      the previous scan result + timestamp
└─ sources    download sources you have opened and remembered
```

The file is written atomically. If it is missing, corrupted or has an unexpected
shape, the tool silently falls back to defaults — a broken file never blocks
startup. Older versions kept three separate files
(`settings.json` / `cache.json` / `sources.json`); they are migrated
automatically on first read and **the old files are left in place**.

You can point the tool at another directory with the
`DSH_UPDATER_SETTINGS_DIR` environment variable (useful for portable or test runs).

---

## Language switching

* The UI language is detected from the system language on first launch and can be
  changed in **Preferences → Language**.
* The interface is rebuilt immediately after switching — **no restart needed**.
* Switching language does **not** trigger a rescan: the previous result is reused.

> **Note:** if some text is still shown in a different language after switching,
> press **"🔄 Rescan"** to refresh the display. This only affects a few
> long log/tooltip strings that are built while scanning.

---

## Known limitations

* A few multi-line log messages are not yet translated and still show Chinese.
* **"Use GPU acceleration"** only records a preference — DSH does not expose a GPU
  acceleration option yet, so it currently has no effect.

---

## Repository layout

| File | Purpose |
|---|---|
| `updater_core.py` | Detection / version compare / download / update / skill sync |
| `updater_gui.pyw` | The Tkinter GUI |
| `i18n.py` + `i18n_*.py` | Multi-language framework and translation tables |
| `pack_source.py` | Builds the source-edition zip (used locally and in CI) |
| `启动更新器.bat` | One-click launcher for the source edition |
| `.github/workflows/ci.yml` | Static checks + smoke tests on push |
| `.github/workflows/build-release.yml` | Builds the EXE and publishes a Release on `v*` tags |
| `RELEASE_NOTES.md` | Release notes for the current version (used as the Release body) |
