# -*- mode: python ; coding: utf-8 -*-
"""
===============================================================================
 PyInstaller spec 文件 - MergeTool (PySide6 版)
===============================================================================

使用方式（在项目根目录 E:\\MyPythonProgram\\MergeTool 下执行）：

    # 1. 清理旧产物
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

    # 2. 打包
    uv run pyinstaller MergeTool.spec --noconfirm --clean

    # 3. 测试
    .\\dist\\MergeTool\\MergeTool.exe

    # 4. 打包为 zip
    Compress-Archive -Path .\\dist\\MergeTool `
                     -DestinationPath .\\dist\\MergeTool-v2.0.0.zip -Force

===============================================================================
 设计说明
===============================================================================
 1. onedir 模式：启动快（无需每次解压）、体积可控、杀软误报少。
 2. 通过 excludes 排除 PySide6 用不到的巨型模块：
      QtWebEngine(~131MB)、QtPdf、QtQuick/Qml、Qt3D、Charts、
      Multimedia、Sql、Test、Designer、Help 等等，
      打包产物从 500MB+ 降至 80-150MB。
 3. 保留 shiboken6（PySide6 的核心绑定引擎，绝对不能排除）。
 4. 保留 QtSvg（项目用 QSvgRenderer 渲染 SVG 图标）。
 5. pathex=[SRC_DIR]：让 PyInstaller 找到 src 下的 merge_tool 包。
 6. assets/ 目录（若存在）会被打包到 _internal/assets/，
    程序通过 sys._MEIPASS 定位。
===============================================================================
"""

import os
import sys


# =============================================================================
# 路径解析
# =============================================================================
# SPECPATH 是 PyInstaller 注入的变量，表示 spec 文件所在目录（绝对路径）
try:
    PROJECT_ROOT = os.path.abspath(SPECPATH)
except NameError:
    # 若在某些 IDE 里直接执行 spec（非 PyInstaller 环境），回退到当前工作目录
    PROJECT_ROOT = os.path.abspath(os.getcwd())

SRC_DIR = os.path.join(PROJECT_ROOT, "src")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
ICON_FILE = os.path.join(ASSETS_DIR, "icon.ico")

# 入口脚本
ENTRY_SCRIPT = os.path.join(SRC_DIR, "merge_tool", "__main__.py")


# =============================================================================
# datas：非 Python 资源文件
# 格式：(源路径, 打包后位于 _internal/ 下的目录名)
# =============================================================================
datas = []

# 自定义 assets 目录（图标、外部资源等）
if os.path.isdir(ASSETS_DIR):
    datas.append((ASSETS_DIR, "assets"))


# =============================================================================
# hiddenimports：PyInstaller 静态分析可能漏掉的模块
# =============================================================================
hiddenimports = [
    # ----- PySide6 核心模块（确保不会被漏掉） -----
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",

    # ----- chardet 内部探测器（运行时动态加载，静态分析发现不了） -----
    "chardet",
    "chardet.universaldetector",
    "chardet.chardistribution",
    "chardet.charsetprober",
    "chardet.codingstatemachine",
    "chardet.enums",
    "chardet.escprober",
    "chardet.escsm",
    "chardet.eucjpprober",
    "chardet.euckrprober",
    "chardet.euctwprober",
    "chardet.gb2312prober",
    "chardet.hebrewprober",
    "chardet.johabprober",
    "chardet.langbulgarianmodel",
    "chardet.langcyrillicmodel",
    "chardet.langgreekmodel",
    "chardet.langhebrewmodel",
    "chardet.langhungarianmodel",
    "chardet.langthaimodel",
    "chardet.langturkishmodel",
    "chardet.latin1prober",
    "chardet.mbcsgroupprober",
    "chardet.mbcssm",
    "chardet.sbcharsetprober",
    "chardet.sbcsgroupprober",
    "chardet.sjisprober",
    "chardet.utf1632prober",
    "chardet.utf8prober",
]


# =============================================================================
# excludes：排除无用的大体积模块（体积瘦身的核心）
# =============================================================================
excludes = [
    # ---------------- PySide6 中本项目用不到的巨型模块 ----------------
    # WebEngine（最大，~131MB）
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.QtWebView",

    # PDF（~3MB）
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",

    # 3D（很大）
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",

    # 图表/数据可视化
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",

    # 多媒体
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",

    # Quick / QML 全家桶
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.QtQuickControls2",

    # 其它用不到的 Qt 模块
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtNetworkAuth",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtUiTools",

    # ---------------- 科学计算/数据（本项目不用） ----------------
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "sympy",

    # ---------------- 开发工具 / 测试 ----------------
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "sphinx",
    "pydoc",
    "doctest",
    "unittest",
    "test",
    "tests",

    # ---------------- 其它 GUI 框架（避免混入） ----------------
    "tkinter",
    "customtkinter",
    "tkinterdnd2",
    "PyQt5",
    "PyQt6",
    "wx",
]


# =============================================================================
# 分析入口脚本
# =============================================================================
a = Analysis(
    # 入口脚本：__main__.py 内部调用 app.main()
    [ENTRY_SCRIPT],

    # 让 PyInstaller 找到 src 下的 merge_tool 包
    pathex=[SRC_DIR],

    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,

    # PyInstaller 6.x 自带 PySide6 hook，一般无需自定义 hookspath
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    excludes=excludes,

    # 使用 zip 归档 Python 字节码
    noarchive=False,

    # 优化级别：0=不优化，1=去 assert，2=去 docstring
    optimize=1,
)


# =============================================================================
# 打包 PYZ（Python 字节码归档）
# =============================================================================
pyz = PYZ(a.pure)


# =============================================================================
# 生成 EXE
# =============================================================================
exe = EXE(
    pyz,
    a.scripts,

    # onedir 模式：不把所有东西塞进 exe，而是散在 _internal/
    [],
    exclude_binaries=True,

    name="MergeTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,

    # 不使用 UPX 压缩，避免杀毒软件误报
    upx=False,

    # 不显示控制台窗口（GUI 程序）
    # 若需调试，临时改为 True
    console=False,

    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,

    # 程序图标（有则用，无则系统默认）
    icon=ICON_FILE if os.path.exists(ICON_FILE) else None,
)


# =============================================================================
# 收集所有依赖到 dist/MergeTool/ 目录
# =============================================================================
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MergeTool",
)