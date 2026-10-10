# -*- coding: utf-8 -*-
"""
主窗口与 UI 组装调度中心（Google Material Design 3 官方 Reply 架构 - 工业级高保真版）。

================================ 核心升级与重构要点 ================================
1. 【右上角快速过滤框支持 Material 蓝色焦点边框】：
   - 封装工业级 `M3SearchBox` 药丸输入组件，内置事件过滤器精确监听子输入框的焦点事件；
   - 当用户点击或 Tab 聚焦到过滤框时，外层药丸大容器同步呈现 `border: 2px solid #0B57D0`，
     与左侧设置面板中所有输入框的聚焦视觉表现达成 100% 完美一致；
   - 点击药丸容器内任意区域（包括放大镜图标及四周留白）自动激活输入光标，体验更顺手。
2. 彻底根治下拉弹窗与右键菜单外角杂色：
   - 采用 `Qt.WA_TranslucentBackground` 半透明通道结合 `Qt.FramelessWindowHint`，彻底抹除毛边。
3. 保持下拉弹窗宽度与输入框 1:1 绝对同宽。
4. 100% 灵敏的本地文件拖放解析与多线程防卡死处理机制。
"""

import os
import sys
import threading
from typing import List, Optional, Set

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QMenu,
    QProgressBar, QFileDialog, QMessageBox, QFrame, QScrollArea
)
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSize, QEvent

from merge_tool.constants import (
    ENCODING_MAP,
    DEFAULT_OUTPUT_NAME,
    GLOBAL_M3_STYLESHEET,
    TREE_SEARCH_DEBOUNCE_MS,
    SVG_SEARCH,
    SVG_DROPDOWN_ARROW,
    create_svg_icon,
    M3_BG_ROOT,
    GLOBAL_FONT_FAMILY,
)
from merge_tool.file_utils import parse_drop_paths
from merge_tool.tree_model import TreeModel
from merge_tool.tree_view import TreeView
from merge_tool.workers import scan_worker, merge_worker


class WorkerBridge(QObject):
    """跨线程与 Qt 主事件循环安全通信的信号桥梁。"""
    sig_message = Signal(str, object)


class M3SelectButton(QPushButton):
    """
    ★ 工业级 M3 下拉选择按钮：
    宽度严格与输入框 1:1 对齐，拥有纯白底色、大圆角、100% 无外角杂边的标准 Material 菜单！
    """

    valueChanged = Signal(str)

    def __init__(self, items: List[str], current: str = "自动检测", parent=None):
        super().__init__(parent)
        self.items = items
        self.current_value = current

        self.setText(f"  {current}")
        self.setFixedHeight(40)
        self.setIcon(create_svg_icon(SVG_DROPDOWN_ARROW, QSize(16, 16)))
        self.setLayoutDirection(Qt.RightToLeft)  # 箭头靠右，文字靠左

        self.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #C4C7C5;
                border-radius: 12px;
                padding: 6px 14px;
                color: #1F1F1F;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover {
                border: 1px solid #74777F;
            }
        """)

        # 构造纯净大圆角无杂边菜单
        self.menu = QMenu(self)
        
        # 向底层窗口直接注入半透明通道属性，彻底消除外角杂色
        self.menu.setAttribute(Qt.WA_TranslucentBackground, True)
        self.menu.setWindowFlags(self.menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)

        self.menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 6px;
                color: #1F1F1F;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #D3E3FD;
                color: #041E49;
            }
        """)

        for it in self.items:
            act = self.menu.addAction(it)
            act.triggered.connect(lambda checked=False, val=it: self._on_select(val))

        self.clicked.connect(self._show_menu)

    def _show_menu(self) -> None:
        """弹出下拉菜单，保证宽度与宿主按钮完全同宽。"""
        self.menu.setMinimumWidth(self.width())
        self.menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _on_select(self, val: str) -> None:
        """菜单项选中回调。"""
        self.current_value = val
        self.setText(f"  {val}")
        self.valueChanged.emit(val)

    def currentText(self) -> str:
        """获取当前选择的文本内容。"""
        return self.current_value


