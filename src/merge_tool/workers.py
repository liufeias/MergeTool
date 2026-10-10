# -*- coding: utf-8 -*-
"""
后台工作线程。

包含：
    - scan_worker      扫描目录，收集文件
    - merge_worker     合并文件

所有线程通过 ui_queue 向主线程发送消息，格式为 (msg_type, payload)。
"""

import os
import time
import traceback
from datetime import datetime

from merge_tool.constants import (
    SCAN_REPORT_INTERVAL_SEC,
    MERGE_REPORT_INTERVAL_SEC,
)
from merge_tool.encoding_utils import read_file_safely
from merge_tool.file_utils import human_size, normalize_ext_set


def scan_worker(root, options, ui_queue, cancel_flag):
    """
    扫描目录的后台线程函数。

    参数：
        root:        根目录绝对路径
        options:     包含 recurse / extensions_raw / include_no_ext 的字典
        ui_queue:    与 UI 通信的队列
        cancel_flag: threading.Event，用于取消任务

    消息类型：
        ("scan_progress", (count, current_dir_name))
        ("scan_done", [(file_abs, size), ...])
        ("status", (text, color))
    """
    try:
        recurse = bool(options.get("recurse", True))
        extensions = normalize_ext_set(options.get("extensions_raw", ""))
        include_no_ext = bool(options.get("include_no_ext", False))

        collected = []
        stack = [root]
        last_report = time.time()

        while stack:
            if cancel_flag.is_set():
                ui_queue.put(("status", ("扫描已取消", "red")))
                return

            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        if cancel_flag.is_set():
                            ui_queue.put(("status", ("扫描已取消", "red")))
                            return
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                if recurse:
                                    stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                name = entry.name
                                _, ext = os.path.splitext(name)
                                ext_lower = ext.lower()
                                # 扩展名过滤
                                if extensions:
                                    if ext_lower == "":
                                        if not include_no_ext:
                                            continue
                                    elif ext_lower not in extensions:
                                        continue
                                else:
                                    if ext_lower == "" and not include_no_ext:
                                        continue
                                try:
                                    size = entry.stat(
                                        follow_symlinks=False).st_size
                                except OSError:
                                    size = 0
                                collected.append((entry.path, size))
                        except OSError:
                            continue
            except OSError:
                continue

            now = time.time()
            if now - last_report > SCAN_REPORT_INTERVAL_SEC:
                last_report = now
                ui_queue.put((
                    "scan_progress",
                    (len(collected), os.path.basename(current))
                ))

        ui_queue.put(("scan_done", collected))

    except Exception as e:
        tb = traceback.format_exc()
        ui_queue.put(("error", f"扫描文件夹时发生错误:\n{e}\n\n{tb}"))


def merge_worker(files, output, force_encoding, options, file_sizes,
                 ui_queue, cancel_flag):
    """
    合并文件的后台线程函数。

    参数：
        files:           要合并的文件绝对路径列表
        output:          输出文件路径
        force_encoding:  强制编码名或 None
        options:         其他参数（扩展名、筛选、根目录等，用于写入头部）
        file_sizes:      {abs_path: size}，用于写入头部
        ui_queue:        与 UI 通信的队列
        cancel_flag:     threading.Event

    消息类型：
        ("merge_progress", (processed, total, current_name))
        ("merge_done", (output, processed, failed_count, failed_list))
        ("error", message)
    """
    try:
        total = len(files)
        files_sorted = sorted(files, key=lambda p: p.lower())

        # 确保输出目录存在
        out_dir = os.path.dirname(os.path.abspath(output))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # 使用 utf-8-sig 写出，Windows 记事本打开不乱码
        with open(output, "w", encoding="utf-8-sig",
                  newline="\n", buffering=1024 * 1024) as f:

            # ---------- 头部 ----------
            f.write("=" * 70 + "\n")
            f.write("文件内容合并工具 - 输出报告\n")
            f.write("=" * 70 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"根目录: {options.get('root_dir', '')}\n")
            f.write(f"文件总数: {total}\n")
            f.write(f"编码模式: {force_encoding if force_encoding else '自动检测'}\n")
            f.write(f"扩展名筛选: {options.get('extensions_raw', '') or '（不限）'}\n")
            f.write(f"包含无扩展名文件: "
                    f"{'是' if options.get('include_no_ext') else '否'}\n")
            f.write(f"递归搜索: {'是' if options.get('recurse') else '否'}\n")
            f.write(f"文件名筛选: {options.get('pattern', '') or '（无）'}\n")
            f.write(f"使用正则: {'是' if options.get('use_regex') else '否'}\n")
            f.write("\n")
            f.write("--- 文件内容格式说明 ---\n")
            f.write("每个文件的数据块遵循以下格式:\n")
            f.write("1. 以 '文件绝对路径: ' 开头，后跟文件的完整路径。\n")
            f.write("2. 从下一行开始，是该文件的完整、原始内容。\n")
            f.write("3. 每个文件的数据块之后会有一个空行，用于与下一个文件分隔。\n")
            f.write("\n")
            f.write("=" * 70 + "\n")
            f.write("======================= 合并内容开始 =======================\n")
            f.write("=" * 70 + "\n\n")

            processed = 0
            failed = []
            last_report = time.time()

            for path in files_sorted:
                if cancel_flag.is_set():
                    f.write("\n\n[任务已被用户取消，以下文件未合并]\n")
                    break

                try:
                    content, used_enc = read_file_safely(path, force_encoding)
                except Exception as e:
                    failed.append((path, str(e)))
                    content = f"[读取失败: {e}]"
                    used_enc = "unknown"

                size = file_sizes.get(path, 0)
                f.write(f"文件绝对路径:  {path}\n")
                f.write(f"文件编码: {used_enc} | 大小: {human_size(size)}\n")
                f.write("-" * 70 + "\n")
                f.write(content)
                if not content.endswith("\n"):
                    f.write("\n")
                f.write("\n")

                processed += 1

                now = time.time()
                if now - last_report > MERGE_REPORT_INTERVAL_SEC:
                    last_report = now
                    ui_queue.put((
                        "merge_progress",
                        (processed, total, os.path.basename(path))
                    ))

            # 尾部
            f.write("=" * 70 + "\n")
            f.write("======================= 合并内容结束 =======================\n")
            f.write("=" * 70 + "\n")
            f.write(f"\n成功合并文件数: {processed}\n")
            if failed:
                f.write(f"失败文件数: {len(failed)}\n")
                for p, err in failed:
                    f.write(f"  - {p}: {err}\n")

        ui_queue.put(("merge_done", (output, processed, len(failed), failed)))

    except Exception as e:
        tb = traceback.format_exc()
        ui_queue.put(("error", f"合并过程中发生错误:\n{e}\n\n{tb}"))