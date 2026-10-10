# -*- coding: utf-8 -*-
"""
全局常量与 Google Material Design 3 (M3 Reply) 官方设计系统定义模块。

集中管理：
    - 纯正 Google Material Symbols SVG 矢量定义与转换函数
    - Google Material Design 3 官方色彩规范 (Tonal Palette)
    - 树列表排版度量（M3_TREE_ROW_HEIGHT 等全部参数）
    - 全局 M3 QSS 样式表引擎（深度加固：彻底消除橘黄虚线、滚动条饱满半圆圆角、整行连贯选择）
"""

import os
import tempfile
from typing import Dict, Tuple

from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt

# 全局默认字体
GLOBAL_FONT_FAMILY: str = "Microsoft YaHei UI"

# =============================================================================
# 1. Google M3 (Reply App / Material You) 官方纯正色谱体系
# =============================================================================
M3_BG_ROOT = "#EFF3F8"                    # 应用程序总底板颜色（极柔和天青蓝灰底色）
M3_SURFACE_CARD = "#FFFFFF"               # 悬浮大卡片背景色（纯白）
M3_SURFACE_INPUT = "#FFFFFF"              # 输入框纯白内衬
M3_SURFACE_INPUT_HOVER = "#F5F8FC"        # 输入框悬停底色
M3_SURFACE_HOVER = "#E7EDF4"              # 控件悬停底色

# 核心功能胶囊色
M3_FAB_MINT_BG = "#C4EED0"                # 薄荷绿主动作胶囊底色
M3_FAB_MINT_HOVER = "#AEE6BE"             # 薄荷绿悬停
M3_FAB_MINT_TEXT = "#072711"              # 薄荷绿文字（深墨绿）

# 激活胶囊与次要操作
M3_PILL_BLUE_BG = "#D3E3FD"               # 冰蓝激活胶囊底色 (Primary Container)
M3_PILL_BLUE_HOVER = "#C2D7FC"            # 冰蓝悬停色
M3_PILL_BLUE_TEXT = "#041E49"             # 冰蓝深海蓝文字 (On Primary Container)

M3_BTN_SECONDARY_BG = "#E0E6ED"           # 次要操作按钮底色
M3_BTN_SECONDARY_HOVER = "#D4DBE4"        # 次要操作悬停色
M3_COLOR_PRIMARY = "#0B57D0"              # Google Blue 强调主色
M3_DANGER_BG = "#FCE8E6"                  # 浅粉红危险操作背景
M3_DANGER_TEXT = "#B3261E"                # 深暗红文字
M3_DANGER_HOVER = "#FAD2CF"               # 危险操作悬停

# 文本色阶 (Typography Colors)
M3_TEXT_TITLE = "#1F1F1F"                 # 标题墨黑文字（深邃自然）
M3_TEXT_BODY = "#444746"                  # 次要正文与标签（中度炭灰）
M3_TEXT_MUTED = "#727775"                 # 辅助说明、占位符文字
M3_BORDER_SUBTLE = "#C4C7C5"              # 柔和轮廓线 (Outline Variant)

# =============================================================================
# 2. 树视图排版度量
# =============================================================================
M3_TREE_ROW_HEIGHT = 38                   # 舒适行高（像素，38px 呼吸感）

# =============================================================================
# 3. 官方原生 Material Symbols SVG 代码库
# =============================================================================

# 向右折叠大三角 (chevron_right - 饱满大尺寸)
SVG_CHEVRON_RIGHT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <path fill="#444746" d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
</svg>
"""

# 向下展开大三角 (expand_more - 饱满大尺寸)
SVG_EXPAND_MORE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <path fill="#444746" d="M16.59 8.59L12 13.17 7.41 8.59 6 10l6 6 6-6-1.41-1.41z"/>
</svg>
"""

