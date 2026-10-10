<!-- 语言切换条：中文版（当前） | 英文版 -->
**简体中文** | [English](README.en.md)

---

# MergeTool · 文件内容合并工具

> 一款基于 **PySide6 + Google Material Design 3** 的图形化文件内容合并工具。
> 支持目录树三态勾选、平铺/树形双视图、正则筛选、拖放加载、多编码自动检测，
> 可将成百上千个文本文件高效合并为一份带元信息的报告。

![Python](https://img.shields.io/badge/Python-3.11%20~%203.13-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-6.12+-41CD52?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📖 文档导航

| 文档 | 说明 |
| --- | --- |
| [📘 使用帮助](docs/USAGE.md) | 面向普通用户：安装、界面说明、完整操作流程、常见问题 |
| [🛠 开发构建打包](docs/BUILD.md) | 面向开发者：环境搭建、依赖管理、调试、PyInstaller 打包、体积优化 |
| [📝 更新日志](docs/CHANGELOG.md) | 版本变更记录 |

> 英文用户请点击顶部 [English](README.en.md) 切换到英文文档。

---

## ✨ 功能特性

- **目录树三态勾选**：文件夹自动聚合为「全选 / 半选 / 未选」，父子级联联动。
- **平铺 / 树形双视图**：一键在层级结构与扁平文件列表之间切换。
- **强大的筛选能力**：
  - 按扩展名过滤（如 `py,txt,md,json`，可留空表示不限）。
  - 包含 / 排除无扩展名文件。
  - 递归 / 非递归子文件夹。
  - 文件名筛选，支持普通字符串或**正则表达式**。
- **拖放加载**：把文件或文件夹直接拖进窗口即可加载，自动去重、自动追加。
- **严谨的多编码检测**：
  - BOM 头识别 → chardet 采样（带置信度阈值 + 严格解码二次校验）→ UTF-8 严格试探 → GB18030 严格试探 → latin-1 兜底。
  - 中文老项目常见的 GBK/GB2312 无 BOM 文件也能正确识别。
- **高性能后台线程**：扫描与合并均在后台线程执行，UI 全程不卡死，支持随时取消。
- **Google Material Design 3 界面**：官方 Material Symbols 矢量图标、M3 色板、药丸输入框、无杂边圆角菜单。
- **输出带完整元信息**：生成时间、根目录、文件总数、编码模式、筛选条件、每个文件的绝对路径 / 编码 / 大小。

---

## 🖼 界面预览

![MergeTool 主界面](docs/images/main-window.png)

> 左侧为数据源、筛选与输出配置区，右侧为文件树与操作菜单。

---

## 🚀 快速开始

### 方式一：直接运行源码（推荐开发者）

```powershell
# 1. 克隆仓库
git clone https://github.com/liufeias/MergeTool.git
cd MergeTool

# 2. 使用 uv 安装依赖（推荐）
uv sync

# 3. 运行
uv run python -m merge_tool
# 或者
uv run merge-tool
```

### 方式二：使用打包好的 exe（推荐普通用户）

从 [Releases](https://github.com/liufeias/MergeTool/releases) 页面下载 `MergeTool-vX.Y.Z.zip`，
解压后双击 `MergeTool.exe` 即可运行，**无需安装 Python**。

> 详细的安装与使用步骤请阅读 [📘 使用帮助](docs/USAGE.md)。

---

## 🗂 项目结构

```
MergeTool/
├── src/merge_tool/          # 源码包
│   ├── __init__.py          # 包入口与版本号
│   ├── __main__.py          # python -m merge_tool 入口
│   ├── app.py               # 主窗口与 UI 组装调度中心
│   ├── constants.py         # 全局常量、M3 色板、SVG 图标、QSS 主题
│   ├── encoding_utils.py    # 编码检测与安全读取
│   ├── file_utils.py        # 文件系统工具函数
│   ├── tree_model.py        # 树数据模型（三态勾选、父子联动）
│   ├── tree_view.py         # Treeview 视图封装（自定义委托渲染）
│   └── workers.py           # 后台线程（扫描、合并）
├── assets/                  # 图标等静态资源（可选）
├── docs/                    # 文档目录
├── pyproject.toml           # 项目元数据与依赖（PEP 621）
├── uv.lock                  # uv 锁文件
├── MergeTool.spec           # PyInstaller 打包配置
└── README.md                # 本文件
```

---

## 🧭 文档互链

- 中文：[使用帮助](docs/USAGE.md) · [开发构建打包](docs/BUILD.md) · [更新日志](docs/CHANGELOG.md)
- English: [Usage](docs/USAGE.en.md) · [Build](docs/BUILD.en.md) · [Changelog](docs/CHANGELOG.en.md)

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 🙏 致谢

- [PySide6](https://doc.qt.io/qtforpython/) — Qt for Python 官方绑定
- [chardet](https://github.com/chardet/chardet) — 通用字符编码检测库
- [Google Material Design 3](https://m3.material.io/) — 设计语言参考