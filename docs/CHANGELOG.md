<!-- 语言切换：简体中文（当前） | 英文版 -->
**简体中文** | [English](CHANGELOG.en.md)

[← 返回首页](../README.md) · [📘 使用帮助](USAGE.md) · [🛠 开发构建打包](BUILD.md) · [📝 更新日志](CHANGELOG.md)

---

# 更新日志

本文件记录 MergeTool 的版本变更。格式参考 [Keep a Changelog](https://keepachangelog.com/)，
版本号遵循 [Semantic Versioning](https://semver.org/)。

## [2.0.0] - 2026-10-10

### 新增
- Google Material Design 3 全量 UI 重构，采用官方 Material Symbols 矢量图标。
- 右上角药丸型搜索框，聚焦时显示 2px Google 蓝边框。
- 拖放加载文件与文件夹，自动去重、自动追加。
- 树形 / 平铺双视图自由切换。
- 目录三态勾选（全选 / 半选 / 未选）与父子级联联动。
- 正则表达式文件名筛选。
- 多编码级联检测（BOM → chardet → UTF-8 严格 → GB18030 严格 → latin-1 兜底）。
- 后台线程扫描与合并，UI 全程不卡死，支持取消。
- 输出报告包含完整元信息（生成时间、根目录、编码、大小等）。

### 变更
- 从 customtkinter 迁移到 PySide6。
- 输出编码固定为 UTF-8-SIG，保证 Windows 记事本兼容。

### 修复
- 修复勾选父文件夹后中间层子文件夹未同步选中的缺陷。
- 修复下拉菜单与右键菜单圆角外侧杂色问题。
- 修复高亮时出现橘黄色虚线框的问题。

## [1.x.x] - 更早版本

早期基于 customtkinter 的版本，功能较简单，已不再维护。