# -*- coding: utf-8 -*-
"""
基于 PySide6 (Qt) 深度构建的现代 Material Design 3 目录树组件（工业级生产就绪版）。

================================ 核心升级与重构要点 ================================
1. 【彻底根治右键菜单圆角四周的白色尖角】：
   - 在 `_build_context_menu` 中为 `QMenu` 开启 `Qt.WA_TranslucentBackground` 半透明通道，
     通知底层渲染引擎启用真正的 Alpha 混合合成。
   - 注入 `Qt.FramelessWindowHint` 与 `Qt.NoDropShadowWindowHint` 窗口标志，
     从底层物理阻断 Windows 操作系统原生矩形外框与原生不透明阴影的绘制，
     使得 12px 圆角外侧的四个直角区域渲染为 100% 透明通道，与下拉菜单视觉表现完美统一！
2. 彻底解决“图标距离名字太远”的排版断层缺陷：
   - 彻底废除在字符串开头硬塞多个空格的错误机制，直接使用 `item.setText(0, node.name)`；
   - 在 `M3TreeItemDelegate` 中建立基于层级深度的单调紧凑几何排版体系：
     * 复选框：严格固定在最左侧 `base_x + 6`；
     * 随层级平滑缩进：`indent_offset = depth * 18`；
     * 展开/折叠大三角：`base_x + 28 + indent_offset`；
     * 文件夹/文件图标：紧随三角之后 `base_x + 48 + indent_offset`；
     * 文件名文字：紧贴图标之后 `base_x + 72 + indent_offset`（间距仅 6px，紧凑自然！）。
3. 彻底抹杀高亮时的橘黄色虚线框：
   - 自定义代理样式 `NoFocusProxyStyle` 在 C++ 原语级别直接抛弃 `PE_FrameFocusRect` 焦点绘制，
     配合委托全权接管整行背景渲染，橘黄色虚线 100% 彻底蒸发！
4. 恢复 StrongFocus：保证 Delete 键、空格键 100% 能够灵敏响应。
"""

import os
from typing import Callable, Dict, List, Optional, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QHeaderView, QAbstractItemView, QStyledItemDelegate, QStyle, QProxyStyle
)
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor, QMouseEvent
from PySide6.QtCore import Qt, QSize, QRect

from merge_tool.constants import (
    M3_TREE_ROW_HEIGHT,
    SVG_FOLDER,
    SVG_FILE,
    SVG_CHECKED,
    SVG_UNCHECKED,
    SVG_PARTIAL,
    SVG_EXPAND_MORE,
    SVG_CHEVRON_RIGHT,
    create_svg_icon,
    create_svg_pixmap,
    GLOBAL_FONT_FAMILY,
)
from merge_tool.file_utils import human_size
from merge_tool.tree_model import CheckState, TreeModel, Node


class NoFocusProxyStyle(QProxyStyle):
    """
    ★ 核心代理样式：在 C++ 原语级别直接抹杀 Windows 绘制任何焦点虚线框。
    
    原理：当控件或列表项获得焦点时，Windows 默认样式会调用 QStyle.PE_FrameFocusRect
    绘制一条高对比度的虚线轮廓矩形。本类拦截该图元绘制事件并直接返回，彻底消除虚线。
    """

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element == QStyle.PE_FrameFocusRect:
            return  # 彻底丢弃焦点虚线，绝不绘制
        super().drawPrimitive(element, option, painter, widget)