class M3SearchBox(QFrame):
    """
    ★ 工业级 Google Material Design 3 药丸型搜索输入框：
    
    核心功能：
    1. 完美复刻 Google 药丸设计，内嵌 SVG 放大镜图标与原生文本输入控件；
    2. 【核心焦点联动机制】：通过在内置 QLineEdit 安装事件过滤器，
       捕获 FocusIn 与 FocusOut 状态，动态将整个药丸外框切换为 2px #0B57D0 Google 蓝边框，
       与主窗口中所有标准输入框的焦点样式达成 100% 视觉对齐；
    3. 支持悬停反馈（hover）与点击空白处自动获取焦点，人机交互极佳。
    """

    textChanged = Signal(str)

    def __init__(self, placeholder: str = "输入部分文件名快速过滤", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("M3SearchBoxPill")
        self.setFixedSize(280, 44)

        # 内部状态记录
        self._is_focused: bool = False
        self._is_hovered: bool = False

        # 水平布局：图标靠左，文本框自适应居右
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        # 1. 放大镜图标
        self.icon_lbl = QLabel(self)
        self.icon_lbl.setPixmap(create_svg_icon(SVG_SEARCH, QSize(18, 18)).pixmap(18, 18))
        self.icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.icon_lbl)

        # 2. 原生输入框（无边框、透明底色）
        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setStyleSheet(
            "border: none; background: transparent; font-size: 13px; color: #1F1F1F;"
        )
        self.line_edit.textChanged.connect(self.textChanged)
        layout.addWidget(self.line_edit)

        # 关键：监听内部输入框的焦点进出事件
        self.line_edit.installEventFilter(self)

        # 初始化渲染初始状态样式
        self._update_pill_style()

    def _update_pill_style(self) -> None:
        """根据当前的聚焦、悬停状态动态更新外层药丸的边框与阴影效果。"""
        if self._is_focused:
            # 聚焦高亮状态：呈现与左侧输入框一致的 2px Google 强调蓝边框！
            border_css = "border: 2px solid #0B57D0;"
        elif self._is_hovered:
            # 鼠标悬停但未聚焦状态：呈现较深的浅灰轮廓
            border_css = "border: 1px solid #74777F;"
        else:
            # 默认常态：呈现极简柔和灰色微轮廓
            border_css = "border: 1px solid #E0E5EC;"

        self.setStyleSheet(f"""
            QFrame#M3SearchBoxPill {{
                background-color: #FFFFFF;
                {border_css}
                border-radius: 22px;
            }}
        """)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """事件过滤器：精准拦截子控件 line_edit 的聚焦与失焦事件。"""
        if watched == self.line_edit:
            if event.type() == QEvent.FocusIn:
                self._is_focused = True
                self._update_pill_style()
            elif event.type() == QEvent.FocusOut:
                self._is_focused = False
                self._update_pill_style()
        return super().eventFilter(watched, event)

    def enterEvent(self, event) -> None:
        """鼠标移入事件：触发悬停高亮。"""
        super().enterEvent(event)
        self._is_hovered = True
        if not self._is_focused:
            self._update_pill_style()

    def leaveEvent(self, event) -> None:
        """鼠标离开事件：还原悬停状态。"""
        super().leaveEvent(event)
        self._is_hovered = False
        if not self._is_focused:
            self._update_pill_style()

    def mousePressEvent(self, event) -> None:
        """点击药丸框内任何非输入框区域（如放大镜图标）时，自动聚焦到文本输入框。"""
        super().mousePressEvent(event)
        self.line_edit.setFocus()

    def text(self) -> str:
        """获取当前输入的文本内容。"""
        return self.line_edit.text()

    def setText(self, text: str) -> None:
        """设置输入的文本内容。"""
        self.line_edit.setText(text)

    def clear(self) -> None:
        """清空输入框文本。"""
        self.line_edit.clear()


