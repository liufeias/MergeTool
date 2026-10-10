# -*- coding: utf-8 -*-
"""
树的数据模型模块（企业级生产就绪版）。

================================ 核心 Bug 修复说明 ================================
修复勾选父文件夹后，直接子文件夹及多层嵌套子文件夹未显示选中的缺陷：
1. 修复根因：
   原 `set_dir_checked` 仅遍历了 `node.iter_files()`（仅叶子文件）和更新了当前被点击目录的 `node.state`，
   但完全忽略了当前目录下的所有中间子目录（例如 `server/app`、`server/daff`），
   且 `_update_ancestors` 仅向上更新祖先，导致中间子目录的 `state` 依然保留为 `UNCHECKED`。
2. 修复手段：
   - 重构 `set_dir_checked`：
     a. 同步更新当前目录及其下所有后代叶子文件在 `checked_files` 中的存在性以及叶子节点的 `node.state`；
     b. 对当前目录调用 `_refresh_recursive(node)`，彻底、自底向上后序刷新当前目录树分支内每一个子目录的 `state`，
        使其全部正确置为 `CHECKED`（或取消勾选时置为 `UNCHECKED`）；
     c. 向上调用 `_update_ancestors(node.parent)`，同步更新所有上层祖先目录的三态。
   - 实现无死角的“向下级联贯通所有子孙目录与叶子，向上递归聚合计算所有祖先”的双向状态完备一致性。
"""

import os
from enum import Enum
from typing import Dict, Generator, Iterable, List, Optional, Set, Tuple


class CheckState(Enum):
    """
    勾选状态枚举。
    UNCHECKED: 未选（显示为 ☐）
    CHECKED:   全选（显示为 ☑）
    PARTIAL:   部分勾选（仅目录可能出现，显示为 ◪）
    """
    UNCHECKED = 0
    CHECKED = 1
    PARTIAL = 2


class Node:
    """
    树节点数据结构（表示目录或具体文件）。

    属性：
        name:      显示名称（文件或文件夹名）
        path:      绝对路径（全局唯一 Key）
        parent:    父节点指针引用；根节点为 None
        children:  直接子节点列表（保持目录优先、名称排序）
        is_dir:    布尔标记，True 为目录，False 为文件
        size:      文件大小（字节，目录为 0）
        state:     当前三态勾选值（CheckState）
    """

    __slots__ = ("name", "path", "parent", "children", "is_dir", "size", "state")

    def __init__(
        self,
        name: str,
        path: str,
        is_dir: bool,
        size: int = 0,
        parent: Optional["Node"] = None,
    ):
        self.name: str = name
        self.path: str = path
        self.parent: Optional["Node"] = parent
        self.children: List["Node"] = []
        self.is_dir: bool = is_dir
        self.size: int = size
        self.state: CheckState = CheckState.UNCHECKED

    def add_child(self, child: "Node") -> None:
        """向当前节点挂载子节点，同时维护子节点的 parent 指针。"""
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: "Node") -> None:
        """安全移除指定子节点，解除其 parent 引用。"""
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def sort_children(self) -> None:
        """
        对直接子节点排序：
        目录排在前方，文件排在后方；同类型项按名称不区分大小写排序。
        """
        self.children.sort(key=lambda n: (not n.is_dir, n.name.lower()))

    def iter_files(self) -> Generator["Node", None, None]:
        """
        深度优先生成器：高效遍历所有下属后代叶子文件节点（不包含目录）。
        """
        for c in self.children:
            if c.is_dir:
                yield from c.iter_files()
            else:
                yield c

    def iter_dirs(self) -> Generator["Node", None, None]:
        """
        深度优先生成器：遍历所有下属后代目录节点（不包含自身和叶子文件）。
        """
        for c in self.children:
            if c.is_dir:
                yield c
                yield from c.iter_dirs()