class M3TreeItemDelegate(QStyledItemDelegate):
    """
    ★ 工业级树项目渲染委托：
    1. 完全接管整行背景绘制，物理级阻断 Windows 绘制橘黄色虚线；
    2. 主排内部图元严格采用单调递增坐标排版，图标与文件名保持自然紧凑间距（6~8px）。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # 预先生成高性能矢量像素图缓存，避免高频滚动时重复解析 SVG
        self.pix_checked = create_svg_pixmap(SVG_CHECKED, QSize(18, 18))
        self.pix_unchecked = create_svg_pixmap(SVG_UNCHECKED, QSize(18, 18))
        self.pix_partial = create_svg_pixmap(SVG_PARTIAL, QSize(18, 18))
        self.pix_folder = create_svg_pixmap(SVG_FOLDER, QSize(18, 18))
        self.pix_file = create_svg_pixmap(SVG_FILE, QSize(18, 18))
        self.pix_arrow_open = create_svg_pixmap(SVG_EXPAND_MORE, QSize(16, 16))
        self.pix_arrow_close = create_svg_pixmap(SVG_CHEVRON_RIGHT, QSize(16, 16))

    def paint(self, painter: QPainter, option, index) -> None:
        """高性能绘制单行树节点内容。"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = option.rect

        # ★ 关键：无论哪一列，均由我们自己绘制高亮背景，彻底抛弃系统虚线框绘制
        is_selected = bool(option.state & QStyle.State_Selected)
        if is_selected:
            painter.fillRect(rect, QColor("#D3E3FD"))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(rect, QColor("#F5F8FC"))
        else:
            painter.fillRect(rect, QColor("#FFFFFF"))

        item = self.parent().itemFromIndex(index)
        if not item:
            painter.restore()
            return

        # ==================== 第 0 列：主树排 ====================
        if index.column() == 0:
            node_state = item.data(0, Qt.UserRole)
            is_dir = item.data(0, Qt.UserRole + 1)
            depth = item.data(0, Qt.UserRole + 2) or 0
            is_expanded = item.isExpanded()
            display_text = item.text(0)

            base_x = rect.x()
            mid_y = rect.y() + (rect.height() - 18) // 2

            # [1] 最左侧 100% 优先绘制复选框 (固定在 x + 6)
            if node_state == "checked":
                chk_pix = self.pix_checked
            elif node_state == "partial":
                chk_pix = self.pix_partial
            else:
                chk_pix = self.pix_unchecked
            painter.drawPixmap(base_x + 6, mid_y, chk_pix)

            indent_offset = depth * 18

            # [2] 绘制 16px 饱满大三角 (仅目录有)
            if is_dir:
                tri_pix = self.pix_arrow_open if is_expanded else self.pix_arrow_close
                tri_x = base_x + 28 + indent_offset
                painter.drawPixmap(tri_x, rect.y() + (rect.height() - 16) // 2, tri_pix)

            # [3] 紧接着绘制文件夹或文件卡片图标
            icon_pix = self.pix_folder if is_dir else self.pix_file
            icon_x = base_x + 48 + indent_offset
            painter.drawPixmap(icon_x, mid_y, icon_pix)

            # [4] ★ 文件名文字紧随其后 (间距 6px，紧凑自然，绝无大片空白！)
            text_x = icon_x + 24
            text_rect = QRect(text_x, rect.y(), rect.width() - (text_x - rect.x()), rect.height())
            text_color = QColor("#041E49") if is_selected else QColor("#1F1F1F")
            painter.setPen(text_color)
            painter.setFont(option.font)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)

        # ==================== 第 1 列：大小列 ====================
        elif index.column() == 1:
            size_text = item.text(1)
            if size_text:
                text_rect = QRect(rect.x(), rect.y(), rect.width() - 8, rect.height())
                text_color = QColor("#041E49") if is_selected else QColor("#444746")
                painter.setPen(text_color)
                painter.setFont(option.font)
                painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, size_text)

        painter.restore()


