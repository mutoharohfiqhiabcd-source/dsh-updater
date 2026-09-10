# -*- coding: utf-8 -*-
"""pytest 引导：把仓库根目录加入 sys.path，使测试可以直接 import updater_core。

放在 tests/ 下而不是仓库根，是为了不干扰运行时的模块搜索路径。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