class MergeToolApp(QMainWindow):
    """Google Material Design 3 风格合并工具主窗口。"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("MergeTool - Google Material Design 3 工作台")
        self.resize(1440, 880)
        self.setMinimumSize(1120, 720)

        # 挂载 M3 全局主题样式表
        self.setStyleSheet(GLOBAL_M3_STYLESHEET)

        # 开启原生拖放
        self.setAcceptDrops(True)

        # 数据模型与核心状态
        self.model: Optional[TreeModel] = None
        self.expanded: Set[str] = set()
        self.known_files: Set[str] = set()
        self._pending_extra_files: Optional[List[str]] = None
        self._scan_append: bool = False

        # 后台任务线程
        self.task_thread: Optional[threading.Thread] = None
        self.cancel_flag = threading.Event()

        # 信号桥梁
        self.bridge = WorkerBridge()
        self.bridge.sig_message.connect(self._handle_worker_message)

        # 搜索防抖定时器
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_tree_search)

        self._build_ui()

        # 全局安装事件过滤器，拦截所有子部件，100% 确保拖放成功触发
        QApplication.instance().installEventFilter(self)

    # -------------------------------------------------------------------------
    # 界面组装布局 (M3 Reply Architecture)
    # -------------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("MainCentralWidget")
        central.setAttribute(Qt.WA_StyledBackground, True)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 16, 18, 12)
        main_layout.setSpacing(10)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # 1. 左侧 M3 通透侧边栏
        self.left_sidebar = self._build_left_sidebar()
        body_layout.addWidget(self.left_sidebar, stretch=0)

        # 2. 右侧纯白悬浮大卡片
        self.right_card = self._build_right_main_card()
        body_layout.addWidget(self.right_card, stretch=1)

        main_layout.addLayout(body_layout, stretch=1)

        # 3. 底部全宽现代状态栏
        bottom_bar = self._build_bottom_status_bar()
        main_layout.addWidget(bottom_bar, stretch=0)

    def _build_left_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(410)
        sidebar.setAttribute(Qt.WA_StyledBackground, True)

        scroll = QScrollArea(sidebar)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        content.setObjectName("SidebarContent")
        content.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)

        # ==================== 1. 数据源根目录 ====================
        lbl_root = QLabel("数据源根目录")
        lbl_root.setStyleSheet("font-weight: bold; font-size: 13px; color: #1F1F1F;")
        layout.addWidget(lbl_root)

        root_box = QHBoxLayout()
        root_box.setSpacing(8)
        self.txt_root = QLineEdit()
        self.txt_root.setPlaceholderText("选择目录，或拖拽文件至窗口")
        root_box.addWidget(self.txt_root)

        btn_browse_root = QPushButton("浏览")
        btn_browse_root.setFixedSize(72, 38)
        btn_browse_root.setStyleSheet("""
            QPushButton {
                background-color: #D3E3FD;
                color: #041E49;
                font-weight: bold;
                font-size: 12px;
                border-radius: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #C2D7FC;
            }
        """)
        btn_browse_root.clicked.connect(self._choose_root_folder)
        root_box.addWidget(btn_browse_root)
        layout.addLayout(root_box)

        lbl_drag_hint = QLabel("拖入文件或文件夹即可自动合并追加；重复项自动剔除。")
        lbl_drag_hint.setStyleSheet("color: #727775; font-size: 11px;")
        lbl_drag_hint.setWordWrap(True)
        layout.addWidget(lbl_drag_hint)

        layout.addSpacing(6)

        # ==================== 2. 筛选规则 ====================
        lbl_ext = QLabel("文件扩展名 (逗号分隔，留空表示全部):")
        lbl_ext.setStyleSheet("font-weight: bold; font-size: 12px; color: #444746;")
        layout.addWidget(lbl_ext)

        self.txt_ext = QLineEdit("py,txt,md,json")
        self.txt_ext.setPlaceholderText("例如: py,txt,md；留空表示不限")
        layout.addWidget(self.txt_ext)

        chk_box = QHBoxLayout()
        self.chk_no_ext = QCheckBox("包含无扩展名")
        chk_box.addWidget(self.chk_no_ext)
        self.chk_recurse = QCheckBox("递归子文件夹")
        self.chk_recurse.setChecked(True)
        chk_box.addWidget(self.chk_recurse)
        layout.addLayout(chk_box)

        lbl_pattern = QLabel("文件名筛选 (普通字符串或正则):")
        lbl_pattern.setStyleSheet("font-weight: bold; font-size: 12px; color: #444746;")
        layout.addWidget(lbl_pattern)

        pat_box = QHBoxLayout()
        pat_box.setSpacing(8)
        self.txt_pattern = QLineEdit()
        self.txt_pattern.setPlaceholderText("留空表示不筛选")
        pat_box.addWidget(self.txt_pattern)

        self.chk_regex = QCheckBox("使用正则表达式匹配")
        pat_box.addWidget(self.chk_regex)
        layout.addLayout(pat_box)

        layout.addSpacing(6)

        # ==================== 3. 编码与输出 ====================
        lbl_enc = QLabel("文本读取编码:")
        lbl_enc.setStyleSheet("font-weight: bold; font-size: 12px; color: #444746;")
        layout.addWidget(lbl_enc)

        # 纯净 M3 规范下拉选择按钮（无黑角、无白角、与输入框完全同宽）
        self.cmb_encoding = M3SelectButton(list(ENCODING_MAP.keys()), current="自动检测")
        layout.addWidget(self.cmb_encoding)

        lbl_out = QLabel("合并输出目标文件:")
        lbl_out.setStyleSheet("font-weight: bold; font-size: 12px; color: #444746;")
        layout.addWidget(lbl_out)

        out_box = QHBoxLayout()
        self.txt_out = QLineEdit(os.path.abspath("./" + DEFAULT_OUTPUT_NAME))
        out_box.addWidget(self.txt_out)

        btn_browse_out = QPushButton("另存为")
        btn_browse_out.setFixedSize(72, 38)
        btn_browse_out.setStyleSheet("""
            QPushButton {
                background-color: #D3E3FD;
                color: #041E49;
                font-weight: bold;
                font-size: 12px;
                border-radius: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #C2D7FC;
            }
        """)
        btn_browse_out.clicked.connect(self._choose_output_file)
        out_box.addWidget(btn_browse_out)
        layout.addLayout(out_box)

        layout.addSpacing(6)

        # ==================== 4. 辅助操作与主触发区 ====================
        self.chk_flat = QCheckBox("平铺视图 (扁平化展示所有具体文件)")
        self.chk_flat.toggled.connect(self._on_toggle_flat_view)
        layout.addWidget(self.chk_flat)

        btn_grid = QHBoxLayout()
        btn_scan = QPushButton("扫描目录")
        btn_scan.setFixedHeight(40)
        btn_scan.setStyleSheet("""
            QPushButton {
                background-color: #E0E6ED;
                color: #1F1F1F;
                font-size: 12px;
                font-weight: bold;
                border-radius: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #D4DBE4;
            }
        """)
        btn_scan.clicked.connect(lambda: self._on_scan_click(append=False))
        btn_grid.addWidget(btn_scan)

        btn_filter = QPushButton("应用筛选")
        btn_filter.setFixedHeight(40)
        btn_filter.setStyleSheet("""
            QPushButton {
                background-color: #E0E6ED;
                color: #1F1F1F;
                font-size: 12px;
                font-weight: bold;
                border-radius: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #D4DBE4;
            }
        """)
        btn_filter.clicked.connect(self._on_apply_filter)
        btn_grid.addWidget(btn_filter)
        layout.addLayout(btn_grid)

        layout.addSpacing(10)

        # 薄荷绿实体大胶囊 (开始合并文件)
        self.btn_merge = QPushButton("开始合并文件")
        self.btn_merge.setFixedHeight(54)
        self.btn_merge.setStyleSheet("""
            QPushButton {
                background-color: #C4EED0;
                color: #072711;
                font-size: 15px;
                font-weight: bold;
                border-radius: 26px;
                border: none;
            }
            QPushButton:hover {
                background-color: #AEE6BE;
            }
            QPushButton:pressed {
                background-color: #9BDDB0;
            }
        """)
        self.btn_merge.clicked.connect(self._on_merge_click)
        layout.addWidget(self.btn_merge)

        # 取消按钮
        self.btn_cancel = QPushButton("取消当前任务")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #FCE8E6;
                color: #B3261E;
                font-size: 12px;
                font-weight: bold;
                border-radius: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #FAD2CF;
            }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel_click)
        layout.addWidget(self.btn_cancel)

        layout.addStretch(1)

        scroll.setWidget(content)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(scroll)
        return sidebar

    def _build_right_main_card(self) -> QWidget:
        """构建右侧悬浮主卡片，集成支持焦点蓝框的药丸搜索框。"""
        card = QFrame()
        card.setObjectName("RightMainCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        self.badge_total = QLabel("已加载 0 项")
        self.badge_total.setStyleSheet("""
            background-color: #E9EEF6;
            color: #444746;
            border-radius: 14px;
            padding: 6px 14px;
            font-weight: bold;
            font-size: 12px;
        """)
        top_bar.addWidget(self.badge_total)

        self.badge_checked = QLabel("已勾选 0 项")
        self.badge_checked.setStyleSheet("""
            background-color: #D3E3FD;
            color: #041E49;
            border-radius: 14px;
            padding: 6px 14px;
            font-weight: bold;
            font-size: 12px;
        """)
        top_bar.addWidget(self.badge_checked)

        top_bar.addStretch(1)

        # ★★★ 核心升级：装配获得焦点后自动显示 2px 蓝色框的 M3SearchBox 药丸搜索栏 ★★★
        self.search_pill = M3SearchBox(placeholder="输入部分文件名快速过滤", parent=card)
        self.txt_search = self.search_pill.line_edit
        self.txt_search.textChanged.connect(self._on_tree_search_changed)
        top_bar.addWidget(self.search_pill)

        layout.addLayout(top_bar)

        # 装配 M3 高性能树组件
        self.tree_view = TreeView(
            parent=card,
            on_check=self._update_badges,
            on_expand=None,
            on_clear=self._on_clear_list,
            on_mode_change=lambda flat: self.chk_flat.setChecked(flat),
            on_delete=self._on_delete_selected_paths,
        )
        layout.addWidget(self.tree_view, stretch=1)

        return card

    def _build_bottom_status_bar(self) -> QWidget:
        """构建底部全局状态栏。"""
        bar = QWidget()
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #D5DBE3;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0B57D0;
                border-radius: 2px;
            }
        """)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #727775; font-size: 12px;")
        layout.addWidget(self.status_label)

        return bar

    # -------------------------------------------------------------------------
    # ★ 全局事件过滤器拦截，保证 100% 拖放响应
    # -------------------------------------------------------------------------
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.DragEnter:
            drag_event: QDragEnterEvent = event
            if drag_event.mimeData().hasUrls():
                drag_event.acceptProposedAction()
                self._set_status("松开鼠标即可追加载入所选文件/文件夹...", "#0B57D0")
                return True
        elif event.type() == QEvent.DragMove:
            drag_event: QDragMoveEvent = event
            if drag_event.mimeData().hasUrls():
                drag_event.acceptProposedAction()
                return True
        elif event.type() == QEvent.Drop:
            drop_event: QDropEvent = event
            urls = drop_event.mimeData().urls()
            raw_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            if raw_paths:
                drop_event.acceptProposedAction()
                self._process_dropped_files(raw_paths)
                return True
        return super().eventFilter(watched, event)

    def _process_dropped_files(self, raw_paths: List[str]) -> None:
        """核心拖放文件归并调度。"""
        paths = [os.path.abspath(p) for p in raw_paths if p]
        if not paths:
            return

        dirs = [p for p in paths if os.path.isdir(p)]
        files = [p for p in paths if os.path.isfile(p)]

        if dirs:
            self.txt_root.setText(os.path.abspath(dirs[0]))
            self._pending_extra_files = files
            self._set_status(f"检索到 {len(dirs)} 个目录，开始扫描追加...", "#0B57D0")
            self._on_scan_click(append=True)
        elif files:
            self._append_files(files)

    def _append_files(self, files: List[str]):
        """独立外部文件的无缝去重追加。"""
        new_files = [
            os.path.abspath(p) for p in files
            if os.path.abspath(p) not in self.known_files and os.path.isfile(p)
        ]

        if not new_files:
            self._set_status(f"拖入的 {len(files)} 个文件均已存在（自动去重）。", "#F59E0B")
            return

        if self.model is None or self.model.root is None:
            try:
                common = os.path.commonpath(new_files)
            except ValueError:
                common = os.path.dirname(new_files[0])

            if os.path.isfile(common) or not os.path.isdir(common):
                common = os.path.dirname(common)
            if not common:
                common = os.path.dirname(new_files[0])

            file_list = []
            for p in new_files:
                try:
                    size = os.path.getsize(p)
                except OSError:
                    size = 0
                file_list.append((p, size))

            self.model = TreeModel()
            self.model.build(common, file_list)
            self.known_files = set(p for p, _ in file_list)

            self.expanded.clear()
            self.expanded.add(common)
            self.txt_root.setText(common)

            self.tree_view.bind_model(self.model, self.expanded, common)
            self.tree_view.set_flat_view(True)
            self.chk_flat.setChecked(True)
            self.tree_view.render()
            self._update_badges()
            self._set_status(f"已直接载入 {len(new_files)} 个独立文件。", "#146C2E")
            return

        previous_checked = set(self.model.checked_files)
        all_files = [
            (p, node.size) for p, node in self.model.path_to_node.items()
            if not node.is_dir
        ]
        for p in new_files:
            try:
                size = os.path.getsize(p)
            except OSError:
                size = 0
            all_files.append((p, size))

        root = self.txt_root.text().strip() or os.path.dirname(new_files[0])
        all_paths = [p for p, _ in all_files]
        try:
            common = os.path.commonpath(all_paths)
        except ValueError:
            common = root

        if os.path.isfile(common) or not os.path.isdir(common):
            common = os.path.dirname(common)
        if not common:
            common = root

        new_model = TreeModel()
        new_model.build(common, all_files)
        new_model.sync_checked_states(previous_checked)

        self.model = new_model
        self.known_files.update(new_files)
        self.txt_root.setText(common)
        self.expanded.add(common)

        self.tree_view.bind_model(self.model, self.expanded, common)
        self.tree_view.render()
        self._update_badges()
        self._set_status(f"成功追加 {len(new_files)} 个文件，当前共 {len(all_files)} 项。", "#146C2E")

    # -------------------------------------------------------------------------
    # 扫描任务执行
    # -------------------------------------------------------------------------
    def _on_scan_click(self, append: bool = False) -> None:
        if self.task_thread and self.task_thread.is_alive():
            QMessageBox.information(self, "提示", "已有任务正在执行中，请等待完成或取消。")
            return

        root = self.txt_root.text().strip()
        if not root or not os.path.isdir(root):
            QMessageBox.critical(self, "错误", "请先选择有效的根文件夹。")
            return

        self.cancel_flag.clear()
        self._set_status("正在全速检索并扫描目录结构...", "#0B57D0")
        self.progress_bar.setValue(0)

        options = {
            "recurse": self.chk_recurse.isChecked(),
            "extensions_raw": self.txt_ext.text().strip(),
            "include_no_ext": self.chk_no_ext.isChecked(),
        }

        self._scan_append = append

        class QueueAdapter:
            def __init__(self, bridge):
                self.bridge = bridge
            def put(self, item):
                self.bridge.sig_message.emit(item[0], item[1])

        self.task_thread = threading.Thread(
            target=scan_worker,
            args=(root, options, QueueAdapter(self.bridge), self.cancel_flag),
            daemon=True,
        )
        self.task_thread.start()

    def _on_scan_done(self, collected: List) -> None:
        append = self._scan_append
        self._scan_append = False

        if self._pending_extra_files:
            existing = {p for p, _ in collected}
            for p in self._pending_extra_files:
                if p not in existing:
                    try:
                        size = os.path.getsize(p)
                    except OSError:
                        size = 0
                    collected.append((p, size))
            self._pending_extra_files = None

        if append and self.model is not None and self.model.root is not None:
            previous_checked = set(self.model.checked_files)
            old_files = [
                (p, n.size) for p, n in self.model.path_to_node.items() if not n.is_dir
            ]
            old_set = set(p for p, _ in old_files)
            new_files = [(p, s) for p, s in collected if p not in old_set]
            all_files = old_files + new_files

            all_paths = [p for p, _ in all_files]
            try:
                common = os.path.commonpath(all_paths)
            except ValueError:
                common = self.txt_root.text().strip()

            if os.path.isfile(common) or not os.path.isdir(common):
                common = os.path.dirname(common)

            new_model = TreeModel()
            new_model.build(common, all_files)
            new_model.sync_checked_states(previous_checked)

            self.model = new_model
            self.known_files = set(all_paths)
            self.txt_root.setText(common)
            self.expanded.add(common)
        else:
            root_path = self.txt_root.text().strip()
            self.model = TreeModel()
            self.model.build(root_path, collected)
            self.known_files = set(p for p, _ in collected)

            self.expanded.clear()
            self.expanded.add(root_path)

        self.tree_view.bind_model(self.model, self.expanded, self.txt_root.text().strip())
        self.tree_view.render()
        self._update_badges()
        self._set_status(f"扫描完成，已加载 {len(self.model.all_files())} 个文件。", "#146C2E")
        self.progress_bar.setValue(100)

    # -------------------------------------------------------------------------
    # 条目删除与清空
    # -------------------------------------------------------------------------
    def _on_delete_selected_paths(self, paths: List[str]) -> None:
        if not paths or not self.model or not self.model.root:
            return

        affected_count = 0
        for p in paths:
            node = self.model.get_node(p)
            if node:
                if node.is_dir:
                    affected_count += len(list(node.iter_files()))
                else:
                    affected_count += 1

        if affected_count == 0:
            return

        msg = (
            f"确定要从当前列表中移除选中的 {len(paths)} 个条目吗？\n"
            f"（共计移除 {affected_count} 个文件，磁盘源文件不受影响）"
        )
        if QMessageBox.question(self, "移除确认", msg) != QMessageBox.Yes:
            return

        removed_count, removed_files = self.model.remove_paths(paths)

        for rf in removed_files:
            self.known_files.discard(rf)

        valid_paths = set(self.model.path_to_node.keys())
        self.expanded.intersection_update(valid_paths)

        if not self.model.all_files():
            self.model = None
            self.expanded.clear()
            self.known_files.clear()
            self.txt_root.setText("")
            self.tree_view.bind_model(None, self.expanded, "")
            self.tree_view.render()
            self._update_badges()
            self._set_status("已移除所有条目，列表为空。", "#727775")
            return

        self.tree_view.render()
        self._update_badges()
        self._set_status(f"成功从合并列表中剔除 {removed_count} 个文件。", "#146C2E")

    def _on_clear_list(self) -> None:
        if not self.model or not self.model.root:
            QMessageBox.information(self, "提示", "列表已处于清空状态。")
            return

        if QMessageBox.question(self, "清空确认", "确定要清空已加载的全部文件列表吗？") != QMessageBox.Yes:
            return

        self.model = None
        self.expanded.clear()
        self.known_files.clear()
        self.txt_root.setText("")
        self.tree_view.bind_model(None, self.expanded, "")
        self.tree_view.render()
        self._update_badges()
        self._set_status("列表已全量清空。", "#727775")

    # -------------------------------------------------------------------------
    # 常用文件选择与界面响应
    # -------------------------------------------------------------------------
    def _choose_root_folder(self) -> None:
        initial = self.txt_root.text().strip() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "选择目标根文件夹", initial)
        if folder:
            self.txt_root.setText(os.path.abspath(folder))
            self._on_scan_click(append=False)

    def _choose_output_file(self) -> None:
        initial = self.txt_out.text().strip() or os.path.abspath("./" + DEFAULT_OUTPUT_NAME)
        path, _ = QFileDialog.getSaveFileName(
            self, "指定合并导出文本路径", initial, "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if path:
            self.txt_out.setText(os.path.abspath(path))

    def _on_toggle_flat_view(self, checked: bool) -> None:
        self.tree_view.set_flat_view(checked)
        self.tree_view.render()

    def _set_status(self, text: str, color: str = "#727775") -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    def _update_badges(self) -> None:
        if self.model is None or self.model.root is None:
            total = 0
            checked = 0
        else:
            total = len(self.model.all_files())
            checked = len(self.model.checked_files)
        self.badge_total.setText(f"已加载 {total} 项")
        self.badge_checked.setText(f"已勾选 {checked} 项")

    def _on_apply_filter(self) -> None:
        if not self.txt_root.text().strip():
            QMessageBox.information(self, "提示", "请先选择根文件夹以进行过滤扫描。")
            return
        self._on_scan_click(append=False)

    def _on_tree_search_changed(self) -> None:
        self.search_timer.start(TREE_SEARCH_DEBOUNCE_MS)

    def _apply_tree_search(self) -> None:
        self.tree_view.set_search_text(self.txt_search.text())
        self.tree_view.render()

    # -------------------------------------------------------------------------
    # 合并任务调度
    # -------------------------------------------------------------------------
    def _on_merge_click(self) -> None:
        if self.task_thread and self.task_thread.is_alive():
            QMessageBox.information(self, "提示", "已有任务正在执行，请稍候。")
            return

        if not self.model or not self.model.root:
            QMessageBox.warning(self, "提示", "当前列表为空，请先载入文件。")
            return

        checked = self.model.checked_files
        if not checked:
            QMessageBox.warning(self, "提示", "请至少勾选一个文件进行合并导出。")
            return

        output = self.txt_out.text().strip()
        if not output:
            QMessageBox.critical(self, "错误", "请指定导出的目标文件路径。")
            return

        if os.path.exists(output):
            if QMessageBox.question(self, "覆盖确认", f"输出目标文件已存在:\n{output}\n\n是否确认覆盖写入？") != QMessageBox.Yes:
                return

        self.cancel_flag.clear()
        self.progress_bar.setValue(0)
        self._set_status("正在合并写入目标文件，请稍候...", "#0B57D0")

        force_enc = ENCODING_MAP.get(self.cmb_encoding.currentText(), None)
        options = {
            "root_dir": self.txt_root.text().strip(),
            "extensions_raw": self.txt_ext.text().strip(),
            "include_no_ext": self.chk_no_ext.isChecked(),
            "recurse": self.chk_recurse.isChecked(),
            "pattern": self.txt_pattern.text().strip(),
            "use_regex": self.chk_regex.isChecked(),
        }

        file_sizes = {
            p: node.size for p, node in self.model.path_to_node.items()
            if not node.is_dir
        }

        class QueueAdapter:
            def __init__(self, bridge):
                self.bridge = bridge
            def put(self, item):
                self.bridge.sig_message.emit(item[0], item[1])

        self.task_thread = threading.Thread(
            target=merge_worker,
            args=(
                list(checked),
                output,
                force_enc,
                options,
                file_sizes,
                QueueAdapter(self.bridge),
                self.cancel_flag,
            ),
            daemon=True,
        )
        self.task_thread.start()

    def _on_cancel_click(self) -> None:
        if self.task_thread and self.task_thread.is_alive():
            self.cancel_flag.set()
            self._set_status("已发出取消指令，正在终止工作线程...", "#F59E0B")
        else:
            QMessageBox.information(self, "提示", "当前没有正在执行的后台任务。")

    # -------------------------------------------------------------------------
    # 异步线程消息分发响应
    # -------------------------------------------------------------------------
    def _handle_worker_message(self, msg_type: str, payload: object) -> None:
        if msg_type == "status":
            text, color = payload
            self._set_status(text, color)

        elif msg_type == "scan_progress":
            count, current = payload
            self._set_status(f"已检索 {count} 个文件... 正在扫描: {current}", "#0B57D0")

        elif msg_type == "scan_done":
            self._on_scan_done(payload)

        elif msg_type == "merge_progress":
            processed, total, current = payload
            pct = int(processed / total * 100) if total else 0
            self.progress_bar.setValue(pct)
            self._set_status(f"正在合并 [{processed}/{total}] ({pct}%) - {current}", "#0B57D0")

        elif msg_type == "merge_done":
            output, processed, failed_count, failed_list = payload
            self.progress_bar.setValue(100)
            if failed_count == 0:
                self._set_status(f"合并任务完成！共导出 {processed} 个文件。", "#146C2E")
            else:
                self._set_status(
                    f"合并完成（部分存在读取错误）。成功: {processed}，失败: {failed_count}。",
                    "#F59E0B",
                )
            info = f"合并处理完成！\n\n成功文件数: {processed}\n读取异常数: {failed_count}\n输出文件路径: {output}"
            if failed_count > 0:
                details = "\n".join(f"- {p}: {e}" for p, e in failed_list[:10])
                if failed_count > 10:
                    details += f"\n... 以及其他 {failed_count - 10} 项"
                info += f"\n\n失败明细:\n{details}"
            QMessageBox.information(self, "完成", info)

        elif msg_type == "error":
            self._set_status("任务异常中断", "#B3261E")
            QMessageBox.critical(self, "运行异常", str(payload))


# =============================================================================
# 全局启动入口
# =============================================================================
def main():
    app = QApplication(sys.argv)
    window = MergeToolApp()
    window.show()
    sys.exit(app.exec())