<!-- Language switch: Chinese | English (current) -->
[简体中文](BUILD.md) | **English**

[← Back to Home](../README.en.md) · [📘 Usage](USAGE.en.md) · [🛠 Build & Packaging](BUILD.en.md) · [📝 Changelog](CHANGELOG.en.md)

---

# MergeTool Build & Packaging Guide

For **developers**: environment setup, debugging, testing, and packaging.
End users should read [📘 Usage](USAGE.en.md).

---

## Table of Contents

- [1. Requirements](#1-requirements)
- [2. Clone & Dependencies](#2-clone--dependencies)
- [3. Project Structure](#3-project-structure)
- [4. Development & Debugging](#4-development--debugging)
- [5. Dependencies](#5-dependencies)
- [6. PyInstaller Packaging](#6-pyinstaller-packaging)
- [7. Size Optimization](#7-size-optimization)
- [8. Release Process](#8-release-process)
- [9. Troubleshooting](#9-troubleshooting)

---

## 1. Requirements

| Item | Requirement |
| --- | --- |
| OS | Windows 10 / 11 (the packaging target) |
| Python | **3.11 – 3.13** (`requires-python = ">=3.11,<3.14"`) |
| Package manager | [uv](https://github.com/astral-sh/uv) (strongly recommended) or pip |
| Build tool | PyInstaller ≥ 6.0 (declared as dev dependency) |
| Disk space | ≥ 2 GB recommended (PySide6 is large) |

> Why uv? This project's `pyproject.toml` uses `uv_build` as the backend.
> `uv sync` reproduces exact dependency versions from `uv.lock`, far faster than pip.

### Install uv

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version
```

---

## 2. Clone & Dependencies

```powershell
git clone https://github.com/liufeias/MergeTool.git
cd MergeTool

# Install runtime + dev dependencies (includes pyinstaller)
uv sync

# Verify
uv run python -c "import PySide6, chardet; print('OK')"
```

### Common uv commands

| Command | Purpose |
| --- | --- |
| `uv sync` | Install/sync all deps from `uv.lock` |
| `uv sync --no-dev` | Runtime deps only |
| `uv add <pkg>` | Add a runtime dep and update the lockfile |
| `uv add --dev <pkg>` | Add a dev dep |
| `uv remove <pkg>` | Remove a dep |
| `uv lock` | Update the lockfile only |
| `uv run <cmd>` | Run a command in the project venv |

### Using pip (optional)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install pyinstaller
```

---

## 3. Project Structure

```
MergeTool/
├── src/merge_tool/              # Source package (src layout)
│   ├── __init__.py              # Package entry, __version__
│   ├── __main__.py              # `python -m merge_tool` entry → app.main()
│   ├── app.py                   # Main window, UI, event dispatch (largest file)
│   ├── constants.py             # Constants, M3 palette, SVG icons, QSS, ENCODING_MAP
│   ├── encoding_utils.py        # Encoding detection & safe reading
│   ├── file_utils.py            # Path/size/extension helpers
│   ├── tree_model.py            # Tree model (tri-state, add/remove, prune)
│   ├── tree_view.py             # QTreeWidget wrapper + custom delegate
│   └── workers.py               # Background threads: scan_worker / merge_worker
├── assets/                      # Icons and static resources (optional)
├── docs/                        # Documentation
├── pyproject.toml               # PEP 621 metadata + uv_build config
├── uv.lock                      # uv lockfile
├── MergeTool.spec               # PyInstaller spec
└── README.en.md
```

### Module responsibilities

| Module | Responsibility | Highlights |
| --- | --- | --- |
| `app.py` | Main window & orchestration | `MergeToolApp`, `M3SearchBox`, `M3SelectButton`, drag-drop event filter |
| `constants.py` | Global constants & theme | `GLOBAL_M3_STYLESHEET`, `ENCODING_MAP`, SVG strings |
| `encoding_utils.py` | Encoding detection | `detect_encoding`, `read_file_safely`, multi-level fallback |
| `file_utils.py` | Helpers | `human_size`, `normalize_ext_set`, `parse_drop_paths` |
| `tree_model.py` | Data model | `Node`, `TreeModel`, `CheckState` tri-state |
| `tree_view.py` | View | `M3TreeItemDelegate`, `NoFocusProxyStyle`, context menu |
| `workers.py` | Background threads | `scan_worker`, `merge_worker`, queue-based UI messaging |

---

## 4. Development & Debugging

### 4.1 Run

```powershell
uv run python -m merge_tool
# or
uv run merge-tool
```

### 4.2 Debugging tips

- **Show console**: `console=False` in `MergeTool.spec`. Temporarily set it to `True`,
  or run from source (which shows a console by default).
- **Tracebacks**: `disable_windowed_traceback=False` in `app.py`, so packaged builds
  show the traceback in a dialog on unhandled exceptions.
- **Print debugging**: background threads post via `ui_queue.put(("status", (text, color)))`.
  Add temporary `print` in `_handle_worker_message` to observe.

### 4.3 Code style

ruff is configured in `pyproject.toml`:

```powershell
uv run ruff check src
uv run ruff format src
```

Ruleset: `E, F, W, I, N, UP, B, C4, SIM`, ignoring `E501`.

---

## 5. Dependencies

### Runtime

| Package | Version | Purpose |
| --- | --- | --- |
| `pyside6` | ≥ 6.12.0 | Qt for Python GUI framework |
| `chardet` | ≥ 5.2.0 | Character encoding detection |

### Development

| Package | Purpose |
| --- | --- |
| `pyinstaller` | Build the exe |

### PySide6 submodules used

- `QtCore` — signals, events, QTimer, QSize, QEvent
- `QtGui` — QIcon, QPixmap, QPainter, QDragEnterEvent
- `QtWidgets` — all widgets
- `QtSvg` — `QSvgRenderer` for SVG icons
- `QtSvgWidgets` — fallback

**Unused but pulled in by default** (excluded in the spec):
QtWebEngine, QtPdf, Qt3D, QtCharts, QtQuick/Qml, QtMultimedia, QtSql, QtTest, QtDesigner, QtHelp, etc.

---

## 6. PyInstaller Packaging

### 6.1 One-shot build

From the project root `E:\MyPythonProgram\MergeTool`:

```powershell
# 1. Clean old artifacts
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# 2. Build (reads MergeTool.spec)
uv run pyinstaller MergeTool.spec --noconfirm --clean

# 3. Test
.\dist\MergeTool\MergeTool.exe

# 4. Zip for release
Compress-Archive -Path .\dist\MergeTool `
                 -DestinationPath .\dist\MergeTool-v2.0.0.zip -Force
```

Artifact layout (onedir):

```
dist/
├── MergeTool/
│   ├── MergeTool.exe          # main executable
│   └── _internal/             # deps (Qt DLLs, Python runtime, assets)
└── MergeTool-v2.0.0.zip       # release archive
```

### 6.2 MergeTool.spec explained

```python
PROJECT_ROOT = os.path.abspath(SPECPATH)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
ICON_FILE = os.path.join(ASSETS_DIR, "icon.ico")
ENTRY_SCRIPT = os.path.join(SRC_DIR, "merge_tool", "__main__.py")

datas = []
if os.path.isdir(ASSETS_DIR):
    datas.append((ASSETS_DIR, "assets"))

hiddenimports = [
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    # chardet dynamically loads its probers at runtime
    "chardet", "chardet.universaldetector", ...
]

excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", ...
    "numpy", "scipy", "pandas", "matplotlib",
    "tkinter", "PyQt5", "PyQt6", ...
]

a = Analysis([ENTRY_SCRIPT], pathex=[SRC_DIR],
             binaries=[], datas=datas, hiddenimports=hiddenimports,
             excludes=excludes, noarchive=False, optimize=1)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name="MergeTool", console=False, upx=False,
          icon=ICON_FILE if os.path.exists(ICON_FILE) else None)
coll = COLLECT(exe, a.binaries, a.datas, name="MergeTool")
```

### 6.3 Key settings

| Setting | Value | Reason |
| --- | --- | --- |
| Mode | **onedir** | Fast startup (no per-run extraction), manageable size, fewer AV false positives |
| `pathex` | `[SRC_DIR]` | Lets PyInstaller find the `src/merge_tool` package |
| `console` | `False` | GUI app |
| `upx` | `False` | Avoid UPX-induced AV false positives |
| `optimize` | `1` | Strip asserts, keep docstrings |
| `hiddenimports` | chardet submodules | chardet imports probers dynamically |
| `excludes` | QtWebEngine etc. | Cuts size from 500 MB+ to 80–150 MB |
| `icon` | `assets/icon.ico` | Falls back to default when missing |

### 6.4 Custom icon

1. Prepare an `.ico` with 16/32/48/256 sizes.
2. Place it at `assets/icon.ico`.
3. The spec auto-uses it.
4. Rebuild.

### 6.5 Locating bundled assets

`assets/` is packed into `_internal/assets/`. Locate it via `sys._MEIPASS`:

```python
import sys, os
if getattr(sys, "frozen", False):
    base = sys._MEIPASS
else:
    base = os.path.dirname(os.path.abspath(__file__))
asset_path = os.path.join(base, "assets", "icon.ico")
```

---

## 7. Size Optimization

A full PySide6 install is **500 MB+**, dominated by QtWebEngine (~131 MB).
The spec excludes:

| Excluded | Approx. saving | Note |
| --- | --- | --- |
| QtWebEngine suite | ~131 MB | No browser engine needed |
| QtQuick / Qml | large | Project uses QtWidgets, not QML |
| Qt3D | large | No 3D |
| QtCharts / DataVisualization | medium | No charts |
| QtMultimedia | medium | No audio/video |
| QtPdf | ~3 MB | No PDF |
| QtSql / QtTest / QtDesigner / QtHelp | medium | Not needed at runtime |
| numpy / scipy / pandas / matplotlib | large | No scientific computing |
| tkinter / PyQt5 / PyQt6 / wx | medium | Avoid mixing GUI frameworks |

**Must keep**:

- `shiboken6` — PySide6's core binding engine. **Never exclude.**
- `QtSvg` — used by `QSvgRenderer` for vector icons.
- `chardet` and all its prober submodules.

Final size: **80–150 MB** depending on the PySide6 version.

---

## 8. Release Process

### 8.1 Version bookkeeping

Keep the version in sync across:

1. `pyproject.toml` → `[project] version = "2.0.0"`
2. `src/merge_tool/__init__.py` → `__version__ = "2.0.0"`
3. `MergeTool.spec` comments / zip name (optional)

### 8.2 Full release

```powershell
# 1. Bump version (three places)
# 2. Update docs/CHANGELOG.md and docs/CHANGELOG.en.md
# 3. Commit
git add .
git commit -m "chore: release v2.0.0"
git tag v2.0.0
git push origin main --tags

# 4. Clean & build
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
uv run pyinstaller MergeTool.spec --noconfirm --clean

# 5. Test
.\dist\MergeTool\MergeTool.exe

# 6. Zip
Compress-Archive -Path .\dist\MergeTool `
                 -DestinationPath .\dist\MergeTool-v2.0.0.zip -Force
```

7. On GitHub → Releases → Draft a new release:
   - Tag: `v2.0.0`
   - Title: `MergeTool v2.0.0`
   - Description: excerpt from CHANGELOG
   - Upload `MergeTool-v2.0.0.zip`

### 8.3 Optional CI automation

Add `.github/workflows/build.yml`:

```yaml
name: Build
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run pyinstaller MergeTool.spec --noconfirm --clean
      - run: Compress-Archive -Path .\dist\MergeTool -DestinationPath .\dist\MergeTool.zip -Force
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/MergeTool.zip
```

---

## 9. Troubleshooting

### Q1: `ModuleNotFoundError: No module named 'merge_tool'`

**Cause**: PyInstaller can't find the src-layout package.

**Fix**: Ensure `pathex=[SRC_DIR]` in the spec and `SRC_DIR` points to `<root>/src`.

### Q2: Packaged app raises `ImportError: chardet.xxx`

**Cause**: chardet loads probers dynamically; static analysis misses them.

**Fix**: Ensure all `chardet.*` submodules are in `hiddenimports` (the project already lists them).

### Q3: Icons missing after packaging

**Cause**: `assets/` not bundled, or `QtSvg` mistakenly excluded.

**Fix**:

1. Ensure `assets/` exists and is in `datas`.
2. Ensure `PySide6.QtSvg` is **not** in `excludes`.

### Q4: exe is still huge

**Check**:

- You used `MergeTool.spec` (not `pyinstaller -F app.py`).
- `excludes` took effect (search the build log for `Excluded module`).
- numpy/pandas etc. weren't accidentally pulled in.

### Q5: Antivirus flags the exe

**Cause**: PyInstaller bootloader + unsigned exe often triggers false positives.

**Mitigation**:

- `upx=False` in the spec (already set).
- Document it for users, or buy a code-signing certificate.

### Q6: `Remove-Item` says build/dist doesn't exist

Normal. `-ErrorAction SilentlyContinue` silences it.

### Q7: Build fails after a PySide6 upgrade

Major PySide6 upgrades may rename modules. Verify the module names in `excludes`
and update PyInstaller + `pyinstaller-hooks-contrib` if needed.

---

## 🧭 Related Documents

- [← Back to Home](../README.en.md)
- [📘 Usage](USAGE.en.md) — for end users
- [📝 Changelog](CHANGELOG.en.md) — version history
- [中文版](BUILD.md)

---

Feel free to open an Issue on GitHub for questions or suggestions.