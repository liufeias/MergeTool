# -*- coding: utf-8 -*-
"""
模块入口。

支持两种运行方式：
    1. uv run python -m merge_tool
    2. uv run merge-tool          （需在 pyproject.toml 中配置 [project.scripts]）

此文件仅做最小化转发，具体逻辑在 app.main() 中。
"""

from merge_tool.app import main

if __name__ == "__main__":
    main()