<!-- Language switch: Chinese | English (current) -->
[简体中文](USAGE.md) | **English**

[← Back to Home](../README.en.md) · [📘 Usage](USAGE.en.md) · [🛠 Build & Packaging](BUILD.en.md) · [📝 Changelog](CHANGELOG.en.md)

---

# MergeTool Usage Guide

This guide is for **end users**. It covers installation, the UI, the complete workflow, and FAQ.
If you want to build from source or package the app, see [🛠 Build & Packaging](BUILD.en.md).

---

## Table of Contents

- [1. What is MergeTool](#1-what-is-mergetool)
- [2. Install & Launch](#2-install--launch)
- [3. UI Overview](#3-ui-overview)
- [4. Complete Workflow](#4-complete-workflow)
- [5. Filtering Rules](#5-filtering-rules)
- [6. Selection Tips](#6-selection-tips)
- [7. Encoding Detection](#7-encoding-detection)
- [8. Output Format](#8-output-format)
- [9. FAQ](#9-faq)

---

## 1. What is MergeTool

MergeTool merges **many text files into a single report**. Typical use cases:

- Concatenate an entire project's source code into one file to feed to an LLM.
- Archive logs, configs, and docs into a single searchable text file.
- Produce a complete record of scattered files for review, submission, or code audit.

Key highlights:

- **Graphical directory tree** — tick files like in a file explorer.
- **Automatic encoding detection** — Chinese mojibake is essentially eliminated.
- **Metadata-rich output** — each file is tagged with absolute path, encoding, and size.

---

## 2. Install & Launch

### 2.1 End users (prebuilt exe)

1. Open the project's [Releases](https://github.com/liufeias/MergeTool/releases) page.
2. Download the latest `MergeTool-vX.Y.Z.zip`.
3. Extract to any directory (**avoid non-ASCII characters and spaces in the path**, e.g. `D:\Tools\MergeTool`).
4. Double-click `MergeTool.exe`.

> ⚠️ On first launch, Windows SmartScreen may show "Windows protected your PC". Click "More info" → "Run anyway".
> This is because the binary is unsigned, not because it is malicious.

### 2.2 Developers (from source)

Requires **Python 3.11 – 3.13** and **uv** (recommended) or pip.

```powershell
git clone https://github.com/liufeias/MergeTool.git
cd MergeTool
uv sync
uv run python -m merge_tool
```

See [🛠 Build & Packaging](BUILD.en.md) for full environment setup.

---

## 3. UI Overview

The main window has three regions:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Left settings panel (scrollable)  │   Right main card (file tree)   │
│  ─────────────────────────────    │   ────────────────────────────  │
│  ① Root directory [input][Browse]  │   [Loaded N][Checked N]         │
│  ② Extensions                      │            [🔍 Search]          │
│  ③ No-ext / Recurse checkboxes     │                                │
│  ④ Filename filter + regex         │   ┌─────────────────────────┐   │
│  ⑤ Read encoding [dropdown]        │   │  ☑ 📁 src               │   │
│  ⑥ Output file [Save As]           │   │    ☑ 📄 app.py    41 KB │   │
│  ⑦ Flat view                       │   │    ☐ 📄 main.py    2 KB │   │
│  ⑧ [Scan] [Apply Filter]           │   └─────────────────────────┘   │
│  ⑨ [Start Merge]   (mint green)    │                                │
│  ⑩ [Cancel Task]   (light red)     │                                │
└─────────────────────────────────────────────────────────────────────┘
│  Bottom status bar: progress bar + status text                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Control reference

| # | Control | Purpose |
| --- | --- | --- |
| ① | Root directory | Scan starting point. You can also drag & drop files/folders onto the window. |
| ② | Extensions | Comma-separated, e.g. `py,txt,md,json`. Empty = no limit. |
| ③ | Checkboxes | "Include no-extension" decides whether files without a suffix are included; "Recurse subfolders" controls depth. |
| ④ | Filename filter | Filter by filename. Tick "Use regex" to treat it as a regular expression. |
| ⑤ | Read encoding | "Auto detect" by default; you can force a specific encoding. |
| ⑥ | Output file | Where the merged result is written; defaults to `merged_content.txt`. |
| ⑦ | Flat view | Show all files in a flat list without hierarchy. |
| ⑧ | Scan / Apply Filter | Scan re-loads the tree; Apply Filter rescans with current conditions. |
| ⑨ | Start Merge | Write the checked files into the output file. |
| ⑩ | Cancel Task | Abort a running scan or merge. |

### File tree

- **Checkbox**: single click toggles state.
- **Folders**: checking a folder cascades to all its files; the folder itself is tri-state (☑ all / ◪ partial / ☐ none).
- **Expand/collapse**: click the left triangle, or **double-click the whole folder row**.
- **Right-click menu**: select all, invert, unselect all, expand all, collapse all, remove selected, clear list.
- **Search box**: live filename filtering (180 ms debounce).
- **Shortcuts**: `Delete` removes selected rows; `Space` toggles their checkbox state.

---

## 4. Complete Workflow

### Step 1 — Choose the data source

- Option A: click "Browse" and pick a root folder.
- Option B: **drag a folder or files onto the window**.
  - Folder: filled in as root directory and scanned automatically.
  - Files: appended as standalone entries (auto de-duplicated).
  - Both: the folder becomes the root; the files are appended.

### Step 2 — Configure filters

Example: merge only Python and Markdown files in a project:

1. Extensions: `py,md`.
2. Tick "Recurse subfolders".
3. Leave "Include no-extension" unticked.
4. Leave filename filter empty.

To exclude test files:

1. Filename filter: `^test_`.
2. Tick "Use regex".

### Step 3 — Scan

Click "Scan". Wait for the tree to load. The status bar reports progress in real time.

### Step 4 — Check files to merge

- Click individual checkboxes.
- Click a folder checkbox to cascade-select its contents.
- Use the right-click menu for "Select all / Invert / Unselect all".
- The top badges show "Loaded N / Checked N" live.

### Step 5 — Confirm output path

Defaults to `merged_content.txt` in the current directory. Click "Save As" to change it.

### Step 6 — Start merging

Click "Start Merge". If the output file already exists, a confirmation dialog appears.
Progress bar and status text update live.

A completion dialog reports success count, failure count, and the output path.

---

## 5. Filtering Rules

### 5.1 Extensions

| Input | Meaning |
| --- | --- |
| `py,txt,md` | only these three |
| `.py, .TXT` | leading dot and case are ignored; equals `py,txt` |
| empty | no extension limit (but "Include no-extension" still applies) |

### 5.2 Include no-extension

- Ticked: `Makefile`, `LICENSE`, `Dockerfile` etc. are included.
- Unticked: such files are skipped.

### 5.3 Recurse subfolders

- Ticked: traverse all subdirectories.
- Unticked: scan only the root level.

### 5.4 Filename filter

- Regex off: **case-insensitive substring** match.
- Regex on: **Python regex** applied to the filename (without path).

Examples:

| Goal | Regex |
| --- | --- |
| Starts with `test_` | `^test_` |
| Ends with `.bak` | `\.bak$` |
| Contains `config` or `settings` | `config\|settings` |
| Purely numeric name | `^\d+$` |

> ⚠️ During merge, the filename filter acts as a **second check**: scanning already filtered by extension, and merging re-checks by filename to ensure only final-condition files are written.

---

## 6. Selection Tips

- **Partial state**: a folder shows ◪ when only some of its files are checked.
- **Cascade rules**:
  - Checking a folder checks all descendants.
  - Unchecking a folder unchecks all descendants.
  - Unchecking a single file updates its ancestors to partial/unchecked.
- **Selected rows + Space**: batch toggle.
- **Right-click → Select checked rows only**: applies to currently highlighted rows.

---

## 7. Encoding Detection

MergeTool uses a cascading strategy:

1. **BOM** — most reliable; covers UTF-8-SIG / UTF-16 / UTF-32.
2. **chardet sampling** — reads first 256 KB, requires confidence > 0.7, then re-verifies with strict decoding on a longer sample.
3. **Strict UTF-8 probe** — if it passes, it's UTF-8.
4. **Strict GB18030 probe** — best coverage for legacy Chinese projects.
5. **latin-1 fallback** — 1 byte → 1 char, never fails.

### Manual override

The "Read encoding" dropdown offers:

- Auto detect (default, recommended)
- UTF-8 / UTF-8-SIG (with BOM)
- GB18030 (recommended for Chinese) / GBK / GB2312
- BIG5
- UTF-16 LE / UTF-16 BE / UTF-32
- Latin-1 / ASCII

> When to override? When you **know** the batch is a specific encoding and auto-detection is wrong.
> E.g. all files are BOM-less GBK — force "GBK" or "GB18030".

---

## 8. Output Format

The output is written as **UTF-8-SIG** (so Windows Notepad displays it correctly), with `\n` newlines.

```
======================================================================
文件内容合并工具 - 输出报告
======================================================================
生成时间: 2026-10-10 16:19:17
根目录: E:\MyPythonProgram\MergeTool
文件总数: 13
编码模式: 自动检测
扩展名筛选: （不限）
包含无扩展名文件: 否
递归搜索: 是
文件名筛选: （无）
使用正则: 否

--- 文件内容格式说明 ---
...

======================================================================
======================= 合并内容开始 =======================
======================================================================

文件绝对路径:  E:\MyPythonProgram\MergeTool\pyproject.toml
文件编码: utf-8 | 大小: 3.85 KB
----------------------------------------------------------------------
<original file content>

...

======================================================================
======================= 合并内容结束 =======================
======================================================================

成功合并文件数: 13
```

Each file block has a three-line header:

1. `文件绝对路径:  <absolute path>`
2. `文件编码: <encoding used> | 大小: <human-readable size>`
3. `----------------------------------------------------------------------`

followed by the raw content and a trailing blank line.

> Note: the report header and per-file labels are intentionally kept in Chinese,
> matching the tool's UI language. The content itself is preserved verbatim.

---

## 9. FAQ

### Q1: Dragging files does nothing?

- Make sure you drag **local files/folders**, not web links or files inside an archive.
- Some admin-elevated apps (e.g. 7-Zip in admin mode) have drag blocked by Windows UIPI.
- Fall back to the "Browse" button.

### Q2: Chinese text is garbled after merging?

- Determine the true source encoding and set "Read encoding" manually.
- If the batch is GBK, "GB18030 (recommended for Chinese)" is safest.
- The output itself is UTF-8-SIG; VSCode / Notepad++ will render it fine.

### Q3: The output is too large?

- Narrow the scope with extension and filename filters.
- Split into batches (e.g. per subdirectory).
- Avoid merging binaries (this tool targets text; binaries get latin-1 fallback and appear garbled).

### Q4: Why are some files under a checked folder not merged?

Check:

1. Extension filter excluded them.
2. "Include no-extension" is off and they have no suffix.
3. Filename filter (or regex) doesn't match.
4. They were manually removed after scanning.

### Q5: The app freezes?

- Scanning huge trees (hundreds of thousands of files) takes time, but the UI is not truly frozen — the status bar keeps updating.
- If it really hangs, click "Cancel Task".
- As a last resort, kill the process and narrow the root directory.

### Q6: Can it merge binaries?

Not recommended. MergeTool targets **text files**; binary content is force-decoded into garbage.
Use zip / 7z for binaries.

### Q7: Does the output path support non-ASCII characters?

Yes. But keep the **app's own directory** ASCII and space-free to avoid rare path issues.

### Q8: Why is the packaged exe so large?

PySide6 is large by nature. This project's `MergeTool.spec` excludes
QtWebEngine, Qt3D, QtCharts, QtQuick, etc., bringing the artifact down to ~80–150 MB.
See [🛠 Build & Packaging](BUILD.en.md) for details.

---

## 🧭 Related Documents

- [← Back to Home](../README.en.md)
- [🛠 Build & Packaging](BUILD.en.md) — env setup, debugging, PyInstaller
- [📝 Changelog](CHANGELOG.en.md) — version history
- [中文版](USAGE.md)

---

Feel free to open an Issue on GitHub for questions or suggestions.