# 文件夹图标 (folder) - Google 浅海蓝
SVG_FOLDER = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <path fill="#0B57D0" d="M4 4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2H4z"/>
</svg>
"""

# 文件图标 (description) - 极简灰白文本卡片
SVG_FILE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <path fill="#74777F" d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
</svg>
"""

# 下拉倒三角 (arrow_drop_down)
SVG_DROPDOWN_ARROW = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <path fill="#444746" d="M11.29 15.71a1 1 0 0 0 1.42 0l4.59-4.59A1 1 0 0 0 16.59 9.5H7.41a1 1 0 0 0-.71 1.62z"/>
</svg>
"""

# 放大镜搜索图标 (search)
SVG_SEARCH = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <path fill="#444746" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
</svg>
"""

# 矢量高清晰度复选框已选图标 (check_box)
SVG_CHECKED = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <rect width="18" height="18" x="3" y="3" rx="4" fill="#0B57D0"/>
  <path fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" d="m7.5 12.5 3 3 6-6"/>
</svg>
"""

# 矢量高清晰度复选框未选图标 (check_box_outline_blank)
SVG_UNCHECKED = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <rect width="18" height="18" x="3" y="3" rx="4" fill="#FFFFFF" stroke="#74777F" stroke-width="2"/>
</svg>
"""

# 复选框半选 (indeterminate_check_box)
SVG_PARTIAL = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <rect width="18" height="18" x="3" y="3" rx="4" fill="#0B57D0"/>
  <path fill="#FFFFFF" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" d="M7 12h10"/>
</svg>
"""

def create_svg_icon(svg_str: str, size: QSize = QSize(20, 20)) -> QIcon:
    """利用 Qt 原生矢量引擎将 SVG 字符串转换为高质量无损 QIcon。"""
    byte_arr = QByteArray(svg_str.encode("utf-8"))
    renderer = QSvgRenderer(byte_arr)
    pixmap = QPixmap(size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)

def create_svg_pixmap(svg_str: str, size: QSize = QSize(20, 20)) -> QPixmap:
    """直接生成高质量矢量 QPixmap 供委托绘制使用。"""
    byte_arr = QByteArray(svg_str.encode("utf-8"))
    renderer = QSvgRenderer(byte_arr)
    pixmap = QPixmap(size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return pixmap

# 动态保存临时高清矢量图标文件供 QSS 纯净精准引用
temp_dir = tempfile.gettempdir()
TEMP_ARROW_SVG_PATH = os.path.join(temp_dir, "m3_dropdown_arrow.svg").replace("\\", "/")
TEMP_CHK_ON_SVG_PATH = os.path.join(temp_dir, "m3_chk_checked.svg").replace("\\", "/")
TEMP_CHK_OFF_SVG_PATH = os.path.join(temp_dir, "m3_chk_unchecked.svg").replace("\\", "/")

try:
    with open(TEMP_ARROW_SVG_PATH, "w", encoding="utf-8") as f:
        f.write(SVG_DROPDOWN_ARROW.strip())
    with open(TEMP_CHK_ON_SVG_PATH, "w", encoding="utf-8") as f:
        f.write(SVG_CHECKED.strip())
    with open(TEMP_CHK_OFF_SVG_PATH, "w", encoding="utf-8") as f:
        f.write(SVG_UNCHECKED.strip())
except Exception:
    pass

# =============================================================================
# 4. 运行参数与编码配置
# =============================================================================
DEFAULT_OUTPUT_NAME = "merged_content.txt"
SCAN_REPORT_INTERVAL_SEC = 0.15
MERGE_REPORT_INTERVAL_SEC = 0.08
TREE_SEARCH_DEBOUNCE_MS = 180

CHARDET_SAMPLE_BYTES = 256 * 1024
CHARDET_MIN_CONFIDENCE = 0.7
STRICT_DECODE_SAMPLE_BYTES = 64 * 1024
FALLBACK_ENCODINGS = ("utf-8", "gb18030", "gbk", "big5", "latin-1")

ENCODING_MAP = {
    "自动检测": None,
    "UTF-8": "utf-8",
    "UTF-8-SIG (带BOM)": "utf-8-sig",
    "GB18030 (推荐中文)": "gb18030",
    "GBK": "gbk",
    "GB2312": "gb2312",
    "BIG5": "big5",
    "UTF-16 LE": "utf-16",
    "UTF-16 BE": "utf-16-be",
    "UTF-32": "utf-32",
    "Latin-1 (ISO-8859-1)": "latin-1",
    "ASCII": "ascii",
}

# =============================================================================
# 5. 全局 Material Design 3 QSS 样式表引擎
# ★ 重点加固：阻断焦点虚线轮廓 (outline: none)，垂直/水平滚动条两端半圆圆角
# =============================================================================
GLOBAL_M3_STYLESHEET = f"""
* {{
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    outline: none;
}}

