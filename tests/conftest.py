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


# ---------------------------------------------------------------------------
# 固定测试环境：语言与本地信息目录
# ---------------------------------------------------------------------------
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _pin_language(monkeypatch):
    """把语言固定为简体中文。

    i18n 在**导入时**会按系统语言初始化，而 CI runner 的系统语言是英文、
    开发机往往是中文。若不固定，测试结果就依赖运行环境——本地全绿、CI 全红，
    而且极难复现。这里全部按原文（简体中文）断言，杜绝这种环境依赖。
    """
    import i18n
    monkeypatch.setattr(i18n, "_current", i18n.SOURCE_LANG, raising=False)
    monkeypatch.setattr(i18n, "_setting", i18n.SOURCE_LANG, raising=False)
    yield


@pytest.fixture(autouse=True)
def _isolate_settings_dir(monkeypatch, tmp_path_factory):
    """默认把本地信息目录指向临时目录，避免任何测试误写用户真实配置。

    个别测试会用 monkeypatch 覆盖成自己的 tmp_path，那是在本 fixture 之后生效，
    不受影响。
    """
    import updater_core as core
    d = tmp_path_factory.mktemp("dsh-home")
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(d))
    yield