class TreeModel:
    """
    树数据模型：统一维护目录结构、路径索引、勾选三态流转与增删修剪。
    """

    def __init__(self):
        self.root: Optional[Node] = None                  # 根节点
        self.path_to_node: Dict[str, Node] = {}          # 全局绝对路径 -> Node 实例映射表
        self.checked_files: Set[str] = set()             # 所有已勾选文件的绝对路径集合

    # -------------------------------------------------------------------------
    # 核心构建机制
    # -------------------------------------------------------------------------
    def build(self, root_dir: str, file_list: List[Tuple[str, int]]) -> None:
        """
        根据指定的根目录和文件元数据全量构建目录树。

        参数：
            root_dir:  根目录绝对路径
            file_list: [(file_abs_path, size_bytes), ...]
        """
        self.root = Node(
            name=os.path.basename(root_dir) or root_dir,
            path=root_dir,
            is_dir=True,
        )
        self.path_to_node = {root_dir: self.root}
        self.checked_files.clear()

        # 逐项插入叶子文件并自动补全中间目录
        for file_abs, size in file_list:
            self._insert_file(file_abs, size)

        # 递归对子级进行排序
        self._sort_recursive(self.root)

    def _insert_file(self, file_abs: str, size: int) -> None:
        """插入单个文件，向上回溯确保各级父目录已创建。"""
        parent_dir = os.path.dirname(file_abs)
        parent_node = self._ensure_dir(parent_dir)
        file_name = os.path.basename(file_abs)
        file_node = Node(name=file_name, path=file_abs, is_dir=False, size=size)
        parent_node.add_child(file_node)
        self.path_to_node[file_abs] = file_node

    def _ensure_dir(self, dir_abs: str) -> Node:
        """
        确保自顶向下的所有中间目录节点均已实例化，并返回直接父目录节点。
        """
        if dir_abs in self.path_to_node:
            return self.path_to_node[dir_abs]

        if self.root is None:
            raise RuntimeError("TreeModel.build 未能初始化根节点")

        to_create = []
        cur = dir_abs
        root_path = self.root.path
        while cur and cur != root_path and cur not in self.path_to_node:
            to_create.append(cur)
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent

        for path in reversed(to_create):
            parent_dir = os.path.dirname(path)
            parent_node = self.path_to_node.get(parent_dir, self.root)
            name = os.path.basename(path) or path
            node = Node(name=name, path=path, is_dir=True, parent=parent_node)
            parent_node.add_child(node)
            self.path_to_node[path] = node

        return self.path_to_node[dir_abs]

    def _sort_recursive(self, node: Node) -> None:
        """递归对所有子节点执行排序。"""
        node.sort_children()
        for c in node.children:
            if c.is_dir:
                self._sort_recursive(c)

    # -------------------------------------------------------------------------
    # 状态同步核心（下溯子代、上溯祖先）
    # -------------------------------------------------------------------------
    def set_dir_checked(self, dir_path: str, checked: bool) -> None:
        """
        设置目录的勾选状态。
        ★ 核心修复点：
        1. 针对该目录下的所有后代叶子文件：在 checked_files 中记录/移除，并同步设置其 state。
        2. 针对该目录及其下属的所有子孙目录节点：递归执行后序遍历更新，确保各层级子文件夹自身也立即更新为 CHECKED（或 UNCHECKED）。
        3. 针对上层祖先目录：自底向上逐级更新聚合状态。

        参数：
            dir_path: 目录绝对路径
            checked: True 表示全选该目录下全部内容；False 表示全取消
        """
        node = self.path_to_node.get(dir_path)
        if not node or not node.is_dir:
            return

        # 1. 深度更新当前目录所有下属叶子文件在 checked_files 集合中的状态
        for f in node.iter_files():
            if checked:
                self.checked_files.add(f.path)
            else:
                self.checked_files.discard(f.path)

        # 2. 从当前节点自身开始，递归向下刷新当前目录分支内所有子目录与叶子文件的 state
        self._refresh_recursive(node)

        # 3. 向上逐级重新聚合计算所有祖先目录的勾选三态
        self._update_ancestors(node.parent)

    def set_file_checked(self, file_path: str, checked: bool) -> None:
        """
        设置单个叶子文件的勾选状态，并沿链向上重算所有祖先目录的三态。
        """
        node = self.path_to_node.get(file_path)
        if not node or node.is_dir:
            return

        if checked:
            self.checked_files.add(file_path)
            node.state = CheckState.CHECKED
        else:
            self.checked_files.discard(file_path)
            node.state = CheckState.UNCHECKED

        self._update_ancestors(node.parent)

    def toggle_dir(self, dir_path: str) -> None:
        """
        切换目录的勾选状态。
        规则：若当前处于全选状态（CHECKED），点击后变为全不选（UNCHECKED）；
              若当前处于未选或部分选（PARTIAL），点击后一律变为全选（CHECKED）。
        """
        node = self.path_to_node.get(dir_path)
        if not node or not node.is_dir:
            return

        if node.state == CheckState.CHECKED:
            self.set_dir_checked(dir_path, False)
        else:
            self.set_dir_checked(dir_path, True)

    def toggle_file(self, file_path: str) -> None:
        """切换单个文件的勾选状态。"""
        node = self.path_to_node.get(file_path)
        if not node or node.is_dir:
            return
        self.set_file_checked(file_path, node.state != CheckState.CHECKED)

    def sync_checked_states(self, checked_paths: Iterable[str]) -> None:
        """
        从外部集合全量同步勾选状态，并全树重算所有节点状态。
        """
        valid_paths = set()
        for p in checked_paths:
            node = self.path_to_node.get(p)
            if node and not node.is_dir:
                valid_paths.add(p)

        self.checked_files = valid_paths
        self.refresh_all_states()

    def refresh_all_states(self) -> None:
        """
        全局重新计算整棵树所有节点的状态（从根节点后序遍历）。
        """
        if self.root:
            self._refresh_recursive(self.root)

    def _refresh_recursive(self, node: Node) -> None:
        """
        后序遍历子树：
        1. 叶子节点：严格根据 self.checked_files 同步更新 state；
        2. 目录节点：先让所有子项（子目录与子文件）递归更新完毕，再计算当前目录的聚合三态。
        """
        if not node.is_dir:
            node.state = (
                CheckState.CHECKED
                if node.path in self.checked_files
                else CheckState.UNCHECKED
            )
            return

        # 若是目录，必须先递归向下更新所有直接子节点（保证子文件夹也先更新）
        for c in node.children:
            self._refresh_recursive(c)

        # 随后，自底向上准确计算当前目录自身的三态
        node.state = self._compute_dir_state(node)

    def _update_ancestors(self, node: Optional[Node]) -> None:
        """
        从指定祖先节点开始向上逐层更新聚合状态，直至到达根节点的父级（None）。
        """
        while node is not None and node.is_dir:
            node.state = self._compute_dir_state(node)
            node = node.parent

    def _compute_dir_state(self, dir_node: Node) -> CheckState:
        """
        聚合计算目录的勾选三态：
        - 若该目录下没有任何文件：视为未选 UNCHECKED
        - 若该目录下所有文件均已勾选：视为全选 CHECKED
        - 若该目录下没有任何文件被勾选：视为未选 UNCHECKED
        - 若部分被勾选：视为部分选 PARTIAL
        """
        total = 0
        checked = 0
        for f in dir_node.iter_files():
            total += 1
            if f.path in self.checked_files:
                checked += 1

        if total == 0:
            return CheckState.UNCHECKED
        if checked == 0:
            return CheckState.UNCHECKED
        if checked == total:
            return CheckState.CHECKED
        return CheckState.PARTIAL

    # -------------------------------------------------------------------------
    # 动态增删与空目录修剪
    # -------------------------------------------------------------------------
    def remove_paths(self, paths: Iterable[str]) -> Tuple[int, List[str]]:
        """
        从模型中级联删除指定路径集合，自动修剪空目录并重算状态。
        """
        removed_files: List[str] = []
        sorted_paths = sorted(set(paths), key=lambda p: len(p), reverse=True)

        for path in sorted_paths:
            node = self.path_to_node.get(path)
            if node is None:
                continue

            if node is self.root:
                all_f = list(self.all_files())
                self.root = None
                self.path_to_node.clear()
                self.checked_files.clear()
                return len(all_f), all_f

            if node.is_dir:
                contained_files = [f.path for f in node.iter_files()]
            else:
                contained_files = [node.path]

            self._cascade_remove_node(node)

            for f_path in contained_files:
                if f_path not in removed_files:
                    removed_files.append(f_path)
                    self.checked_files.discard(f_path)

        if self.root:
            self._prune_empty_dirs(self.root)
            self.refresh_all_states()

        return len(removed_files), removed_files

    def _cascade_remove_node(self, node: Node) -> None:
        """级联注销节点及其所有子代。"""
        for child in list(node.children):
            self._cascade_remove_node(child)

        if node.parent:
            node.parent.remove_child(node)

        self.path_to_node.pop(node.path, None)

    def _prune_empty_dirs(self, node: Node) -> bool:
        """递归修剪没有文件的空目录分支。"""
        if not node.is_dir:
            return True

        for child in list(node.children):
            if child.is_dir:
                has_files = self._prune_empty_dirs(child)
                if not has_files:
                    node.remove_child(child)
                    self.path_to_node.pop(child.path, None)

        has_any_file = any((not c.is_dir) or (c.is_dir and len(c.children) > 0) for c in node.children)
        return has_any_file

    # -------------------------------------------------------------------------
    # 批量操作与查询辅助
    # -------------------------------------------------------------------------
    def check_all(self, paths: Optional[Iterable[str]] = None) -> None:
        """批量全选。"""
        targets = paths if paths is not None else self.all_files()
        for p in targets:
            node = self.path_to_node.get(p)
            if node and not node.is_dir:
                self.checked_files.add(p)
        self.refresh_all_states()

    def uncheck_all(self, paths: Optional[Iterable[str]] = None) -> None:
        """批量取消勾选。"""
        targets = paths if paths is not None else self.all_files()
        for p in targets:
            node = self.path_to_node.get(p)
            if node and not node.is_dir:
                self.checked_files.discard(p)
        self.refresh_all_states()

    def invert_all(self, paths: Optional[Iterable[str]] = None) -> None:
        """批量反选。"""
        targets = paths if paths is not None else self.all_files()
        for p in targets:
            node = self.path_to_node.get(p)
            if node and not node.is_dir:
                if p in self.checked_files:
                    self.checked_files.discard(p)
                else:
                    self.checked_files.add(p)
        self.refresh_all_states()

    def get_node(self, path: str) -> Optional[Node]:
        """按路径返回节点。"""
        return self.path_to_node.get(path)

    def all_files(self) -> Set[str]:
        """获取模型内所有叶子文件的路径集合。"""
        return {p for p, n in self.path_to_node.items() if not n.is_dir}

    def collect_files_under(self, dir_path: str) -> Set[str]:
        """获取指定目录下所有叶子文件的路径集合。"""
        node = self.path_to_node.get(dir_path)
        if not node or not node.is_dir:
            return set()
        return {f.path for f in node.iter_files()}