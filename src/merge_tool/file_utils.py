# -*- coding: utf-8 -*-
"""
文件系统工具函数。

包含：
    - human_size         字节数转人类可读
    - safe_str           安全字符串转换
    - parse_drop_paths   解析拖放事件路径
    - normalize_ext_set  规范化扩展名输入
    - split_extension    拆分文件名与扩展名
"""

import os
import re


def safe_str(obj):
    """
    将任意对象安全转换为字符串。

    任何异常（如对象 __str__ 抛错）都会被捕获并返回占位符，
    保证 UI 渲染逻辑不会因显示问题而崩溃。
    """
    try:
        return str(obj)
    except Exception:
        return "<无法显示>"


def human_size(num_bytes):
    """
    将字节数转换成人类可读的字符串（B/KB/MB/GB/TB/PB）。

    对 None、非数字、负数等异常输入返回 "0 B"，绝不抛异常。
    """
    try:
        num = float(num_bytes)
    except (TypeError, ValueError):
        return "0 B"
    if num < 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} PB"


def parse_drop_paths(raw_data, tk_root=None):
    """
    解析拖放事件返回的路径列表。

    Windows 上 tkinterdnd2 的 event.data 格式示例：
        C:/path/a.txt C:/path/b.txt
        {C:/path with space/c.txt} C:/path/d.txt
        {C:/路径/中文 文件.txt}

    参数：
        raw_data: event.data 原始字符串
        tk_root:  若提供，优先用 tk_root.tk.splitlist 解析（最可靠）

    返回：
        去重后的绝对路径列表（顺序保持首次出现顺序）
    """
    paths = []
    if not raw_data:
        return paths

    # 首选：tk.splitlist（能正确处理 {} 包裹和大括号转义）
    if tk_root is not None:
        try:
            paths = list(tk_root.tk.splitlist(raw_data))
        except Exception:
            paths = []

    # 回退：正则解析 {xxx} 或非空白串
    if not paths:
        try:
            matches = re.findall(r"\{([^}]*)\}|(\S+)", raw_data)
            paths = [a or b for a, b in matches]
        except Exception:
            paths = []

    # 规范化：去空、去重、转绝对路径
    result = []
    seen = set()
    for p in paths:
        if not p:
            continue
        try:
            ap = os.path.abspath(p)
        except Exception:
            continue
        if ap in seen:
            continue
        seen.add(ap)
        result.append(ap)
    return result


def normalize_ext_set(extensions_raw):
    """
    把用户输入的扩展名字符串规范化为集合。

    输入示例：
        "txt,log,md"   -> {".txt", ".log", ".md"}
        ".CS,.H"       -> {".cs", ".h"}
        ""             -> set()

    规则：
        - 按逗号切分
        - 去空白、转小写
        - 自动补前导点
        - 空集表示不限扩展名
    """
    result = set()
    if not extensions_raw:
        return result
    for e in str(extensions_raw).split(","):
        e = e.strip().lower()
        if not e:
            continue
        if not e.startswith("."):
            e = "." + e
        result.add(e)
    return result


def split_extension(file_name):
    """
    拆分文件名和扩展名。

    返回：
        (name_without_ext, ext_with_dot_lower)
    对无扩展名文件，ext 返回 ""。
    """
    name, ext = os.path.splitext(file_name)
    return name, ext.lower()


def is_path_within(child, parent):
    """
    判断 child 路径是否在 parent 目录下（含子目录）。

    用 os.path.commonpath 实现，跨平台安全。
    若其中一个为空则返回 False。
    """
    if not child or not parent:
        return False
    try:
        child_ap = os.path.abspath(child)
        parent_ap = os.path.abspath(parent)
        return os.path.commonpath([child_ap, parent_ap]) == parent_ap
    except (ValueError, OSError):
        # 不同盘符会触发 ValueError，返回 False 即可
        return False