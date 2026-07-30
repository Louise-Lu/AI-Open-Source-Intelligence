"""CLI entrypoint: python -m evaluation.run"""
# 命令行工具 入口点
# 在项目根目录下运行
# python -m evaluation.run -> 执行 evaluation/runner.py 的 main()函数

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.runner import main


if __name__ == "__main__":
    main()
