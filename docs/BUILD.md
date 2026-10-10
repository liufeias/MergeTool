<!-- 语言切换：简体中文（当前） | 英文版 -->
**简体中文** | [English](BUILD.en.md)

[← 返回首页](../README.md) · [📘 使用帮助](USAGE.md) · [🛠 开发构建打包](BUILD.md) · [📝 更新日志](CHANGELOG.md)

---

# MergeTool 开发构建打包指南

本文档面向**开发者**，介绍如何从源码搭建环境、调试、测试与打包发布。
普通用户请阅读 [📘 使用帮助](USAGE.md)。

---

## 目录

- [1. 环境要求](#1-环境要求)
- [2. 克隆与依赖管理](#2-克隆与依赖管理)
- [3. 项目结构](#3-项目结构)
- [4. 开发与调试](#4-开发与调试)
- [5. 依赖说明](#5-依赖说明)
- [6. PyInstaller 打包](#6-pyinstaller-打包)
- [7. 体积优化原理](#7-体积优化原理)
- [8. 发布流程](#8-发布流程)
- [9. 常见构建问题](#9-常见构建问题)

---

## 1. 环境要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows 10 / 11（打包目标平台） |
| Python | **3.11 ~ 3.13**（`requires-python = ">=3.11,<3.14"`） |
| 包管理器 | [uv](https://github.com/astral-sh/uv)（强烈推荐）或 pip |
| 构建工具 | PyInstaller ≥ 6.0（dev 依赖已声明） |
| 磁盘空间 | 建议 ≥ 2 GB（PySide6 体积较大） |

> 为什么用 uv？本项目 `pyproject.toml` 使用 `uv_build` 作为构建后端，
> `uv sync` 会根据 `uv.lock` 精确还原依赖版本，速度远快于 pip。

### 安装 uv

```powershell
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 验证
uv --version
```

---

## 2. 克隆与依赖管理

```powershell
# 1. 克隆
git clone https://github.com/liufeias/MergeTool.git
cd MergeTool

# 2. 安装运行依赖 + dev 依赖（含 pyinstaller）
uv sync

# 3. 验证安装
uv run python -c "import PySide6, chardet; print('OK')"
```

### 常用 uv 命令

| 命令 | 作用 |
| --- | --- |
| `uv sync` | 按 `uv.lock` 安装/同步所有依赖 |
| `uv sync --no-dev` | 只安装运行依赖，不装 pyinstaller |
| `uv add <pkg>` | 添加运行依赖并更新锁文件 |
| `uv add --dev <pkg>` | 添加开发依赖 |
| `uv remove <pkg>` | 移除依赖 |
| `uv lock` | 只更新锁文件 |
| `uv run <cmd>` | 在项目虚拟环境中执行命令 |

### 使用 pip（可选）

若不用 uv：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install pyinstaller
```

---

## 3. 项目结构

```
MergeTool/
├── src/merge_tool/              # 源码包（src 布局）
│   ├── __init__.py              # 包入口，__version__
│   ├── __main__.py              # python -m merge_tool 入口，转发到 app.main()
│   ├── app.py                   # 主窗口、UI 组装、事件分发（最大文件）
│   ├── constants.py             # 常量、M3 色板、SVG 图标、QSS 主题、ENCODING_MAP
│   ├── encoding_utils.py        # 编码检测与安全读取
│   ├── file_utils.py            # 路径/大小/扩展名工具函数
│   ├── tree_model.py            # 树数据模型（三态勾选、增删、修剪）
│   ├── tree_view.py             # QTreeWidget 封装 + 自定义委托渲染
│   └── workers.py               # 后台线程：scan_worker / merge_worker
├── assets/                      # 图标等静态资源（可选，打包进 _internal/assets）
├── docs/                        # 文档
├── pyproject.toml               # 项目元数据（PEP 621）+ uv_build 配置
├── uv.lock                      # uv 锁文件
├── MergeTool.spec               # PyInstaller 打包配置
└── README.md
```

### 模块职责速查

| 模块 | 职责 | 关键点 |
| --- | --- | --- |
| `app.py` | 主窗口与调度 | `MergeToolApp`、`M3SearchBox`、`M3SelectButton`、拖放事件过滤 |
| `constants.py` | 全局常量与主题 | `GLOBAL_M3_STYLESHEET`、`ENCODING_MAP`、SVG 图标字符串 |
| `encoding_utils.py` | 编码检测 | `detect_encoding`、`read_file_safely`，多级兜底 |
| `file_utils.py` | 工具函数 | `human_size`、`normalize_ext_set`、`parse_drop_paths` |
| `tree_model.py` | 数据模型 | `Node`、`TreeModel`、`CheckState` 三态 |
| `tree_view.py` | 视图 | `M3TreeItemDelegate`、`NoFocusProxyStyle`、右键菜单 |
| `workers.py` | 后台线程 | `scan_worker`、`merge_worker`，通过队列与 UI 通信 |

---

## 4. 开发与调试

### 4.1 运行程序

```powershell
# 方式一：模块方式
uv run python -m merge_tool

# 方式二：命令行入口（pyproject 中声明）
uv run merge-tool
```

### 4.2 调试技巧

- **显示控制台**：`MergeTool.spec` 中 `console=False`。调试时可临时改为 `True`，
  或直接源码运行（源码运行默认有控制台）。
- **异常堆栈**：`app.py` 中 `disable_windowed_traceback=False`，
  打包后异常会弹窗显示 traceback。
- **打印调试**：后台线程通过 `ui_queue.put(("status", (text, color)))` 向 UI 发消息，
  可临时在 `_handle_worker_message` 中加 `print` 观察。

### 4.3 代码风格

`pyproject.toml` 已配置 ruff：

```powershell
uv run ruff check src
uv run ruff format src
```

规则集：`E, F, W, I, N, UP, B, C4, SIM`，忽略 `E501`（行宽由 formatter 处理）。

---

## 5. 依赖说明

### 运行依赖

| 包 | 版本 | 用途 |
| --- | --- | --- |
| `pyside6` | ≥ 6.12.0 | Qt for Python，GUI 框架 |
| `chardet` | ≥ 5.2.0 | 字符编码检测 |

### 开发依赖

| 包 | 用途 |
| --- | --- |
| `pyinstaller` | 打包为 exe |

### PySide6 子模块使用情况

项目实际用到的 PySide6 模块：

- `QtCore` — 信号、事件、QTimer、QSize、QEvent
- `QtGui` — QIcon、QPixmap、QPainter、QDragEnterEvent
- `QtWidgets` — 全部控件
- `QtSvg` — `QSvgRenderer` 渲染 SVG 图标
- `QtSvgWidgets` — 备用

**未使用但默认被 PySide6 引入**的大型模块（已在 spec 中排除）：
QtWebEngine、QtPdf、Qt3D、QtCharts、QtQuick/Qml、QtMultimedia、QtSql、QtTest、QtDesigner、QtHelp 等。

---

## 6. PyInstaller 打包

### 6.1 一键打包流程

在项目根目录 `E:\MyPythonProgram\MergeTool` 下执行：

```powershell
# 1. 清理旧产物
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# 2. 打包（读取 MergeTool.spec）
uv run pyinstaller MergeTool.spec --noconfirm --clean

# 3. 测试运行
.\dist\MergeTool\MergeTool.exe

# 4. 打包为 zip 发布
Compress-Archive -Path .\dist\MergeTool `
                 -DestinationPath .\dist\MergeTool-v2.0.0.zip -Force
```

产物结构（onedir 模式）：

```
dist/
├── MergeTool/
│   ├── MergeTool.exe          # 主程序
│   └── _internal/             # 依赖（Qt DLL、Python 运行时、assets 等）
└── MergeTool-v2.0.0.zip       # 发布包
```

### 6.2 MergeTool.spec 详解

`MergeTool.spec` 是 PyInstaller 的构建脚本，核心结构：

```python
# 路径解析
PROJECT_ROOT = os.path.abspath(SPECPATH)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
ICON_FILE = os.path.join(ASSETS_DIR, "icon.ico")
ENTRY_SCRIPT = os.path.join(SRC_DIR, "merge_tool", "__main__.py")

# datas：非 Python 资源
datas = []
if os.path.isdir(ASSETS_DIR):
    datas.append((ASSETS_DIR, "assets"))

# hiddenimports：静态分析漏掉的模块
hiddenimports = [
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    # chardet 内部探测器（运行时动态加载）
    "chardet", "chardet.universaldetector", ...
]

# excludes：排除大体积模块
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", ...
    "numpy", "scipy", "pandas", "matplotlib",
    "tkinter", "PyQt5", "PyQt6", ...
]

a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[SRC_DIR],
    binaries=[], datas=datas, hiddenimports=hiddenimports,
    excludes=excludes, noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name="MergeTool", console=False, upx=False,
          icon=ICON_FILE if os.path.exists(ICON_FILE) else None)
coll = COLLECT(exe, a.binaries, a.datas, name="MergeTool")
```

### 6.3 关键配置说明

| 配置 | 值 | 原因 |
| --- | --- | --- |
| 打包模式 | **onedir** | 启动快（无需每次解压）、体积可控、杀软误报少 |
| `pathex` | `[SRC_DIR]` | 让 PyInstaller 找到 `src/merge_tool` 包 |
| `console` | `False` | GUI 程序，不显示控制台 |
| `upx` | `False` | 避免 UPX 压缩导致杀软误报 |
| `optimize` | `1` | 去除 assert，保留 docstring |
| `hiddenimports` | chardet 子模块 | chardet 运行时动态 import 探测器，静态分析发现不了 |
| `excludes` | QtWebEngine 等 | 体积从 500 MB+ 降至 80–150 MB |
| `icon` | `assets/icon.ico` | 不存在时用系统默认图标 |

### 6.4 自定义图标

1. 准备一个 `.ico` 文件（建议含 16/32/48/256 多尺寸）。
2. 放到 `assets/icon.ico`。
3. spec 中的 `icon=ICON_FILE if os.path.exists(ICON_FILE) else None` 会自动使用。
4. 重新打包。

### 6.5 打包后资源定位

`assets/` 会被打包到 `_internal/assets/`。程序中通过 `sys._MEIPASS` 定位：

```python
import sys, os
if getattr(sys, "frozen", False):
    base = sys._MEIPASS
else:
    base = os.path.dirname(os.path.abspath(__file__))
asset_path = os.path.join(base, "assets", "icon.ico")
```

---

## 7. 体积优化原理

PySide6 完整安装约 **500 MB+**，其中最大的是 QtWebEngine（~131 MB）。
本项目通过 `excludes` 排除以下模块：

| 排除模块 | 约省体积 | 说明 |
| --- | --- | --- |
| QtWebEngine 全家桶 | ~131 MB | 项目不用浏览器内核 |
| QtQuick / Qml | 大 | 项目用 QtWidgets，不用 QML |
| Qt3D | 大 | 无 3D 需求 |
| QtCharts / DataVisualization | 中 | 无图表 |
| QtMultimedia | 中 | 无音视频 |
| QtPdf | ~3 MB | 无 PDF |
| QtSql / QtTest / QtDesigner / QtHelp | 中 | 运行时不需要 |
| numpy / scipy / pandas / matplotlib | 大 | 项目无科学计算 |
| tkinter / PyQt5 / PyQt6 / wx | 中 | 避免混入其他 GUI 框架 |

**必须保留**：

- `shiboken6` — PySide6 核心绑定引擎，**绝对不能排除**。
- `QtSvg` — 项目用 `QSvgRenderer` 渲染矢量图标。
- `chardet` 及其全部探测器子模块。

最终产物约 **80–150 MB**（视 PySide6 版本浮动）。

---

## 8. 发布流程

### 8.1 版本号维护

版本号在三处保持一致：

1. `pyproject.toml` → `[project] version = "2.0.0"`
2. `src/merge_tool/__init__.py` → `__version__ = "2.0.0"`
3. `MergeTool.spec` 注释与 zip 名（可选）

### 8.2 完整发布步骤

```powershell
# 1. 更新版本号（三处）
# 2. 更新 docs/CHANGELOG.md 与 docs/CHANGELOG.en.md
# 3. 提交
git add .
git commit -m "chore: release v2.0.0"
git tag v2.0.0
git push origin main --tags

# 4. 清理并打包
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
uv run pyinstaller MergeTool.spec --noconfirm --clean

# 5. 测试
.\dist\MergeTool\MergeTool.exe

# 6. 压缩
Compress-Archive -Path .\dist\MergeTool `
                 -DestinationPath .\dist\MergeTool-v2.0.0.zip -Force
```

7. 在 GitHub 仓库 → Releases → Draft a new release：
   - Tag: `v2.0.0`
   - Title: `MergeTool v2.0.0`
   - 描述：从 CHANGELOG 摘录
   - 上传 `MergeTool-v2.0.0.zip`

### 8.3 可选的 CI 自动化

若需 GitHub Actions 自动打包，可添加 `.github/workflows/build.yml`：

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

## 9. 常见构建问题

### Q1：`ModuleNotFoundError: No module named 'merge_tool'`

**原因**：PyInstaller 找不到 src 布局下的包。

**解决**：确认 spec 中 `pathex=[SRC_DIR]`，且 `SRC_DIR` 指向 `项目根/src`。

### Q2：打包后运行报 `ImportError: chardet.xxx`

**原因**：chardet 运行时动态加载探测器，PyInstaller 静态分析漏掉。

**解决**：确认 spec 的 `hiddenimports` 中包含全部 `chardet.*` 子模块（本项目已列全）。

### Q3：打包后图标不显示 / SVG 图标缺失

**原因**：`assets/` 未被打包，或 `QtSvg` 被误排除。

**解决**：

1. 确认 `assets/` 存在且 spec 中 `datas` 已包含。
2. 确认 `excludes` 中**没有** `PySide6.QtSvg`。

### Q4：exe 体积仍然很大

**排查**：

- 确认使用的是 `MergeTool.spec`（而非 `pyinstaller -F app.py`）。
- 检查 `excludes` 是否生效：打包日志中搜索 `Excluded module`。
- 确认没有意外引入 numpy/pandas 等。

### Q5：杀毒软件报毒

**原因**：PyInstaller 引导程序 + 未签名 exe 常被误报。

**缓解**：

- spec 中 `upx=False`（已设置）。
- 向用户说明，或购买代码签名证书。

### Q6：`Remove-Item` 提示 build/dist 不存在

正常现象。加 `-ErrorAction SilentlyContinue` 即可忽略。

### Q7：PySide6 版本升级后打包失败

PySide6 大版本升级可能改变模块名。检查 spec 中 `excludes` 的模块名是否仍有效，
必要时更新 PyInstaller 与 `pyinstaller-hooks-contrib`。

---

## 🧭 相关文档

- [← 返回首页](../README.md)
- [📘 使用帮助](USAGE.md) — 面向普通用户
- [📝 更新日志](CHANGELOG.md) — 版本历史
- [English Version](BUILD.en.md)