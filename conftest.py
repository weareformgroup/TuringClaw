"""
conftest.py — 确保 TuringClaw 包可以被正确导入。

项目结构：
  /mnt/c/Users/Administrator/TuringClaw/  ← 这是包目录本身
  /mnt/c/Users/Administrator/             ← 这是需要加入 sys.path 的父目录

hatchling 的 packages=["."] 配置将项目根目录作为包，
所以需要将父目录加入 sys.path。
"""
import sys
from pathlib import Path

# 项目根目录的父目录
_parent = str(Path(__file__).parent.parent.resolve())
if _parent not in sys.path:
    sys.path.insert(0, _parent)