class TreeView(QWidget):
    """
    符合 Google Material Design 3 规范的高级目录树组件。
    复选框绝对位于整行最左端，整行连贯选择高亮，杜绝虚线框，间距紧凑自然。
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_check: Optional[Callable[[], None]] = None,
        on_expand: Optional[Callable[[str, bool], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        on_mode_change: Optional[Callable[[bool], None]] = None,
        on_delete: Optional[Callable[[List[str]], None]] = None,
    ):
        super().__init__(parent)
        self.on_check = on_check
        self.on_expand = on_expand
        self.on_clear = on_clear
        self.on_mode_change = on_mode_change
        self.on_delete = on_delete

        self.model: Optional[TreeModel] = None
        self.expanded: Set[str] = set()
        self.root_dir: str = ""
        self.flat_view: bool = False
        self.search_text: str = ""

        # 路径与 QTreeWidgetItem 双向索引表
        self.path_to_item: Dict[str, QTreeWidgetItem] = {}
        self.item_to_path: Dict[QTreeWidgetItem, str] = {}

        self._build_ui()
        self._build_context_menu()

    def _build_ui(self) -> None:
        """初始化树控件排版与表头。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["文件与文件夹名称", "大小"])

        # ★ 应用原生代理样式彻底消灭橘黄虚线
        self.tree.setStyle(NoFocusProxyStyle(self.tree.style()))

        # 恢复 StrongFocus：保证 Delete 键与空格键 100% 能够响应
        self.tree.setFocusPolicy(Qt.StrongFocus)

        # 开启整行连贯选择高亮
        self.tree.setAllColumnsShowFocus(True)

        # 关闭原生容易错位的树枝装饰器
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)

        # 安装自定义紧凑渲染委托
        self.delegate = M3TreeItemDelegate(self.tree)
        self.tree.setItemDelegate(self.delegate)

        # 表头配置：支持鼠标自由拖拽调整列宽
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # 第 0 列可自由拖拽
        header.resizeSection(0, 640)                             # 默认舒展宽度
        header.setSectionResizeMode(1, QHeaderView.Interactive)  # 第 1 列大小可自由拖拽
        header.resizeSection(1, 120)                             # 紧凑合理的 120px 大小列

        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        # 信号连接
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_custom_context_menu)

        layout.addWidget(self.tree)

    def _build_context_menu(self) -> None:
        """
        ★ 核心修复方法：构建纯净 M3 风格右键菜单，彻底根除圆角四周白色尖角！
        
        原理详述：
        1. 注入 Qt.WA_TranslucentBackground 属性：
           通知底层窗口系统启用 Alpha 透明混合通道，使 Windows 窗口管理器（DWM）
           将圆角外侧原本的矩形填充像素完全渲染为 100% 透明，杜绝任何白色死角！
        2. 注入 Qt.FramelessWindowHint 与 Qt.NoDropShadowWindowHint 窗口标志：
           彻底剥离 Windows 系统的原生直角矩形边框与原生矩形阴影，
           从底层物理机制上避免系统绘制直角黑边或杂色底角。
        3. QSS 配套 12px 大圆角与 #CBD5E1 优雅微边框，与编码选择弹窗实现 100% 视觉对齐！
        """
        self.menu = QMenu(self)

        # ★★★ 终极消除外角杂色核心代码 ★★★
        self.menu.setAttribute(Qt.WA_TranslucentBackground, True)
        self.menu.setWindowFlags(
            self.menu.windowFlags()
            | Qt.FramelessWindowHint
            | Qt.NoDropShadowWindowHint
        )

        # 挂载符合 Material Design 3 规范的高清无杂边样式表
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
            QMenu::separator {
                height: 1px;
                background: #EFF3F8;
                margin: 4px 8px;
            }
        """)

        # 菜单动作项装配
        act_check_all = self.menu.addAction("全选所有文件")
        act_check_all.triggered.connect(lambda: self._menu_check_all(False))

        act_invert_all = self.menu.addAction("反选所有文件")
        act_invert_all.triggered.connect(lambda: self._menu_invert(False))

        act_uncheck_all = self.menu.addAction("全不选所有文件")
        act_uncheck_all.triggered.connect(lambda: self._menu_uncheck_all(False))

        self.menu.addSeparator()

        act_check_sel = self.menu.addAction("全选选中条目")
        act_check_sel.triggered.connect(lambda: self._menu_check_all(True))

        act_invert_sel = self.menu.addAction("反选选中条目")
        act_invert_sel.triggered.connect(lambda: self._menu_invert(True))

        act_uncheck_sel = self.menu.addAction("全不选选中条目")
        act_uncheck_sel.triggered.connect(lambda: self._menu_uncheck_all(True))

        self.menu.addSeparator()

        act_expand_all = self.menu.addAction("展开所有文件夹")
        act_expand_all.triggered.connect(self._expand_all)

        act_collapse_all = self.menu.addAction("折叠所有文件夹")
        act_collapse_all.triggered.connect(self._collapse_all)

        self.menu.addSeparator()

        act_delete = self.menu.addAction("从列表中移除选中项 (Delete)")
        act_delete.triggered.connect(self._delete_selected)

        self.menu.addSeparator()

        act_clear = self.menu.addAction("清空全部文件列表")
        act_clear.triggered.connect(lambda: self.on_clear() if self.on_clear else None)

    # =========================================================================
    # 状态与模型绑定
    # =========================================================================
    def bind_model(self, model: Optional[TreeModel], expanded: Set[str], root_dir: str) -> None:
        """绑定数据模型与展开状态集。"""
        self.model = model
        self.expanded = expanded
        self.root_dir = os.path.abspath(root_dir) if root_dir else ""

    def set_flat_view(self, flat: bool) -> None:
        """切换平铺模式状态。"""
        self.flat_view = flat

    def set_search_text(self, text: str) -> None:
        """更新过滤检索词。"""
        self.search_text = (text or "").strip().lower()

    # =========================================================================
    # 渲染引擎
    # =========================================================================
    def render(self) -> None:
        """根据当前模式全量重建视图树。"""
        self.tree.clear()
        self.path_to_item.clear()
        self.item_to_path.clear()

        if self.model is None or self.model.root is None:
            return

        # 禁用重绘刷新，极大降低大规模节点挂载时的界面闪烁与卡顿
        self.tree.setUpdatesEnabled(False)
        try:
            if self.flat_view:
                self._render_flat()
            else:
                self._render_tree()
        finally:
            self.tree.setUpdatesEnabled(True)

    def _render_flat(self) -> None:
        """平铺扁平模式渲染。"""
        assert self.model is not None
        all_files = sorted(self.model.all_files(), key=lambda p: p.lower())

        for path in all_files:
            node = self.model.get_node(path)
            if node is None or node.is_dir:
                continue

            if self.search_text and self.search_text not in node.name.lower():
                continue

            item = QTreeWidgetItem(self.tree)
            self._setup_item(item, node, depth=0, is_flat=True)

    def _render_tree(self) -> None:
        """多层级树形模式递归渲染。"""
        assert self.model is not None and self.model.root is not None
        root = self.model.root
        self.expanded.add(root.path)

        root_item = QTreeWidgetItem(self.tree)
        self._setup_item(root_item, root, depth=0, is_flat=False)
        self._render_children(root_item, root, depth=1)

    def _render_children(self, parent_item: QTreeWidgetItem, dir_node: Node, depth: int) -> None:
        """递归挂载子目录与子文件。"""
        for child in dir_node.children:
            if child.is_dir:
                if self.search_text and not self._dir_matches_search(child):
                    continue
                item = QTreeWidgetItem(parent_item)
                self._setup_item(item, child, depth=depth, is_flat=False)
                self._render_children(item, child, depth + 1)

        for child in dir_node.children:
            if not child.is_dir:
                if self.search_text and self.search_text not in child.name.lower():
                    continue
                item = QTreeWidgetItem(parent_item)
                self._setup_item(item, child, depth=depth, is_flat=False)

    def _get_state_str(self, state: CheckState) -> str:
        """转换枚举为渲染委托能够解析的字符串标记。"""
        if state == CheckState.CHECKED:
            return "checked"
        if state == CheckState.PARTIAL:
            return "partial"
        return "unchecked"

    def _setup_item(self, item: QTreeWidgetItem, node: Node, depth: int, is_flat: bool) -> None:
        """写入行元数据与显示文本。"""
        item.setData(0, Qt.UserRole, self._get_state_str(node.state))
        item.setData(0, Qt.UserRole + 1, node.is_dir)
        item.setData(0, Qt.UserRole + 2, depth)

        # ★ 关键：直接传递纯净文件名，绝对不塞硬空格，彻底杜绝图标距离文字过远！
        if is_flat and self.root_dir:
            try:
                display_name = os.path.relpath(node.path, self.root_dir)
            except ValueError:
                display_name = node.name
        else:
            display_name = node.name

        item.setText(0, display_name)

        if not node.is_dir:
            item.setText(1, human_size(node.size))

        self.path_to_item[node.path] = item
        self.item_to_path[item] = node.path

        if node.is_dir:
            if self.search_text or node.path in self.expanded:
                item.setExpanded(True)

    def _dir_matches_search(self, dir_node: Node) -> bool:
        """判断当前目录或其下属文件是否命中过滤关键词。"""
        if self.search_text in dir_node.name.lower():
            return True
        for f in dir_node.iter_files():
            if self.search_text in f.name.lower():
                return True
        return False

    def refresh_all(self) -> None:
        """快速局部刷新所有复选框状态，不重构 DOM 结构以获得极高响应度。"""
        if self.model is None:
            return
        for path, item in self.path_to_item.items():
            node = self.model.get_node(path)
            if node:
                item.setData(0, Qt.UserRole, self._get_state_str(node.state))
        self.tree.viewport().update()

    # =========================================================================
    # 事件处理（基于单调递增几何偏移量精准触发）
    # =========================================================================
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """单机项目事件命中测试。"""
        if self.model is None:
            return
        path = self.item_to_path.get(item)
        if not path:
            return
        node = self.model.get_node(path)
        if not node:
            return

        if column == 0:
            pos = self.tree.mapFromGlobal(self.cursor().pos())
            rect = self.tree.visualItemRect(item)
            rel_x = pos.x() - rect.x()

            # [0 ~ 26px]：精确命中最左端复选框区域
            if rel_x <= 26:
                if node.is_dir:
                    self.model.toggle_dir(path)
                else:
                    self.model.toggle_file(path)
                self.refresh_all()
                if self.on_check:
                    self.on_check()
                return

            depth = item.data(0, Qt.UserRole + 2) or 0
            indent_offset = depth * 18
            tri_start = 28 + indent_offset
            tri_end = tri_start + 20

            # 精确命中折叠展开三角区域 (仅目录生效)
            if tri_start <= rel_x <= tri_end and node.is_dir:
                self.toggle_expand(path)
                return

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """双击文件夹整行任意区域即刻平滑展开/折叠。"""
        item = self.tree.itemAt(event.pos())
        if item and self.model:
            path = self.item_to_path.get(item)
            if path:
                node = self.model.get_node(path)
                if node and node.is_dir:
                    self.toggle_expand(path)
                    event.accept()
                    return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        """键盘按键事件：保证 Delete 键与空格键 100% 畅通无阻响应。"""
        if event.key() == Qt.Key_Delete:
            self._delete_selected()
            event.accept()
        elif event.key() == Qt.Key_Space:
            self._toggle_selected_items()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _toggle_selected_items(self) -> None:
        """空格键批量切换当前已选中项的勾选状态。"""
        if not self.model:
            return
        for item in self.tree.selectedItems():
            path = self.item_to_path.get(item)
            if path:
                node = self.model.get_node(path)
                if node:
                    if node.is_dir:
                        self.model.toggle_dir(path)
                    else:
                        self.model.toggle_file(path)
        self.refresh_all()
        if self.on_check:
            self.on_check()

    def toggle_expand(self, path: str) -> None:
        """切换单个目录节点的展开与折叠。"""
        if not self.model:
            return
        node = self.model.get_node(path)
        if not node or not node.is_dir:
            return

        item = self.path_to_item.get(path)
        if not item:
            return

        is_exp = not item.isExpanded()
        item.setExpanded(is_exp)
        if is_exp:
            self.expanded.add(path)
        else:
            self.expanded.discard(path)
        if self.on_expand:
            self.on_expand(path, is_exp)
        self.tree.viewport().update()

    def _on_custom_context_menu(self, pos) -> None:
        """弹出消除杂边后的高级悬浮右键菜单。"""
        self.menu.exec(self.tree.mapToGlobal(pos))

    def _delete_selected(self) -> None:
        """触发删除当前选中的行。"""
        paths = [
            self.item_to_path[item]
            for item in self.tree.selectedItems()
            if item in self.item_to_path
        ]
        if paths and self.on_delete:
            self.on_delete(paths)

    def _expand_all(self) -> None:
        """全部展开。"""
        if not self.model or not self.model.root:
            return
        if self.flat_view:
            self.flat_view = False
            if self.on_mode_change:
                self.on_mode_change(False)
        for path, node in self.model.path_to_node.items():
            if node.is_dir:
                self.expanded.add(path)
        self.render()

    def _collapse_all(self) -> None:
        """全部折叠。"""
        if not self.model or not self.model.root:
            return
        if self.flat_view:
            self.flat_view = False
            if self.on_mode_change:
                self.on_mode_change(False)
        self.expanded.clear()
        if self.model.root.path:
            self.expanded.add(self.model.root.path)
        self.render()

    def _menu_check_all(self, only_selected: bool) -> None:
        """全选。"""
        if not self.model:
            return
        targets = self._resolve_targets(only_selected)
        self.model.check_all(targets)
        self.refresh_all()
        if self.on_check:
            self.on_check()

    def _menu_uncheck_all(self, only_selected: bool) -> None:
        """全不选。"""
        if not self.model:
            return
        targets = self._resolve_targets(only_selected)
        self.model.uncheck_all(targets)
        self.refresh_all()
        if self.on_check:
            self.on_check()

    def _menu_invert(self, only_selected: bool) -> None:
        """反选。"""
        if not self.model:
            return
        targets = self._resolve_targets(only_selected)
        self.model.invert_all(targets)
        self.refresh_all()
        if self.on_check:
            self.on_check()

    def _resolve_targets(self, only_selected: bool) -> Optional[Set[str]]:
        """计算操作的目标文件集合。"""
        if not only_selected:
            return None
        selected_items = self.tree.selectedItems()
        if not selected_items or not self.model:
            return set()
        files: Set[str] = set()
        for item in selected_items:
            path = self.item_to_path.get(item)
            if path:
                node = self.model.get_node(path)
                if node:
                    if node.is_dir:
                        files.update(self.model.collect_files_under(path))
                    else:
                        files.add(path)
        return files