QMainWindow, QWidget#MainCentralWidget, QWidget#SidebarContent {{
    background-color: #EFF3F8;
}}

QFrame#RightMainCard {{
    background-color: #FFFFFF;
    border: none;
    border-radius: 28px;
}}

/* 基础输入框 */
QLineEdit {{
    background-color: #FFFFFF;
    border: 1px solid #C4C7C5;
    border-radius: 12px;
    padding: 8px 14px;
    color: #1F1F1F;
    font-size: 13px;
    min-height: 24px;
}}
QLineEdit:hover {{
    border: 1px solid #74777F;
}}
QLineEdit:focus {{
    background-color: #FFFFFF;
    border: 2px solid #0B57D0;
}}

/* 复选框 */
QCheckBox {{
    font-size: 13px;
    color: #1F1F1F;
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 20px;
    height: 20px;
}}
QCheckBox::indicator:unchecked {{
    image: url("{TEMP_CHK_OFF_SVG_PATH}");
}}
QCheckBox::indicator:checked {{
    image: url("{TEMP_CHK_ON_SVG_PATH}");
}}

/* ★ 树视图：彻底封死虚线轮廓，整行连贯选择高亮 */
QTreeWidget {{
    background-color: #FFFFFF;
    border: none;
    outline: none;
    font-size: 13px;
    color: #1F1F1F;
}}
QTreeWidget:focus {{
    outline: none;
    border: none;
}}
QTreeWidget::item {{
    height: 38px;
    padding-left: 0px;
    border: none;
    outline: none;
}}
QTreeWidget::item:focus {{
    outline: none;
    border: none;
}}
QTreeWidget::item:selected {{
    background-color: #D3E3FD;
    color: #041E49;
    border: none;
    outline: none;
}}

/* 表头：浅灰底色 + 1px 优雅右侧分割线 */
QHeaderView::section {{
    background-color: #F0F4F8;
    color: #444746;
    border: none;
    border-right: 1px solid #E0E5EC;
    border-bottom: 1px solid #E0E5EC;
    font-weight: bold;
    font-size: 12px;
    padding-left: 10px;
    padding-right: 10px;
    height: 40px;
}}
QHeaderView::section:last {{
    border-right: none;
}}

/* ★ 垂直滚动条：下移 42px 避开表头，滑块上下留 2px 呼吸槽以呈现绝对半圆胶囊端头！ */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin-top: 42px;
    margin-bottom: 8px;
    margin-right: 2px;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: #A0AAB5;
    min-height: 36px;
    border-radius: 4px;
    margin-top: 2px;
    margin-bottom: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: #707A85;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    width: 0px;
    background: transparent;
    border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

/* ★ 水平滚动条：左右留 2px 呼吸槽以呈现绝对半圆胶囊端头！ */
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin-left: 8px;
    margin-right: 8px;
    margin-bottom: 2px;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: #A0AAB5;
    min-width: 36px;
    border-radius: 4px;
    margin-left: 2px;
    margin-right: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: #707A85;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    height: 0px;
    width: 0px;
    background: transparent;
    border: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}
"""