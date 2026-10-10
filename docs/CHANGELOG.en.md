<!-- Language: English (current) | [简体中文](CHANGELOG.md) -->

[简体中文](CHANGELOG.md) | **English**

[← Back to Home](../README.en.md) · [📘 Usage Guide](USAGE.en.md) · [🛠 Build & Package](BUILD.en.md) · [📝 Changelog](CHANGELOG.en.md)

---

# Changelog

This file records version changes for MergeTool. The format is based on [Keep a Changelog](https://keepachangelog.com/),
and version numbers follow [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-10-10

### Added
- Full UI redesign based on Google Material Design 3, using official Material Symbols vector icons.
- Pill-shaped search box in the top-right corner, showing a 2px Google Blue border when focused.
- Drag-and-drop loading for files and folders, with automatic deduplication and automatic appending.
- Free switching between tree view and flat view.
- Tri-state checkbox for directories (checked / indeterminate / unchecked) with parent-child cascading.
- Regular expression filename filtering.
- Multi-encoding cascading detection (BOM → chardet → strict UTF-8 → strict GB18030 → latin-1 fallback).
- Background-thread scanning and merging, keeping the UI responsive at all times, with cancellation support.
- Output report containing complete metadata (generation time, root directory, encoding, size, etc.).

### Changed
- Migrated from customtkinter to PySide6.
- Output encoding is fixed to UTF-8-SIG to ensure compatibility with Windows Notepad.

### Fixed
- Fixed a defect where intermediate-level subfolders were not selected synchronously after checking a parent folder.
- Fixed the color fringing issue outside the rounded corners of dropdown menus and context menus.
- Fixed the issue where an orange dashed outline appeared during highlighting.

## [1.x.x] - Earlier Versions

Early versions based on customtkinter, with relatively simple functionality, are no longer maintained.