# -*- coding: utf-8 -*-
"""
merge_tool 包入口。

本包提供一个图形化的"文件内容合并工具"，支持：
    - 目录树多级勾选（文件夹三态）
    - 平铺/树形两种显示模式
    - 正则/普通字符串筛选
    - 拖放加载
    - 严谨的多编码检测
    - 高性能后台扫描与合并

模块结构：
    constants       全局常量与编码表
    file_utils      文件系统工具函数
    encoding_utils  编码检测与安全读取
    tree_model      树的数据模型（三态勾选、父子联动）
    tree_view       Treeview 视图封装（勾选框、右键菜单）
    workers         后台线程（扫描、合并）
    app             主窗口与 UI 组装
"""

__version__ = "2.0.0"
__all__ = ["__version__"]