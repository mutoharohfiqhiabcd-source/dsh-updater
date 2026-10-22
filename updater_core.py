# -*- coding: utf-8 -*-
"""
updater_core.py —— DeepSeek Harness 自动检测与更新器（纯逻辑层，不依赖 GUI）
============================================================
功能：
  1. 检测电脑内的 DeepSeek Harness 安装（源码检出 / npm 全局 / .dsh 运行时 profile）
  2. 获取官方开源最新版本（GitHub master 源码 + npm registry 发布版）
  3. 插件检测：读取 profile 启用清单与运行时安装包（名称 / 大小 / 版本）
  4. 技能检测：扫描 .dsh/skills 下的技能目录（名称 / 大小 / 版本）
  5. 更新：下载官方源码 zip → 备份 → 整目录替换（保留 node_modules/.git）→ 可选 pnpm install

命令行自测：  python updater_core.py --selftest
"""
from __future__ import annotations

import base64
import copy
import datetime
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from i18n import t

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
GITHUB_OWNER = "deepseek-ai"
GITHUB_REPO = "deepseek-harness"
GITHUB_BRANCH = "master"

RAW_PACKAGE_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/package.json"
)
ZIP_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"
API_COMMIT_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
)
NPM_LATEST_URL = "https://registry.npmjs.org/@deepseek-ai/dsh/latest"

# ---- 本更新器自身的仓库（用于「检查更新器更新」）----
SELF_REPO_OWNER = "mutoharohfiqhiabcd-source"
SELF_REPO_NAME = "dsh-updater"
SELF_REPO_URL = f"https://github.com/{SELF_REPO_OWNER}/{SELF_REPO_NAME}"
SELF_RELEASES_URL = (
    f"https://api.github.com/repos/{SELF_REPO_OWNER}/{SELF_REPO_NAME}/releases?per_page=20"
)
SELF_TAGS_URL = (
    f"https://api.github.com/repos/{SELF_REPO_OWNER}/{SELF_REPO_NAME}/tags?per_page=100"
)

UA = {"User-Agent": "dsh-auto-updater/1.0 (+https://github.com/deepseek-ai/deepseek-harness)"}

HOME = Path.home()
DSH_HOME = Path(os.environ.get("DSH_HOME") or (HOME / ".dsh"))

INSTALL_KIND_SOURCE = "source"     # 源码检出（可整目录替换更新）
INSTALL_KIND_NPM = "npm"           # npm 全局安装
INSTALL_KIND_PROFILE = "profile"   # .dsh 运行时 profile

# 名称里包含这些词的目录会被当作“源码检出”候选（避免全盘深扫）
_SRC_HINTS = ("harness", "deepseek")
# 保留不动的大目录（整目录替换时）
_KEEP_DIRS = ("node_modules", ".git")
_NPM_GLOBAL_FALLBACKS = (
    Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules",
    Path(os.environ.get("LOCALAPPDATA", "")) / "npm" / "node_modules",
)


# ---------------------------------------------------------------------------
# 网络小工具
# ---------------------------------------------------------------------------
def http_get(url: str, timeout: float = 25.0, binary: bool = False,
             headers: dict | None = None) -> bytes:
    """GET 并返回原始字节；失败抛异常。

    headers 用来覆盖默认 UA / 附加 Accept 等（例如 npm 包元数据的精简格式）。
    """
    merged = dict(UA)
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, headers=merged)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_json(url: str, timeout: float = 25.0, headers: dict | None = None):
    return json.loads(http_get(url, timeout=timeout, headers=headers).decode("utf-8", "replace"))


def http_get_text(url: str, timeout: float = 25.0, headers: dict | None = None) -> str:
    return http_get(url, timeout=timeout, headers=headers).decode("utf-8", "replace")


def _parse_package_version(text: str) -> str:
    """从 package.json 文本取 version 字段（不依赖 json 解析健壮性时备用）。"""
    m = re.search(r'"version"\s*:\s*"([^"]+)"', text)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# 版本比较（支持 0.1.0-rc.5 / 1.2.3-alpha.1 之类）
# ---------------------------------------------------------------------------
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+.]([0-9A-Za-z.-]+))?$")


def version_key(v: str):
    """把版本串转成可比较元组；无法解析时按 (0,0,0,'') 兜底。"""
    if not v:
        return (0, 0, 0, "")
    m = _VERSION_RE.match(v.strip())
    if not m:
        return (0, 0, 0, v.strip().lower())
    major, minor, patch = (int(m.group(i)) for i in (1, 2, 3))
    pre = (m.group(4) or "").lower()
    return (major, minor, patch, pre)


def compare_versions(a: str, b: str) -> int:
    """a>b 返回 1；a<b 返回 -1；相等返回 0。"""
    ka, kb = version_key(a), version_key(b)
    if ka > kb:
        return 1
    if ka < kb:
        return -1
    return 0


# ---------------------------------------------------------------------------
# 稳定性 / 适配性评估（依据官网信息）
# ---------------------------------------------------------------------------
# 稳定性分级：
#   stable     官方最新发布版（npm latest / 无预发布后缀）
#   candidate  官方发布候选（rc 后缀，且出现在官方 tags/npm 版本里）
#   prerelease 预发布（alpha/beta 后缀）
#   unstable   官网信息缺乏或无法核实的“不稳定版”（找不到对应官方记录）
# 注意：这里只放中文原文，**不要**在模块级调用 t()。
# 模块级 t() 在 import 时就求值，那时语言还没从设置里加载，结果会被
# 永久冻死在导入时的语言上（表现为界面里混入其它语言）。
# 展示时一律用 grade_label_of() 按当前语言即时翻译。
GRADE_LABELS = {
    "stable": "稳定版",
    "candidate": "候选版 rc",
    "prerelease": "预发布 alpha",
    "unstable": "不稳定版",
}


def grade_label_of(grade: str) -> str:
    """把分级标识翻成当前语言的展示文本（缓存里不该存翻译结果）。"""
    g = str(grade or "")
    if not g:
        return ""
    return t(GRADE_LABELS.get(g, "不稳定版"))

def _grade_by_suffix(version: str) -> str:
    """按版本号后缀粗分级（用于本地版本还没有官网对照时）。"""
    v = (version or "").strip().lower()
    if not v:
        return "unstable"
    if any(k in v for k in ("alpha", "beta", "preview", "dev")):
        return "prerelease"
    if "-rc" in v or "rc." in v or v.endswith("-rc") or ".rc" in v:
        return "candidate"
    if any(ch.isdigit() for ch in v) and "-" not in v:
        return "stable"
    return "unstable"


def assess_version(version: str, official: dict | None, kind_for_ref: str = "npm") -> dict:
    """
    依据官网信息评估一个版本/更新目标的稳定性与适配性。
    kind_for_ref: 'npm'（对 npm 发布版）或 'github'（对 GitHub master 源码）。

    返回：{
      "version": ..., "grade": stable|candidate|prerelease|unstable,
      "grade_label": ..., "reason": str,
      "in_official": bool, "is_official_latest": bool,
      "node_ok": bool|None, "node_reason": str,
    }
    """
    v = (version or "").strip()
    if not v:
        return {"version": v, "grade": "unstable", "grade_label": GRADE_LABELS["unstable"],
                "reason": t("版本号为空，官网无法核实"), "in_official": False,
                "is_official_latest": False, "node_ok": None, "node_reason": t("无法评估")}

    official = official or {}
    ref = official.get(kind_for_ref) or {}
    npm = official.get("npm") or {}
    gh = official.get("github") or {}
    npm_ok = bool(npm.get("version"))
    gh_ok = bool(gh.get("version"))

    # 官方发布记录全集
    official_versions: list[str] = list(npm.get("versions") or []) + list(gh.get("tags") or [])
    dist_tags: dict = npm.get("dist_tags") or {}
    latest = dist_tags.get("latest") or npm.get("version")

    in_official = v in official_versions or v == latest or (
        bool(npm_ok or gh_ok) and (v in (npm.get("versions") or []) or v in (gh.get("tags") or []))
    )
    is_latest = bool(latest) and v == latest

    reason_parts = []
    node_ok = None
    node_reason = t("该版本未声明 Node.js 运行要求（官方 engines 缺失）")
    engines = ref.get("engines_node") or npm.get("engines_node")
    if not engines:
        # 本机 node 版本用于适配性判断
        node_ok = None
    else:
        cur_node = _local_node_version()
        node_ok = _match_node_range(cur_node, engines) if cur_node else None
        if node_ok is True:
            node_reason = t("本机 Node {cur_node} 满足官方要求 {engines}", cur_node=cur_node, engines=engines)
        elif node_ok is False:
            node_reason = t("本机 Node {cur_node} 不满足官方要求 {engines}（不适配）", cur_node=cur_node, engines=engines)
        else:
            node_reason = t("官方要求 Node {engines}，无法精确判定当前环境", engines=engines)
    reason_parts.append(node_reason)

    # —— 分级 ——
    if is_latest:
        grade = "stable"
    elif in_official:
        grade = _grade_by_suffix(v)
    else:
        # 官网可用？若官网完全没信息 → 不稳定版；若有信息但找不到该版本记录 → 也不稳定
        if not npm_ok and not gh_ok:
            grade = "unstable"
            reason_parts.insert(0, t("官网信息获取失败（GitHub 与 npm 均不可用），无法核实"))
        else:
            grade = "unstable"
            reason_parts.insert(0, t("该版本未出现在官方发布记录（GitHub tags / npm 版本表）中，无法核实其稳定性"))
    if grade == "stable":
        reason_parts.insert(0, t("与官方最新发布版（npm latest）一致"))
    elif grade == "unstable":
        pass
    else:
        reason_parts.insert(0, t("官方发布记录中存在该版本（预发布/候选版本）"))

    return {
        "version": v,
        "grade": grade,
        "grade_label": grade_label_of(grade),
        "reason": t("；").join(dict.fromkeys(reason_parts)),
        "in_official": in_official,
        "is_official_latest": is_latest,
        "node_ok": node_ok,
        "node_reason": node_reason,
    }


_LOCAL_NODE_VERSION: str | None = None


def _local_node_version() -> str:
    """本机 Node 版本；进程内缓存（一次检测会把每个安装各评估一遍，别重复起进程）。"""
    global _LOCAL_NODE_VERSION
    if _LOCAL_NODE_VERSION is not None:
        return _LOCAL_NODE_VERSION
    version = ""
    try:
        for exe in ("node", "node.exe"):
            p = shutil.which(exe)
            if p:
                r = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=10,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if r.returncode == 0:
                    version = (r.stdout or "").strip().lstrip("v")
                    break
    except Exception:  # noqa: BLE001
        pass
    _LOCAL_NODE_VERSION = version
    return version


# ---------------------------------------------------------------------------
# 官方版本：多源并发抓取
# ---------------------------------------------------------------------------
# 背景：从国内直连 GitHub API / npm registry 时，TLS 握手会被随机卡住——
# 实测**同一个 URL** 一次 1~4s 成功、一次 25s 超时失败。旧实现串行请求 7 个地址，
# 最坏要等 7 次超时（实测整次检测 90s+）。现在改成：
#   1. 同一份数据准备多个来源/多次尝试，全部**并发**发出，谁先成功用谁；
#   2. 单个请求短超时（5s），整轮抓取最多等 OFFICIAL_FETCH_BUDGET 秒；
#   3. 抓到的结果写本地缓存，5 分钟内重复检测不再联网（见 fetch_official_versions）。
OFFICIAL_CACHE_TTL = 300.0      # 官方版本结果缓存有效期（秒）
OFFICIAL_FAIL_TTL = 30.0        # 抓取不完整（某个源全灭）时的缓存有效期（秒）
OFFICIAL_FETCH_BUDGET = 8.0     # 一轮抓取最多等多久（秒）
_PROBE_TIMEOUT = 5.0            # 单个候选请求的超时（秒）

# 候选地址：官方源在前，镜像兜底；重复条目＝并发重试（对冲 TLS 握手被卡）。
# 实测同一条链路会随机「握手卡 5s 超时」，所以宁可多开几个并发连接，也别串行重试。
_RAW_ALT_URL = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/raw/{GITHUB_BRANCH}/package.json"
)
# jsDelivr 是 GitHub 的只读 CDN 镜像：内容只会「比 GitHub 旧」（缓存），绝不会更新，
# 所以它只可能让我们晚一个版本发现更新，不会误报「可更新」——作为兜底是安全的。
_JSDELIVR_MANIFEST = (
    f"https://cdn.jsdelivr.net/gh/{GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH}/package.json",
    f"https://gcore.jsdelivr.net/gh/{GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH}/package.json",
)
_GITHUB_MANIFEST_PROBES = (
    RAW_PACKAGE_URL, _RAW_ALT_URL, _JSDELIVR_MANIFEST[0],
    RAW_PACKAGE_URL, _JSDELIVR_MANIFEST[1], _RAW_ALT_URL,
)
_NPM_TAGS_PROBES = (
    "https://registry.npmjs.org/-/package/@deepseek-ai/dsh/dist-tags",
    "https://registry.npmmirror.com/-/package/@deepseek-ai/dsh/dist-tags",
    NPM_LATEST_URL,
    "https://registry.npmmirror.com/@deepseek-ai/dsh/latest",
)
_NPM_PACKUMENT_PROBES = (
    "https://registry.npmjs.org/@deepseek-ai/dsh",
    "https://registry.npmmirror.com/@deepseek-ai/dsh",
    "https://registry.npmjs.org/@deepseek-ai/dsh",
)
_GH_COMMITS_PROBES = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits?per_page=6",
)
_GH_TAGS_PROBES = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/tags?per_page=100",
    f"https://data.jsdelivr.com/v1/package/gh/{GITHUB_OWNER}/{GITHUB_REPO}",
)
_NPM_ABBREVIATED_ACCEPT = {"Accept": "application/vnd.npm.install-v1+json"}


def _probe_github_manifest(url: str) -> dict:
    """GitHub master 的 package.json → 官方源码版版本号与 engines。"""
    data = http_get_json(url, timeout=_PROBE_TIMEOUT)
    if not isinstance(data, dict):
        raise ValueError("manifest 不是 JSON 对象")
    version = str(data.get("version") or "").strip()
    if not version:
        raise ValueError("manifest 缺少 version")
    return {"version": version, "engines_node": (data.get("engines") or {}).get("node")}


def _probe_npm_tags(url: str) -> dict:
    """npm dist-tags（体积最小的接口）→ latest 版本。"""
    data = http_get_json(url, timeout=_PROBE_TIMEOUT)
    tags = {str(k): str(v) for k, v in (data or {}).items()} if isinstance(data, dict) else {}
    if not tags.get("latest"):
        raise ValueError("dist-tags 缺少 latest")
    return {"version": tags["latest"], "dist_tags": tags}


def _probe_npm_latest(url: str) -> dict:
    """npm 单版本接口（@deepseek-ai/dsh/latest）→ latest 版本 + engines。"""
    data = http_get_json(url, timeout=_PROBE_TIMEOUT)
    if not isinstance(data, dict):
        raise ValueError("latest 不是 JSON 对象")
    version = str(data.get("version") or "").strip()
    if not version:
        raise ValueError("latest 缺少 version")
    return {"version": version, "engines_node": (data.get("engines") or {}).get("node")}


def _probe_npm_version_channel(url: str) -> dict:
    """npm 版本通道：dist-tags 与 latest 两个小接口，谁先回用谁（都只产出版本号）。"""
    if url.rstrip("/").endswith("/latest"):
        return _probe_npm_latest(url)
    return _probe_npm_tags(url)


def _probe_npm_packument(url: str) -> dict:
    """npm 包元数据（abbreviated）→ 全部发布版本 + dist-tags + engines。

    用 Accept: application/vnd.npm.install-v1+json 取精简包元数据（本项目约 20 万字节），
    比 `npm view` 子进程（实测 33s，还要等 Node 启动）快得多，也不再依赖本机装没装 npm。
    """
    data = http_get_json(url, timeout=_PROBE_TIMEOUT, headers=_NPM_ABBREVIATED_ACCEPT)
    if not isinstance(data, dict):
        raise ValueError("packument 不是 JSON 对象")
    raw_tags = data.get("dist-tags") or {}
    tags = {str(k): str(v) for k, v in raw_tags.items()} if isinstance(raw_tags, dict) else {}
    versions_meta = data.get("versions") or {}
    versions = [str(v) for v in versions_meta] if isinstance(versions_meta, dict) else []
    if not tags.get("latest") and not versions:
        raise ValueError("packument 为空")
    latest = tags.get("latest") or ""
    engines_node = None
    latest_meta = versions_meta.get(latest) if isinstance(versions_meta, dict) else None
    if isinstance(latest_meta, dict):
        engines_node = (latest_meta.get("engines") or {}).get("node")
    return {"version": latest, "dist_tags": tags, "versions": versions,
            "engines_node": engines_node}


def _probe_gh_commits(url: str) -> dict:
    """最近提交 → 最新 commit 与日期（用于「最近更新」展示）。"""
    items = http_get_json(url, timeout=_PROBE_TIMEOUT)
    if not isinstance(items, list) or not items:
        raise ValueError("commits 为空")
    recent = []
    for c in items:
        commit = c.get("commit") or {}
        message = commit.get("message") or ""
        first = message.splitlines()[0].strip()[:110] if message else ""
        date = (commit.get("committer") or {}).get("date") or ""
        recent.append({"sha": str(c.get("sha", ""))[:8], "msg": first, "date": date[:10]})
    top = items[0]
    return {"commit": str(top.get("sha", ""))[:10],
            "date": ((top.get("commit") or {}).get("committer") or {}).get("date"),
            "recent": recent}


def _probe_gh_tags(url: str) -> list:
    """官方发布过的 tag 版本（api.github.com 或 jsDelivr 数据 API）。"""
    data = http_get_json(url, timeout=_PROBE_TIMEOUT)
    raw_names: list = []
    if isinstance(data, list):          # api.github.com/repos/.../tags
        raw_names = [str(item.get("name", "")) for item in data if isinstance(item, dict)]
    elif isinstance(data, dict):        # data.jsdelivr.com/v1/package/gh/...
        tags = data.get("tags")
        if isinstance(tags, dict):
            raw_names = [str(k) for k in tags]
        elif isinstance(tags, list):
            raw_names = [str(x) for x in tags]
        if not raw_names:
            raw_names = [str(x) for x in (data.get("versions") or [])]
    out = []
    for name in raw_names:
        if name.startswith("dsh-v"):
            name = name[len("dsh-v"):]
        if name:
            out.append(name)
    if not out:
        raise ValueError("tags 为空")
    return out


def _match_node_range(version: str, ranges: str | None):
    """
    粗略判断 version 是否满足 engines.node 表达式。
    支持空格分隔的多个约束（隐含 AND），及 `||` 分支。
    返回 True / False；无法解析时返回 None。
    """
    if not ranges or not version:
        return None
    try:
        cur = tuple(int(x) for x in re.findall(r"\d+", version)[:3])
    except Exception:  # noqa: BLE001
        return None

    def eval_one(cond: str) -> bool | None:
        cond = cond.strip()
        m = re.match(r"^(>=|<=|>|<|=|\^|~)?\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$", cond)
        if not m:
            return None
        op, maj, mnr, pat = m.group(1) or "=", m.group(2), m.group(3), m.group(4)
        base = (int(maj), int(mnr or 0), int(pat or 0))
        if op == "=":
            return cur[:3] == base
        if op == "^":
            # 主版本 0 时 ^ 只锁 minor（简化为锁前两位）
            if base[0] == 0:
                return cur[:2] == base[:2]
            return cur[0] == base[0] and cur[1:] >= base[1:]
        if op == "~":
            return cur[:2] == base[:2] and cur[2] >= base[2]
        if op == ">=":
            return cur >= base
        if op == ">":
            return cur > base
        if op == "<=":
            return cur <= base
        if op == "<":
            return cur < base
        return None

    for branch in str(ranges).split("||"):
        parts = re.split(r"\s+", branch.strip())
        ok = True
        for part in parts:
            if not part:
                continue
            r = eval_one(part)
            if r is False:
                ok = False
                break
            if r is None:
                return None  # 出现无法解析的分支
        if ok:
            return True
    return False


def _empty_official() -> dict:
    """官方版本信息骨架（字段与旧版保持一致，界面/测试都依赖这些键）。"""
    return {
        "github": {"ok": False, "version": None, "commit": None, "date": None,
                   "error": None, "tags": [], "engines_node": None, "recent": []},
        "npm": {"ok": False, "version": None, "dist_tags": {}, "versions": [],
                "engines_node": None, "error": None},
    }


def _parallel_probe(candidates: dict, budget: float,
                    required: list | None = None) -> dict:
    """并发执行候选抓取，每个 key 取第一个成功结果。

    candidates: {key: [无参函数, ...]}；函数成功返回值、失败抛异常。
    required:  「必需信息」的满足条件，形如 [{"gh_manifest"}, {"a", "b"}]——
               每个集合里任意一个 key 有结果即算满足；全部条件满足就提前返回，
               不必干等可选项（例如 GitHub 的「最近提交」接口）超时。
    返回 {key: value 或 None}，总等待不超过 budget 秒。
    没跑完的请求是守护线程：函数返回后它们自行结束，不会拖住进程退出
    （旧实现每个请求都阻塞到超时，这是「点一次检测要等 90 秒」的病根）。
    """
    needed = [set(group) for group in (required or [])]

    def satisfied() -> bool:
        return all(any(key in results for key in group) for group in needed)

    lock = threading.Lock()
    results: dict = {}
    failures = {key: 0 for key in candidates}
    remaining = set(candidates)
    finished = threading.Event()

    def runner(key, fn):
        try:
            value = fn()
            ok = True
        except Exception:  # noqa: BLE001
            value, ok = None, False
        with lock:
            if ok:
                if key not in results:
                    results[key] = value
                remaining.discard(key)
            else:
                failures[key] += 1
                if key not in results and failures[key] >= len(candidates[key]):
                    results[key] = None
                    remaining.discard(key)
            if not remaining or (needed and satisfied()):
                finished.set()

    for key, fns in candidates.items():
        for fn in fns:
            threading.Thread(target=runner, args=(key, fn), daemon=True,
                             name=f"dshu-probe-{key}").start()
    finished.wait(budget)
    with lock:
        return {key: results.get(key) for key in candidates}


def _merge_official(parts: dict, previous: dict | None = None) -> dict:
    """把各数据源的抓取结果合并成旧版 fetch_official_versions 的结构。

    previous 是上一次缓存的结果：只有 tags / versions 这类「历史清单」允许在
    抓取失败时沿用旧值（它们只影响分级展示）；latest 版本必须来自本轮抓取，
    拿不到就如实报告失败，绝不拿旧值假装「已是最新」。
    """
    out = _empty_official()
    prev = previous if isinstance(previous, dict) else {}
    prev_gh = prev.get("github") or {}
    prev_npm = prev.get("npm") or {}

    # —— GitHub master package.json ——
    gh = out["github"]
    manifest = parts.get("gh_manifest")
    if isinstance(manifest, dict) and manifest.get("version"):
        gh["version"] = str(manifest["version"])
        gh["engines_node"] = manifest.get("engines_node")
        gh["ok"] = True
    else:
        gh["error"] = t("所有 GitHub 源均不可达")

    # —— 最近提交（可选，失败不影响「是否有更新」判断）——
    commits = parts.get("gh_commits")
    if isinstance(commits, dict) and commits.get("recent"):
        gh["recent"] = commits["recent"]
        gh["commit"] = commits.get("commit")
        gh["date"] = commits.get("date")

    # —— GitHub tags：失败沿用旧清单 ——
    tags = parts.get("gh_tags")
    if isinstance(tags, list) and tags:
        gh["tags"] = [str(x) for x in tags]
    else:
        gh["tags"] = [str(x) for x in (prev_gh.get("tags") or [])]

    # —— npm ——
    npm = out["npm"]
    packument = parts.get("npm_packument") if isinstance(parts.get("npm_packument"), dict) else {}
    tags_view = parts.get("npm_tags") if isinstance(parts.get("npm_tags"), dict) else {}
    dist_tags: dict = {}
    if packument.get("dist_tags"):
        dist_tags.update({str(k): str(v) for k, v in packument["dist_tags"].items()})
    if tags_view.get("dist_tags"):
        dist_tags.update({str(k): str(v) for k, v in tags_view["dist_tags"].items()})
    npm["dist_tags"] = dist_tags
    versions = [str(x) for x in (packument.get("versions") or [])]
    if not versions:
        versions = [str(x) for x in (prev_npm.get("versions") or [])]
    npm["versions"] = versions
    npm["version"] = (dist_tags.get("latest")
                      or tags_view.get("version")
                      or packument.get("version") or None)
    npm["ok"] = bool(npm["version"])
    npm["engines_node"] = packument.get("engines_node") or tags_view.get("engines_node")
    if not npm["ok"]:
        npm["error"] = t("所有 npm 源均不可达")
    # npm 未单独声明 engines 时回退官方仓库 master 的 engines（同一项目）
    if not npm["engines_node"]:
        npm["engines_node"] = gh.get("engines_node")
    return out


def official_cache_file() -> Path:
    """官方版本缓存文件（与设置文件同目录，测试/便携模式可用环境变量覆盖）。"""
    return _settings_dir() / "official-cache.json"


def load_official_cache() -> dict:
    """读取官方版本缓存，返回 {"saved_at": str, "data": dict}；损坏时返回 {}。"""
    data = _read_json(official_cache_file())
    return data if isinstance(data, dict) else {}


def _cache_age_seconds(entry: dict) -> float | None:
    """缓存写入至今的秒数；时间戳解析失败返回 None。"""
    try:
        saved = datetime.datetime.fromisoformat(str(entry.get("saved_at") or ""))
    except Exception:  # noqa: BLE001
        return None
    return max(0.0, (datetime.datetime.now() - saved).total_seconds())


def save_official_cache(data: dict, saved_at: str | None = None) -> str:
    """写入官方版本缓存，返回写入的时间戳；失败返回空串（不抛异常）。"""
    stamp = saved_at or datetime.datetime.now().isoformat(timespec="seconds")
    try:
        target = official_cache_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps({"saved_at": stamp, "data": data},
                                  ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(tmp, target)
        return stamp
    except Exception:  # noqa: BLE001
        return ""


def _official_is_complete(data: dict) -> bool:
    """两条关键信息（GitHub master 版本、npm latest）都拿到了才算完整。

    抓取不完整（比如网络整段断掉）时缓存只保留 30 秒，避免一次失败把
    之后 5 分钟的「检测」都锁死在错误结果上。
    """
    if not isinstance(data, dict):
        return False
    gh = data.get("github") if isinstance(data.get("github"), dict) else {}
    npm = data.get("npm") if isinstance(data.get("npm"), dict) else {}
    return bool((gh or {}).get("version") and (npm or {}).get("version"))


def fetch_official_versions(fresh: bool = False) -> dict:
    """
    获取官方最新版本信息（GitHub master + npm），5 分钟内重复调用直接吃缓存。

    返回结构见 _empty_official()：
      github: ok/version/commit/date/error/tags/engines_node/recent
      npm:    ok/version/dist_tags/versions/engines_node/error
    fresh=True 强制重新联网抓取（发布验证等场景用）。
    """
    cache = load_official_cache()
    age = _cache_age_seconds(cache) if cache else None
    previous = cache.get("data") if isinstance(cache.get("data"), dict) else None
    if not fresh and age is not None and previous is not None:
        ttl = OFFICIAL_CACHE_TTL if _official_is_complete(previous) else OFFICIAL_FAIL_TTL
        if age <= ttl:
            return copy.deepcopy(previous)
    candidates = {
        "gh_manifest": [lambda url=u: _probe_github_manifest(url)
                        for u in _GITHUB_MANIFEST_PROBES],
        "npm_tags": [lambda url=u: _probe_npm_version_channel(url)
                     for u in _NPM_TAGS_PROBES],
        "npm_packument": [lambda url=u: _probe_npm_packument(url)
                          for u in _NPM_PACKUMENT_PROBES],
        "gh_commits": [lambda url=u: _probe_gh_commits(url) for u in _GH_COMMITS_PROBES],
        "gh_tags": [lambda url=u: _probe_gh_tags(url) for u in _GH_TAGS_PROBES],
    }
    parts = _parallel_probe(
        candidates, OFFICIAL_FETCH_BUDGET,
        # 只要拿到「GitHub master 版本」和「任一 npm 版本通道」，UI 就能判断有没有更新；
        # 「最近提交 / tags 清单」只是展示细节，不该让它们把检测拖到超时。
        required=[{"gh_manifest"}, {"npm_tags", "npm_packument"}],
    )
    out = _merge_official(parts, previous)
    save_official_cache(out)
    return out


# ---------------------------------------------------------------------------
# 检查「更新器自身」是否有新版本
# ---------------------------------------------------------------------------
def _pick_self_latest(releases: list) -> dict | None:
    """从 GitHub Releases 列表挑出「最近发布」的一个（纯函数，便于测试）。

    刻意按**发布时间**而不是版本号挑选：本仓库历史 tag 存在版本号倒挂
    （v1.0.1 指向的提交比 v0.6.7 更早），按版本号挑会误报「有新版本」。
    忽略草稿（draft）与缺少 tag 的条目。
    """
    if not isinstance(releases, list):
        return None
    usable = [r for r in releases
              if isinstance(r, dict)
              and not r.get("draft")
              and str(r.get("tag_name") or "").strip()]
    if not usable:
        return None
    usable.sort(key=lambda r: str(r.get("published_at") or r.get("created_at") or ""),
                reverse=True)
    top = usable[0]
    return {
        "tag": str(top["tag_name"]).strip(),
        "date": str(top.get("published_at") or top.get("created_at") or ""),
        "url": str(top.get("html_url") or SELF_REPO_URL),
        "source": "release",
    }


SELF_CACHE_TTL = 300.0


def _self_cache_file() -> Path:
    """「更新器自身最新发布」缓存文件（与设置文件同目录）。"""
    return _settings_dir() / "self-cache.json"


def _read_self_cache(fresh: bool) -> dict:
    """读取远端最新发布缓存；只缓存候选本身，是否更新的判断每次都现算。"""
    if fresh:
        return {}
    data = _read_json(_self_cache_file())
    if not isinstance(data, dict):
        return {}
    candidate = data.get("candidate")
    if not isinstance(candidate, dict) or not candidate.get("tag"):
        return {}
    age = _cache_age_seconds(data)
    if age is None or age > SELF_CACHE_TTL:
        return {}
    return candidate


def _save_self_cache(candidate: dict) -> None:
    """写入远端最新发布缓存；失败静默（缓存只是加速，不该影响主流程）。"""
    try:
        target = _self_cache_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(
            {"saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
             "candidate": candidate}, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(tmp, target)
    except Exception:  # noqa: BLE001
        pass


def fetch_self_latest(current_version: str = "", fresh: bool = False) -> dict:
    """查询本更新器自身在 GitHub 上的最新发布，判断是否需要更新。

    结果缓存 5 分钟（SELF_CACHE_TTL）：重复调用直接吃缓存，不再打 GitHub API。
    返回 dict：
      ok         查询是否成功
      current    当前版本（原样回传）
      latest     远端最新版本号（去掉 v 前缀）
      tag        远端原始 tag 名
      date       发布时间（ISO8601，可能为空）
      url        发布页面地址
      source     release / tag
      has_update 是否存在比当前更新的版本
      note       需要额外提示用户的说明（可为空）
      error      失败原因（ok=False 时）
    """
    res = {
        "ok": False, "current": current_version, "latest": "", "tag": "",
        "date": "", "url": SELF_REPO_URL, "source": "", "has_update": False,
        "note": "", "error": "",
    }

    cand = _read_self_cache(fresh) or None
    if cand is None:
        try:
            cand = _pick_self_latest(http_get_json(SELF_RELEASES_URL, timeout=_PROBE_TIMEOUT))
        except Exception as e:  # noqa: BLE001
            res["error"] = t("无法访问 GitHub Releases 接口：{p1}: {e}", p1=type(e).__name__, e=e)

        if cand is None:
            # 退回用 tags（此时没有发布时间，按版本号取最大的那个）
            try:
                tags = http_get_json(SELF_TAGS_URL, timeout=_PROBE_TIMEOUT)
            except Exception as e:  # noqa: BLE001
                res["error"] = res["error"] or t("无法访问 GitHub Tags 接口：{p1}: {e}",
                                                 p1=type(e).__name__, e=e)
                tags = None
            if isinstance(tags, list) and tags:
                best = max(tags, key=lambda t: version_key(str(t.get("name") or "")))
                cand = {
                    "tag": str(best.get("name") or "").strip(),
                    "date": "",
                    "url": f"{SELF_REPO_URL}/releases",
                    "source": "tag",
                }
        if cand is not None:
            _save_self_cache(cand)

    if cand is None:
        res["error"] = res["error"] or t("远端没有可用的 Release 或 Tag。")
        return res

    res.update({"ok": True, "tag": cand["tag"], "date": cand["date"],
                "url": cand["url"], "source": cand["source"],
                "latest": cand["tag"].lstrip("vV")})

    cmp = compare_versions(res["latest"], current_version) if current_version else 1
    res["has_update"] = cmp > 0
    if current_version and cmp < 0:
        # 远端最近发布的版本号反而更低。最常见的原因是「本地版本还没发布到
        # GitHub」（正常状态），少数情况才是历史 tag 顺序异常，所以措辞保持中性，
        # 不要一律说成异常。
        res["note"] = t("远端最近发布的是 {p1}，低于当前版本 {p2}；通常表示当前版本尚未发布到 GitHub。",
                        p1=res['latest'], p2=current_version)
    return res


# ---------------------------------------------------------------------------
# 源码检出检测
# ---------------------------------------------------------------------------
def _looks_like_checkout_dir(path: Path) -> bool:
    """判断目录是否为 DSH 源码检出，**不排除** .dsh-bak-* 备份目录。

    回滚时需要校验的恰恰是备份目录的内容，因此不能用 _is_source_checkout
    （它以排除备份目录为职责）。
    """
    pkg = Path(path) / "package.json"
    if not pkg.is_file():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:  # noqa: BLE001
        return False
    return data.get("name") == "@deepseek-ai/dsh-root"


def _is_source_checkout(path: Path) -> bool:
    """判定目录是否为 DSH 源码检出根：package.json name == @deepseek-ai/dsh-root。
    自动排除本工具生成的备份目录（*.dsh-bak-*）。"""
    if ".dsh-bak-" in path.name:
        return False
    pkg = path / "package.json"
    if not pkg.is_file():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:  # noqa: BLE001
        return False
    if data.get("name") != "@deepseek-ai/dsh-root":
        return False
    # 进一步确认形态：apps/cli/src/bin.ts 或 scripts 存在
    return (path / "apps" / "cli" / "src" / "bin.ts").exists() or (
        path / "apps" / "cli" / "package.json"
    ).exists()


def _probe_dir(d: Path, found: list, depth: int):
    """浅层探测一个候选目录：本身是检出则记录，否则看它的子目录（限 depth 层）。"""
    try:
        if _is_source_checkout(d):
            if not any(p == d for p, _, _ in found):
                ver = _read_dir_version(d)
                found.append((d, "source", ver))
            return
    except Exception:  # noqa: BLE001
        return
    if depth <= 0:
        return
    try:
        children = [c for c in d.iterdir() if c.is_dir()]
    except Exception:  # noqa: BLE001
        return
    for c in children:
        name = c.name.lower()
        if any(h in name for h in _SRC_HINTS):
            try:
                if _is_source_checkout(c):
                    if not any(p == c for p, _, _ in found):
                        found.append((c, "source", _read_dir_version(c)))
            except Exception:  # noqa: BLE001
                pass
            else:
                _probe_dir(c, found, depth - 1)


def _read_dir_version(path: Path) -> str:
    try:
        data = json.loads((path / "package.json").read_text(encoding="utf-8-sig", errors="replace"))
        return data.get("version") or ""
    except Exception:  # noqa: BLE001
        return ""


def _list_fixed_drives() -> list:
    drives = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        p = f"{letter}:\\"
        if os.path.exists(p):
            drives.append(Path(p))
    if not drives:
        drives = [Path.cwd().anchor and Path(Path.cwd().anchor)]  # type: ignore[list-item]
    return drives


def find_source_checkouts() -> list:
    """
    自动搜索源码检出。返回 [(Path, kind, version), ...]
    搜索范围：所有固定盘根目录下名称含 harness/deepseek 的目录（限两层），
    加上用户主目录、DSH_HOME 旁的常见位置。
    """
    found: list = []
    roots = _list_fixed_drives()
    for extra in (HOME, DSH_HOME.parent if DSH_HOME.parent != HOME else None):
        if extra and extra not in roots:
            roots.append(extra)
    for root in roots:
        try:
            entries = [e for e in root.iterdir() if e.is_dir()]
        except Exception:  # noqa: BLE001
            continue
        for e in entries:
            name = e.name.lower()
            if any(h in name for h in _SRC_HINTS):
                _probe_dir(e, found, depth=1)
    return found


# ---------------------------------------------------------------------------
# npm 全局 / profile 检测
# ---------------------------------------------------------------------------
def _npm_root_global() -> Path | None:
    """尝试用 npm root -g 拿全局 node_modules 目录（短超时）。"""
    for exe in ("npm", "npm.cmd"):
        path = shutil.which(exe)
        if not path:
            continue
        try:
            r = subprocess.run(
                [path, "root", "-g"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if r.returncode == 0:
                p = Path((r.stdout or "").strip())
                if p.is_dir():
                    return p
        except Exception:  # noqa: BLE001
            pass
    for fb in _NPM_GLOBAL_FALLBACKS:
        if fb.is_dir():
            return fb
    return None


def find_npm_global() -> list:
    """查找 npm 全局 @deepseek-ai/dsh。返回 [(Path, kind, version), ...]"""
    root = _npm_root_global()
    if not root:
        return []
    pkg = root / "@deepseek-ai" / "dsh" / "package.json"
    if not pkg.is_file():
        return []
    try:
        data = json.loads(pkg.read_text(encoding="utf-8-sig", errors="replace"))
        return [(pkg.parent, INSTALL_KIND_NPM, data.get("version") or "")]
    except Exception:  # noqa: BLE001
        return [(pkg.parent, INSTALL_KIND_NPM, "")]


def find_profiles() -> list:
    """
    查找 .dsh/profiles 下的运行 profile 以及 CLI 运行时版本。
    返回 [(profile_dir, kind, version, cli_version), ...]，
    kind=profile；version 取 profile 里可读到的 dsh 包版本或父级 CLI 版本。
    """
    profiles_root = DSH_HOME / "profiles"
    if not profiles_root.is_dir():
        return []
    # CLI / 运行时版本：profiles/node_modules/@deepseek-ai/dsh
    cli_version = ""
    cli_pkg = profiles_root / "node_modules" / "@deepseek-ai" / "dsh" / "package.json"
    if cli_pkg.is_file():
        try:
            cli_version = json.loads(cli_pkg.read_text(encoding="utf-8-sig", errors="replace")).get(
                "version", ""
            )
        except Exception:  # noqa: BLE001
            cli_version = ""
    found = []
    try:
        entries = sorted([e for e in profiles_root.iterdir() if e.is_dir()])
    except Exception:  # noqa: BLE001
        entries = []
    for d in entries:
        if d.name == "node_modules":
            continue
        # 以含 package.json 的 profile 为准（web 等）
        manifest = d / "package.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8-sig", errors="replace"))
        except Exception:  # noqa: BLE001
            data = {}
        if not data.get("name", "").startswith("dsh-profile"):
            continue
        # profile 内 node_modules 里若直接装有 dsh 包则用它的版本
        ver = ""
        for cand in (
            d / "node_modules" / "@deepseek-ai" / "dsh" / "package.json",
            profiles_root / "node_modules" / "@deepseek-ai" / "dsh" / "package.json",
        ):
            if cand.is_file():
                try:
                    ver = json.loads(
                        cand.read_text(encoding="utf-8-sig", errors="replace")
                    ).get("version", "")
                except Exception:  # noqa: BLE001
                    pass
                if ver:
                    break
        found.append((d, INSTALL_KIND_PROFILE, ver or cli_version, cli_version))
    # 若没有任何带 package.json 的 profile 目录，仍然记录 profiles 根本身
    if not found:
        found.append((profiles_root, INSTALL_KIND_PROFILE, cli_version, cli_version))
    return found


def resolve_runtime_source_root(profile_dir: Path) -> Path | None:
    """运行时 profile 的 dsh 运行时若其实指向一个源码检出，返回检出根目录。

    典型情况：`~/.dsh/profiles/node_modules/@deepseek-ai/dsh` 是指向
    `<checkout>/apps/cli` 的 junction（本机就是这样）。此时「更新这个 profile」
    与「更新那个源码检出」是同一件事，插件可以把更新按钮指向检出根目录。
    纯 npm 安装（不在源码检出里）的运行时返回 None，这类运行时不在插件更新范围。
    """
    profile_dir = Path(profile_dir)
    candidates = [
        profile_dir / "node_modules" / "@deepseek-ai" / "dsh",
        DSH_HOME / "profiles" / "node_modules" / "@deepseek-ai" / "dsh",
    ]
    for cand in candidates:
        try:
            if not cand.exists():
                continue
            real = Path(os.path.realpath(str(cand)))
        except Exception:  # noqa: BLE001
            continue
        for root in (real, real.parent, real.parent.parent, real.parent.parent.parent):
            try:
                if _is_source_checkout(root):
                    return root
            except Exception:  # noqa: BLE001
                pass
    return None


# ---------------------------------------------------------------------------
# 汇总检测
# ---------------------------------------------------------------------------
def _norm_path_key(path: str | Path) -> str:
    """路径规范化键：解析 junction/symlink 真身 + 小写，用于重复自检。"""
    try:
        real = os.path.realpath(str(path))
    except Exception:  # noqa: BLE001
        real = str(path)
    try:
        real = os.path.normcase(os.path.normpath(real))
    except Exception:  # noqa: BLE001
        pass
    return real


def _dedupe_installs(installs: list) -> dict:
    """按真实路径去重；返回 (去重列表, 统计信息)。"""
    seen: dict[str, dict] = {}
    removed: list[dict] = []
    for inst in installs:
        key = _norm_path_key(inst["path"])
        if key in seen:
            removed.append(inst)
            continue
        seen[key] = inst
    return {"installs": list(seen.values()), "removed": removed}


def detect_all(fetch_official: bool = True, fresh: bool = False) -> dict:
    """检测本机所有 DSH 安装并拉取官方版本。返回 dict。

    fetch_official=False 时跳过所有联网请求（界面可以先用本地结果秒开，
    再异步补上官方版本），此时 official 为 None、各安装的 status 为 unknown。
    fresh=True 时忽略官方版本缓存，强制重新联网抓取。
    """
    result = {"installs": [], "official": None, "errors": [],
              "selfcheck": {"duplicates": 0, "notes": []}}
    # 源码检出
    for path, kind, ver in find_source_checkouts():
        result["installs"].append(
            {
                "path": str(path),
                "kind": kind,
                "kind_label": t("源码检出"),
                "version": ver,
                "updateable": True,  # 源码检出支持整目录替换
                "update_target": str(path),
            }
        )
    # npm 全局
    for path, kind, ver in find_npm_global():
        result["installs"].append(
            {
                "path": str(path),
                "kind": kind,
                "kind_label": t("npm 全局"),
                "version": ver,
                "updateable": False,  # npm 全局走 npm i -g，另行处理
                "update_target": "",
            }
        )
    # profile
    for path, kind, ver, cli_ver in find_profiles():
        # 运行时若指向源码检出（junction），插件里也能直接更新它
        runtime_root = resolve_runtime_source_root(Path(path))
        result["installs"].append(
            {
                "path": str(path),
                "kind": kind,
                "kind_label": t("运行时 profile ({p1})", p1=Path(path).name),
                "version": ver,
                "cli_version": cli_ver,
                "updateable": False,
                "update_target": str(runtime_root) if runtime_root else "",
            }
        )

    # —— 自检 1：同一真实位置去重（防 junction/链接导致同一安装出现多次）——
    dedup = _dedupe_installs(result["installs"])
    result["installs"] = dedup["installs"]
    result["selfcheck"]["duplicates"] = len(dedup["removed"])
    if dedup["removed"]:
        result["selfcheck"]["notes"].append(
            t("已合并 %d 处指向同一真实路径的重复安装：%s")
            % (len(dedup["removed"]), t("、").join(r["path"] for r in dedup["removed"][:3]))
        )

    # 官方版本（--offline 时整块跳过，一个网络请求都不发）
    result["official"] = fetch_official_versions(fresh=fresh) if fetch_official else None
    off = result["official"] or {}
    official_gh = (off.get("github") or {}).get("version") or ""
    official_npm = (off.get("npm") or {}).get("version") or ""
    for inst in result["installs"]:
        local = inst["version"] or ""
        if not local:
            inst["status"] = t("无法读取版本")
        elif inst["kind"] == INSTALL_KIND_SOURCE:
            ref, ref_ok = official_gh, bool(official_gh)
            ref_kind = "github"
        else:
            ref, ref_ok = official_npm, bool(official_npm)
            ref_kind = "npm"
        inst["ref_version"] = ref or ""
        inst["ref_kind"] = ref_kind
        if local:
            if ref_ok and compare_versions(ref, local) > 0:
                inst["status"] = t("可更新")
            elif not ref_ok and not (official_gh and official_npm):
                inst["status"] = t("官方版本获取失败")
            else:
                inst["status"] = t("已是最新")
            # —— 稳定性 / 适配性评估（依据官网信息）——
            inst["assess"] = (assess_version(local, result["official"], kind_for_ref=ref_kind)
                              if fetch_official else
                              {"grade": "unknown", "grade_label": GRADE_LABELS.get("unknown", ""),
                               "reason": t("未联网检测")})
            inst["grade"] = inst["assess"]["grade"]
            inst["grade_label"] = inst["assess"]["grade_label"]
        else:
            inst["grade"] = "unstable"
            inst["grade_label"] = GRADE_LABELS["unstable"]
            inst["assess"] = {"grade": "unstable", "grade_label": GRADE_LABELS["unstable"],
                              "reason": t("版本号为空，官网无法核实")}
    # —— 自检 2：官方参照目标本身也做评估（更新文件稳定性）——
    if fetch_official and result["official"]:
        for tag, kind_for in (("github", "github"), ("npm", "npm")):
            v = result["official"][tag].get("version")
            if v:
                result["official"][tag]["assess"] = assess_version(v, result["official"],
                                                                   kind_for_ref=kind_for)
    return result


# ---------------------------------------------------------------------------
# 目录大小
# ---------------------------------------------------------------------------
def dir_size(path: Path, skip_dirs: tuple = (), limit_files: int | None = None,
             limit_seconds: float | None = None) -> int:
    """递归统计目录字节数。skip_dirs 为相对名集合（遇到即跳过整个子树）。
    跳过符号链接与 junction（防循环、防重复统计 pnpm 软链）。
    limit_files / limit_seconds：软上限，超过即返回已统计值（防超大目录拖死扫描）。"""
    total = 0
    files = 0
    t0 = time.monotonic()
    stack = [path]
    try:
        while stack:
            cur = stack.pop()
            try:
                with os.scandir(cur) as it:
                    for entry in it:
                        if limit_files is not None and files >= limit_files:
                            return total
                        if limit_seconds is not None and time.monotonic() - t0 >= limit_seconds:
                            return total
                        try:
                            if entry.is_symlink():
                                continue
                            is_junction = getattr(entry, "is_junction", None)
                            if is_junction is not None and is_junction():
                                continue
                            if entry.is_dir():
                                if entry.name not in skip_dirs and entry.name != ".git":
                                    stack.append(Path(entry.path))
                            elif entry.is_file():
                                try:
                                    total += entry.stat().st_size
                                    files += 1
                                except OSError:
                                    pass
                        except OSError:
                            continue
            except OSError:
                continue
    except Exception:  # noqa: BLE001
        pass
    return total


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.2f} MB"
    return f"{n / 1024 ** 3:.2f} GB"


def dir_created_text(path: Path) -> str:
    """目录创建（安装）时间文本；失败返回空串。ctime 在 Windows 表示创建时间。"""
    try:
        st = os.stat(path)
        ts = getattr(st, "st_ctime", 0)
        if not ts:
            ts = st.st_mtime
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# 插件检测
# ---------------------------------------------------------------------------
class ProgressReporter:
    """扫描/下载/解压共用的进度上报器：按项推进并携带已用时间与阶段名。

    - announce(name)：处理某大目录*前*先广播“正在处理 X”（不计数），
      这样即使单目录统计较慢，UI 进度也不会静止。
    - step(name)：该目录处理完成后 done+1 并广播。
    """

    def __init__(self, cb, total: int, phase: str, start_done: int = 0):
        self.cb = cb
        self.total = total
        self.done = start_done
        self.phase = phase
        self.start = time.monotonic()
        self._last_emit = 0.0

    def _emit(self, current: str = "", finished: bool = False):
        if not self.cb:
            return
        now = time.monotonic()
        # 节流：相邻两次广播至少间隔 60ms，避免 UI 队列被刷爆
        if not finished and now - self._last_emit < 0.06:
            return
        self._last_emit = now
        try:
            self.cb(
                {
                    "phase": self.phase,
                    "done": self.done,
                    "total": self.total,
                    "current": current,
                    "elapsed": now - self.start,
                    "finished": finished,
                }
            )
        except Exception:  # noqa: BLE001  （GUI 回调不应拖垮扫描）
            pass

    def announce(self, current: str = ""):
        """开始处理一项前调用：广播“正在处理 current”，不计入 done。"""
        self._emit(current)

    def step(self, current: str = ""):
        """完成一项后调用：done+1 并广播。"""
        self.done += 1
        self._emit(current)

    def finish(self):
        self._emit("", finished=True)


def _find_package_dir(name: str, search_roots: list) -> Path | None:
    """在多个 node_modules 根中定位包目录（支持 @scope/name 与扁平名）。"""
    if name.startswith("@"):
        parts = name.split("/")
        if len(parts) != 2:
            return None
        rel = Path(parts[0]) / parts[1]
    else:
        rel = Path(name)
    for root in search_roots:
        cand = root / rel
        if cand.is_dir() and (cand / "package.json").is_file():
            return cand
    return None


def _read_package_json(path: Path) -> dict:
    try:
        return json.loads((path / "package.json").read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:  # noqa: BLE001
        return {}


def profile_plugin_manifest(profile_dir: Path) -> dict:
    """返回 profile 的 package.json。"""
    return _read_package_json(profile_dir)


def scan_plugins(include_core: bool = True, on_progress=None) -> dict:
    """
    扫描 DSH 插件。

    返回：{"items":[{name, version, size, size_text, path, enabled, source}],
          "total_items": n, "errors": [], "elapsed": float, "speed": float(项/秒)}

    on_progress(rep: dict) —— 每处理完一项回调一次：
      {"phase", "done", "total", "current", "elapsed"}（current 为当前包名）。
    """
    start = time.monotonic()
    items: list = []
    errors: list = []
    seen: set = set()
    profiles_root = DSH_HOME / "profiles"
    profiles = find_profiles()
    # 收集候选 node_modules 根：仅基于已知且“必定存在”的位置，避免全盘搜索拖慢扫描：
    #  DSH 运行时根、各 profile、npm 全局。源码检出 node_modules 不作为默认来源
    #  （它内容与 profile/运行时根重复，且全盘发现源码检出开销大）。
    search_roots: list[Path] = []
    # DSH 运行时根 node_modules（内置 dsh-base / dsh-web-app 等 bundle 所在）
    if (profiles_root / "node_modules").is_dir():
        search_roots.append(profiles_root / "node_modules")
    for d, *_ in profiles:
        nm = d / "node_modules"
        if nm.is_dir():
            search_roots.append(nm)
    # npm 全局 node_modules（内置 dsh 包也会随 @deepseek-ai/dsh 装入）
    try:
        ng = _npm_root_global()
        if ng and ng not in search_roots:
            search_roots.append(ng)
    except Exception:  # noqa: BLE001
        pass
    search_roots = list(dict.fromkeys(search_roots))  # 去重且保序

    # ---- 先统计总任务数，用于精确进度 ----
    task_names: list[tuple[str, str, str]] = []   # (kind, 名称/路径, profile名)
    # 1) 启用清单：profile package.json 的 dependencies + bundles
    for profile_dir, *_ in profiles:
        manifest = profile_plugin_manifest(profile_dir)
        names = list((manifest.get("dependencies") or {}).keys())
        bundles = ((manifest.get("dsh") or {}).get("profile") or {}).get("bundles") or []
        names += [b for b in bundles if b not in names]
        for name in names:
            if name not in seen:
                seen.add(name)
                task_names.append(("enabled", name, Path(profile_dir).name))
    # 2) 运行时内置包
    if include_core:
        # 在所有候选根下找 @deepseek-ai 的 dsh-*/cordis 目录
        for root in search_roots:
            core_root = root / "@deepseek-ai"
            if not core_root.is_dir():
                continue
            try:
                for c in sorted(core_root.iterdir()):
                    if c.is_dir() and (c.name.startswith("dsh-") or c.name.startswith("cordis")):
                        key = f"@deepseek-ai/{c.name}"
                        if key not in seen:
                            seen.add(key)
                            task_names.append(("core", str(c), ""))
            except Exception:  # noqa: BLE001
                pass

    rep = ProgressReporter(on_progress, len(task_names), "plugins")
    # 任务还没开始前就广播一条，让 UI 进度条立刻“活”起来
    rep.announce(t("准备就绪，开始枚举插件目录…") if not task_names else "")

    for kind, name, profile_name in task_names:
        if kind == "enabled":
            rep.announce(t("解析启用插件 {name}", name=name))
            pkg_dir = _find_package_dir(name, search_roots)
            if pkg_dir is None:
                errors.append(t("无法解析已启用插件 {name}（未在 node_modules 找到）", name=name))
                rep.step(name)
                continue
            data = _read_package_json(pkg_dir)
            ver = data.get("version") or ""
            size = dir_size(pkg_dir, skip_dirs=("node_modules", ".git", ".pnpm"),
                            limit_files=200_000, limit_seconds=5.0)
            items.append(
                {
                    "name": name,
                    "version": ver,
                    "size": size,
                    "size_text": human_size(size),
                    "path": str(pkg_dir),
                    "enabled": True,
                    "source": f"profile:{profile_name}",
                    "installed": dir_created_text(pkg_dir),
                }
            )
        else:  # core
            c = Path(name)
            rep.announce(t("统计内置包 @deepseek-ai/{p1} 大小…", p1=c.name))
            data = _read_package_json(c)
            ver = data.get("version") or ""
            size = dir_size(c, skip_dirs=("node_modules", ".git", ".pnpm"),
                            limit_files=200_000, limit_seconds=5.0)
            items.append(
                {
                    "name": f"@deepseek-ai/{c.name}",
                    "version": ver,
                    "size": size,
                    "size_text": human_size(size),
                    "path": str(c),
                    "enabled": False,
                    "source": t("运行时内置"),
                    "installed": dir_created_text(c),
                }
            )
        rep.step(name)
    rep.finish()
    elapsed = time.monotonic() - start
    # 按启用优先、名称排序，方便阅读
    items.sort(key=lambda x: (not x["enabled"], x["name"].lower()))
    # 自检：同一真实目录只保留一项（防 junction/多来源重复）
    dedup_plugins = _dedupe_scan_items(items)
    items = dedup_plugins["items"]
    if not items and not errors:
        errors.append(
            t("未找到任何插件：请检查 DSH 数据目录是否存在，或本机是否安装了运行时插件包。\n当前搜索位置：{p1}",
              p1=DSH_HOME)
        )
    return {
        "items": items,
        "total_items": len(items),
        "errors": errors,
        "elapsed": elapsed,
        "speed": (len(items) / elapsed) if elapsed > 0 else 0.0,
        "selfcheck": {"duplicates": dedup_plugins["removed"]},
    }


def _dedupe_scan_items(items: list) -> dict:
    """按 (真实路径) 去重扫描结果，保留第一次出现者。"""
    seen: set = set()
    kept: list = []
    removed = 0
    for it in items:
        key = _norm_path_key(it.get("path", ""))
        if not key or key in seen:
            removed += 1
            continue
        seen.add(key)
        kept.append(it)
    return {"items": kept, "removed": removed}


# ---------------------------------------------------------------------------
# 技能检测
# ---------------------------------------------------------------------------
def parse_skill_version(skill_dir: Path) -> str | None:
    """从 SKILL.md frontmatter 解析 version（支持顶层 version 与 metadata.version）。"""
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        # 也可能是单个 .md 文件技能目录（skill-filesystem 支持），这里只认 SKILL.md
        return None
    try:
        text = md.read_text(encoding="utf-8-sig", errors="replace")[:4000]
    except Exception:  # noqa: BLE001
        return None
    # frontmatter: 以 --- 开头
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        end = text.find("\n...", 3)
        if end < 0:
            return None
    fm = text[3:end]
    # metadata: 缩进的 version
    m = re.search(r"^\s*version\s*:\s*[\"']?([0-9A-Za-z][0-9A-Za-z.\-]*)[\"']?\s*$", fm, re.M)
    if m:
        return m.group(1)
    return None


def scan_skills(root: Path | None = None, on_progress=None) -> dict:
    """
    扫描技能目录。默认根为 %DSH_HOME%/skills（可用 DSH_SKILLS 环境变量覆盖）。
    返回：{"items":[{name, version, size, size_text, path, has_skill_md}],
          "root": ..., "errors": [...], "elapsed": float, "speed": float(项/秒)}
    on_progress(rep) —— 每个技能目录处理完后回调。
    """
    start = time.monotonic()
    skills_root = Path(os.environ.get("DSH_SKILLS") or (root or DSH_HOME / "skills"))
    items = []
    errors = []
    if not skills_root.is_dir():
        return {
            "items": [], "root": str(skills_root),
            "errors": [t("技能目录不存在: ") + str(skills_root)],
            "elapsed": 0.0, "speed": 0.0,
        }
    try:
        entries = sorted([e for e in skills_root.iterdir()], key=lambda p: p.name.lower())
    except Exception as e:  # noqa: BLE001
        return {
            "items": [], "root": str(skills_root), "errors": [str(e)],
            "elapsed": 0.0, "speed": 0.0,
        }
    # 预筛候选（保持进度=已检查目录数）。按官方文档：用户技能根跳过 .system 子目录，
    # 并兼容“目录包 <name>/SKILL.md”与“平铺 <name>.md”两种形态。
    candidates = []
    for e in entries:
        if e.name in (".system", ".git") and e.is_dir():
            continue
        if e.is_dir():
            if (e / "SKILL.md").is_file() or (e / "README.md").is_file():
                candidates.append(e)
        elif e.suffix.lower() in (".md", ".markdown"):
            candidates.append(e)
    rep = ProgressReporter(on_progress, len(candidates), "skills")
    if not candidates:
        rep.announce(t("未发现技能目录…"))
    for e in candidates:
        # 目录技能：含 SKILL.md（或本身就是技能目录）
        if e.is_dir():
            name = e.name
            rep.announce(t("统计技能 {name} 文件与大小…", name=name))
            ver = parse_skill_version(e) or ""
            size = dir_size(e, skip_dirs=("node_modules", ".git", ".pnpm", "node_modules.bak"),
                            limit_files=200_000, limit_seconds=5.0)
            items.append(
                {
                    "name": name,
                    "version": ver,
                    "size": size,
                    "size_text": human_size(size),
                    "path": str(e),
                    "has_skill_md": (e / "SKILL.md").is_file(),
                    "installed": dir_created_text(e),
                }
            )
        # 平铺单文件技能（*.md）
        else:
            name = e.stem
            rep.announce(t("读取技能 {name}", name=name))
            size = e.stat().st_size if e.is_file() else 0
            items.append(
                {
                    "name": name,
                    "version": "",
                    "size": size,
                    "size_text": human_size(size),
                    "path": str(e),
                    "has_skill_md": False,
                    "installed": dir_created_text(e),
                }
            )
        rep.step(e.name)
    rep.finish()
    elapsed = time.monotonic() - start
    dedup_skills = _dedupe_scan_items(items)
    items = dedup_skills["items"]
    return {
        "items": items,
        "root": str(skills_root),
        "errors": errors,
        "elapsed": elapsed,
        "speed": (len(items) / elapsed) if elapsed > 0 else 0.0,
        "selfcheck": {"duplicates": dedup_skills["removed"]},
    }


# ---------------------------------------------------------------------------
# 检测最新版本 / 同步更新（插件 & 技能）
# ---------------------------------------------------------------------------
def check_plugin_latest(names: list, on_progress=None) -> dict:
    """
    对插件名列表查询官方最新版：
    - @deepseek-ai/* 与可在 npm registry 找到的包 → npm dist-tags.latest
    - 查询失败则 latest=None。
    返回 {name: {"latest": str|None, "error": str|None}}
    """
    result = {}
    rep = ProgressReporter(on_progress, len(names), "plugin-latest")
    for name in names:
        rep.announce(t("查询 {name} 最新版…", name=name))
        latest, err = None, None
        try:
            from urllib.parse import quote
            enc = quote(name, safe="")  # @scope/name → URL 编码
            data = http_get_json(f"https://registry.npmjs.org/{enc}/latest", timeout=15)
            latest = (data or {}).get("version")
            if not latest:
                err = t("npm 无该包")
        except Exception as e:  # noqa: BLE001
            err = str(e)[:80]
        result[name] = {"latest": latest, "error": err}
        rep.step(name)
    rep.finish()
    return result


def check_skill_latest(skill_items: list, on_progress=None) -> dict:
    """
    对技能条目查询来源的最新版本：
    - 目录含 .git 且有 origin → 用 git ls-remote 对比当前 HEAD 的最近 tag
    - 否则（本机为拷贝安装）→ 无法自动判定，返回 latest=None, error='本地副本（无 git 来源）'
    返回 {name: {"latest": str|None, "error": str|None, "git_ok": bool}}
    """
    result = {}
    rep = ProgressReporter(on_progress, len(skill_items), "skill-latest")
    for it in skill_items:
        name = it.get("name", "")
        path = Path(it.get("path", ""))
        rep.announce(t("检查技能 {name} 来源…", name=name))
        latest, err, git_ok = None, None, False
        if (path / ".git").is_dir():
            git_ok = True
            # 找最近 tag：ls-remote --tags origin
            try:
                r = subprocess.run(
                    ["git", "-C", str(path), "ls-remote", "--tags", "origin"],
                    capture_output=True, text=True, timeout=30,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if r.returncode == 0:
                    tags = []
                    for line in r.stdout.splitlines():
                        parts = line.split("\t")
                        if len(parts) == 2 and parts[1].endswith("^{}"):
                            continue
                        ref = parts[1].split("/")[-1] if len(parts) == 2 else ""
                        ref = ref.lstrip("v")
                        if re.match(r"^\d+\.\d+", ref):
                            tags.append(ref)
                    if tags:
                        tags.sort(key=version_key)
                        latest = tags[-1]
                    else:
                        err = t("远端无版本 tag")
                else:
                    err = t("git ls-remote 失败")
            except Exception as e:  # noqa: BLE001
                err = str(e)[:80]
        else:
            err = t("本地副本（无 git 来源，无法自动检测）")
        result[name] = {"latest": latest, "error": err, "git_ok": git_ok}
        rep.step(name)
    rep.finish()
    return result


def update_skills_git(skill_items: list, log=print) -> dict:
    """对有 git 来源的技能执行 git pull（同步更新）；返回统计。"""
    ok, failed, skipped = [], [], 0
    for it in skill_items:
        path = Path(it.get("path", ""))
        if not (path / ".git").is_dir():
            skipped += 1
            continue
        log(t("更新技能 {p1}…", p1=it.get('name', '')))
        try:
            r = subprocess.run(
                ["git", "-C", str(path), "pull", "--ff-only"],
                capture_output=True, text=True, timeout=120,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if r.returncode == 0:
                ok.append(it.get("name", ""))
                log(t("  ✔ {p1} 已更新", p1=it.get('name', '')))
            else:
                failed.append((it.get("name", ""), r.stderr.strip()[:120]))
                log(f"  ✖ {it.get('name', '')}: {r.stderr.strip()[:120]}")
        except Exception as e:  # noqa: BLE001
            failed.append((it.get("name", ""), str(e)[:120]))
    return {"ok": ok, "failed": failed, "skipped": skipped}


# ---------------------------------------------------------------------------
# 下载 / 备份 / 替换
# ---------------------------------------------------------------------------
class _Throttle:
    """限流：距上次触发超过 min_gap 秒 或 进度增量超过 min_step 才放行。"""

    def __init__(self, min_gap: float = 0.3, min_step: float = 2.0):
        self.min_gap = min_gap
        self.min_step = min_step
        self.last_t = 0.0
        self.last_pct = -100.0

    def allow(self, pct: float) -> bool:
        now = time.monotonic()
        if now - self.last_t >= self.min_gap or pct - self.last_pct >= self.min_step:
            self.last_t = now
            self.last_pct = pct
            return True
        return False


def _fmt_eta(seconds: float) -> str:
    if seconds < 0 or seconds != seconds:  # NaN
        return t("计算中…")
    if seconds < 60:
        return t("{seconds:.0f} 秒", seconds=seconds)
    return t("{p1} 分 {p2} 秒", p1=int(seconds // 60), p2=int(seconds % 60))


def _fmt_dl_progress(got: int, total: int, elapsed: float) -> str:
    pct = (got / total * 100) if total else 0.0
    remain = max(total - got, 0) if total else 0
    speed = (got / elapsed) if elapsed > 1.0 else (got / max(elapsed, 1e-9))
    eta = (remain / speed) if speed > 0 and total else 0.0
    return (
        t("已下载 {p1:.1f} / {p2:.1f} MB（{pct:.0f}%）｜剩余 {p3}｜速度 {p4:.2f} MB/s｜预计还需 {p5}｜已用 {elapsed:.1f} 秒", p1=got / 1024 / 1024, p2=total / 1024 / 1024, pct=pct, p3=human_size(remain), p4=speed / 1024 / 1024, p5=_fmt_eta(eta), elapsed=elapsed)
    )


def download_file(url: str, dest: Path, log=print, timeout: float = 120.0,
                  progress_cb=None) -> Path:
    """流式下载到 dest，返回 dest。进度行经 log 输出（限流），数值经 progress_cb 回调。"""
    req = urllib.request.Request(url, headers=UA)
    log(t("开始下载：{url}", url=url))
    throttle = _Throttle(min_gap=0.4, min_step=5.0)
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        got = 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                fh.write(chunk)
                got += len(chunk)
                if total:
                    pct = got / total * 100
                    if throttle.allow(pct):
                        elapsed = time.monotonic() - t0
                        log(t("[下载] {p1}", p1=_fmt_dl_progress(got, total, elapsed)))
                    if progress_cb:
                        progress_cb(min(pct / 100.0, 1.0))
    if progress_cb:
        progress_cb(1.0)
    log(t("下载完成：{dest}（{p1}，用时 {p2:.1f} 秒）", dest=dest, p1=human_size(got), p2=time.monotonic() - t0))
    return dest


def _extract_zip_with_progress(zip_path: Path, extract_dir: Path,
                               log=print, progress_cb=None) -> None:
    """逐文件解压，输出限流进度行。"""
    with zipfile.ZipFile(zip_path) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        total_bytes = sum(i.file_size for i in infos)
        throttle = _Throttle(min_gap=0.3, min_step=5.0)
        t0 = time.monotonic()
        done_bytes = 0
        done_files = 0
        for info in infos:
            try:
                zf.extract(info, extract_dir)
            except Exception as e:  # noqa: BLE001
                log(t("解压跳过异常文件 {p1}: {e}", p1=info.filename, e=e))
            done_bytes += info.file_size
            done_files += 1
            if total_bytes:
                pct = done_bytes / total_bytes * 100
                if throttle.allow(pct):
                    elapsed = time.monotonic() - t0
                    speed = (done_bytes / elapsed) if elapsed > 1.0 else (done_bytes / max(elapsed, 1e-9))
                    eta = ((total_bytes - done_bytes) / speed) if speed > 0 else 0.0
                    log(
                        t("[解压] 文件 {done_files}/{p1}｜{p2:.1f}/{p3:.1f} MB（{pct:.0f}%）｜速度 {p4:.2f} MB/s｜预计还需 {p5}｜已用 {elapsed:.1f} 秒", done_files=done_files, p1=len(infos), p2=done_bytes / 1024 / 1024, p3=total_bytes / 1024 / 1024, pct=pct, p4=speed / 1024 / 1024, p5=_fmt_eta(eta), elapsed=elapsed)
                    )
                if progress_cb:
                    progress_cb(min(pct / 100.0, 1.0))
        if progress_cb:
            progress_cb(1.0)
        log(t("解压完成：{done_files} 个文件，用时 {p1:.1f} 秒", done_files=done_files, p1=time.monotonic() - t0))


def _find_zip_root(zip_path: Path, extract_dir: Path, log=print, progress_cb=None) -> Path:
    """解压 zip 并返回其中包含 dsh-root package.json 的顶层目录。"""
    log(t("解压中：{p1}", p1=zip_path.name))
    _extract_zip_with_progress(zip_path, extract_dir, log=log, progress_cb=progress_cb)
    # 找 name == @deepseek-ai/dsh-root 的目录
    try:
        for child in extract_dir.iterdir():
            if not child.is_dir():
                continue
            if _is_source_checkout(child):
                return child
            # 仓库可能再包一层
            for sub in child.iterdir():
                if sub.is_dir() and _is_source_checkout(sub):
                    return sub
    except Exception:  # noqa: BLE001
        pass
    raise RuntimeError(t("下载的压缩包中未找到 DeepSeek Harness 源码根目录"))


def _is_port_open(port: int = 3080, host: str = "127.0.0.1") -> bool:
    """检测本地端口是否被监听（DSH Web UI 默认 3080）。"""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def _run_pnpm_step(target_dir: Path, args: list, log, what: str) -> None:
    """在工作目录里执行一条 pnpm 命令，输出实时写入日志；失败抛 RuntimeError。"""
    pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    if not pnpm:
        raise RuntimeError(t("未找到 pnpm。已替换源码，但未执行 {p1}；请手动运行。", p1=what))
    log(t("执行 {p1} …", p1=what))
    proc = subprocess.Popen(
        [pnpm, *args],
        cwd=str(target_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            log(line)
    code = proc.wait()
    if code != 0:
        raise RuntimeError(
            t("{p1} 失败（退出码 {p2}）。源码已替换，请手动排查。", p1=what, p2=code))


# ---------------------------------------------------------------------------
# 关闭正在运行的 DSH（更新前自动处理）
# ---------------------------------------------------------------------------
def processes_on_port(port: int = 3080) -> list:
    """返回监听指定端口的进程 [{"pid": int, "name": str}]。

    Windows 用 netstat -ano 取 PID 再查 tasklist 取进程名；其它平台用 lsof。
    取不到时返回空列表，绝不抛异常。
    """
    pids: list = []
    try:
        if os.name == "nt":
            r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                               timeout=20,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for line in (r.stdout or "").splitlines():
                parts = line.split()
                if len(parts) >= 4 and f":{port}" in parts[1] and parts[3].upper() == "LISTENING":
                    if parts[-1].isdigit():
                        pids.append(int(parts[-1]))
        else:
            r = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True,
                               text=True, timeout=20)
            for line in (r.stdout or "").splitlines():
                if line.strip().isdigit():
                    pids.append(int(line.strip()))
    except Exception:  # noqa: BLE001
        return []

    out = []
    for pid in dict.fromkeys(pids):          # 去重且保序
        name = ""
        try:
            if os.name == "nt":
                r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                   capture_output=True, text=True, timeout=15,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                first = (r.stdout or "").strip().splitlines()
                if first:
                    name = first[0].split()[0]
            else:
                r = subprocess.run(["ps", "-p", str(pid), "-o", "comm="],
                                   capture_output=True, text=True, timeout=15)
                name = (r.stdout or "").strip()
        except Exception:  # noqa: BLE001
            pass
        out.append({"pid": pid, "name": name or "?"})
    return out


def close_dsh(port: int = 3080, log=print) -> dict:
    """结束占用指定端口的进程（连同其子进程）。

    返回 {"ok": bool, "closed": [...], "errors": [...]}；任何失败都只记录不抛异常，
    由调用方决定是否继续。
    """
    procs = processes_on_port(port)
    closed, errors = [], []
    if not procs:
        log(t("未发现占用 {p1} 端口的进程。", p1=port))
        return {"ok": True, "closed": closed, "errors": errors}

    for p in procs:
        pid = p["pid"]
        try:
            if os.name == "nt":
                r = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                                   capture_output=True, text=True, timeout=30,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            else:
                r = subprocess.run(["kill", "-9", str(pid)], capture_output=True,
                                   text=True, timeout=30)
            if r.returncode == 0:
                closed.append(p)
                log(t("已关闭进程 {p1}（{p2}）。", p1=pid, p2=p["name"]))
            else:
                msg = (r.stderr or r.stdout or "").strip()[:120]
                errors.append({"pid": pid, "error": msg or "taskkill 返回非 0"})
                log(t("无法关闭进程 {p1}：{p2}", p1=pid, p2=msg or "taskkill 返回非 0"))
        except Exception as e:  # noqa: BLE001
            errors.append({"pid": pid, "error": str(e)[:120]})
            log(t("无法关闭进程 {p1}：{p2}", p1=pid, p2=str(e)[:120]))

    # 给系统一点时间释放端口
    if closed:
        for _ in range(20):
            if not _is_port_open(port):
                break
            time.sleep(0.25)
    return {"ok": not errors and not _is_port_open(port),
            "closed": closed, "errors": errors}


# ---------------------------------------------------------------------------
# 更新历史与回滚
# ---------------------------------------------------------------------------
HISTORY_LIMIT = 50


def load_history() -> list:
    """读取更新历史（最新在前）；结构不对时返回空列表。"""
    data = read_preferences().get("history")
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def append_history(entry: dict) -> bool:
    """追加一条更新历史（最新在前，超出上限则丢弃最旧的）。"""
    if not isinstance(entry, dict) or not entry.get("kind"):
        return False
    prefs = read_preferences()
    hist = prefs.get("history")
    if not isinstance(hist, list):
        hist = []
    item = dict(entry)
    item.setdefault("at", datetime.datetime.now().isoformat(timespec="seconds"))
    hist.insert(0, item)
    prefs["history"] = hist[:HISTORY_LIMIT]
    return write_preferences(prefs)


def list_source_backups(target_dir: Path) -> list:
    """列出某个源码检出旁边的备份目录（最新在前）。

    形如 <目标名>.dsh-bak-YYYYMMDD-HHMMSS，按名字倒序即时间倒序。
    """
    target_dir = Path(target_dir)
    parent = target_dir.parent
    prefix = target_dir.name + ".dsh-bak-"
    try:
        found = [p for p in parent.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    except Exception:  # noqa: BLE001
        return []
    out = []
    for p in sorted(found, reverse=True):
        out.append({"backup": str(p), "stamp": p.name[len(prefix):],
                    "version": _read_dir_version(p)})
    return out


def rollback_source(target_dir: Path, backup_dir: Path, log=print) -> dict:
    """把源码检出回滚到指定备份。

    先把当前目录整体改名存成一份新备份（避免回滚本身不可逆），再放入备份。
    返回 {"ok", "restored_from", "saved_current"}。
    """
    target_dir, backup_dir = Path(target_dir), Path(backup_dir)
    if not target_dir.is_dir():
        raise RuntimeError(t("目标目录不存在：{p1}", p1=target_dir))
    if not backup_dir.is_dir():
        raise RuntimeError(t("备份目录不存在：{p1}", p1=backup_dir))
    if not _looks_like_checkout_dir(backup_dir):
        raise RuntimeError(t("该备份不是有效的 DeepSeek Harness 源码检出：{p1}", p1=backup_dir))

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    saved = target_dir.parent / f"{target_dir.name}.dsh-bak-{ts}"
    log(t("先把当前目录存为备份 → {p1}", p1=saved))
    shutil.move(str(target_dir), str(saved))
    try:
        log(t("从备份恢复 → {p1}", p1=target_dir))
        shutil.move(str(backup_dir), str(target_dir))
    except Exception as e:  # noqa: BLE001
        log(t("恢复失败，正在还原当前目录：{e}", e=e))
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        shutil.move(str(saved), str(target_dir))
        raise RuntimeError(t("回滚失败，已还原：{e}", e=e)) from e
    ver = _read_dir_version(target_dir)
    log(t("回滚完成，当前版本：{p1}", p1=ver or t("未知")))
    return {"ok": True, "restored_from": str(backup_dir), "saved_current": str(saved),
            "version": ver}


def rollback_npm(version: str, log=print) -> dict:
    """把 npm 全局安装回滚到指定版本。没有目录级备份，只能重装旧版本。"""
    v = str(version or "").strip()
    if not v:
        raise RuntimeError(t("没有可用的旧版本号，无法回滚。"))
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise RuntimeError(t("未找到 npm，无法回滚。"))
    if _is_port_open(3080):
        raise RuntimeError(t("检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。"
                            "回滚会替换正在使用的原生模块，请先关闭 DeepSeek Harness。"))
    log(t("执行：npm install -g @deepseek-ai/dsh@{p1}", p1=v))
    proc = subprocess.Popen(
        [npm, "install", "-g", f"@deepseek-ai/dsh@{v}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            log(line)
    code = proc.wait()
    if code != 0:
        raise RuntimeError(t("npm 回滚失败（退出码 {p1}）。", p1=code))
    return {"ok": True, "version": v}


def rollback_targets(installs: list | None = None) -> dict:
    """汇总三类安装各自的可回滚项，供界面展示。

    返回 {"source": [...], "npm": [...], "profile": [...]}，每项含可读描述与
    执行回滚所需的信息。
    """
    hist = load_history()
    out = {"source": [], "npm": [], "profile": []}
    # 未传 installs 时自行扫盘：这样用户**之前已有的备份**也能列出来，
    # 不依赖历史记录（历史是本次版本才引入的）
    if installs is None:
        try:
            installs = [{"kind": INSTALL_KIND_SOURCE, "path": str(p), "version": v}
                        for p, _k, v in find_source_checkouts()]
        except Exception:  # noqa: BLE001
            installs = []

    # 源码：既看历史，也直接扫盘上的备份（历史可能被清过）
    seen = set()
    for h in hist:
        if h.get("kind") != "source":
            continue
        path = str(h.get("path") or "")
        if path and path not in seen:
            seen.add(path)
            for b in list_source_backups(Path(path)):
                out["source"].append({
                    "target": path, "backup": b["backup"], "stamp": b["stamp"],
                    "from_version": h.get("old_version") or b.get("version") or "",
                    "to_version": h.get("new_version", ""),
                    "at": h.get("at", ""),
                })
    if installs:
        for inst in installs:
            if inst.get("kind") != INSTALL_KIND_SOURCE:
                continue
            path = str(inst.get("path") or "")
            if path and path not in seen:
                seen.add(path)
                for b in list_source_backups(Path(path)):
                    out["source"].append({
                        "target": path, "backup": b["backup"], "stamp": b["stamp"],
                        "from_version": b.get("version") or "",
                        "to_version": inst.get("version", ""),
                        "at": "",
                    })

    for h in hist:
        if h.get("kind") == "npm" and h.get("old_version"):
            out["npm"].append({
                "target": h.get("path", ""), "version": h["old_version"],
                "from_version": h.get("new_version", ""),
                "to_version": h.get("old_version", ""),
                "at": h.get("at", ""),
            })
        elif h.get("kind") == "profile" and h.get("old_version"):
            out["profile"].append({
                "target": h.get("path", ""), "version": h["old_version"],
                "from_version": h.get("new_version", ""),
                "to_version": h.get("old_version", ""),
                "at": h.get("at", ""),
            })
    return out


def update_source_from_zip(
    target_dir: Path,
    run_pnpm_install: bool = False,
    log=print,
    keep_backup: bool = True,
    backup_root: Path | None = None,
    progress_cb=None,
    run_pnpm_build: bool = False,
) -> dict:
    """
    下载官方源码 zip → 备份 → 整目录替换 target_dir（保留 node_modules/.git）。

    步骤：
      1. 检查目标合法性
      2. 若 DSH Web(3080) 正在监听 → 抛错提示先关闭
      3. 下载 zip 到临时目录并解压
      4. 备份：将 target_dir 整体改名（同盘 move），node_modules/.git 随目录一起走
         备份完成后新建目标路径，再把 node_modules/.git 从备份目录移回，以加速 pnpm install
      5. 把解压出的新源码整体移入目标路径
      6. 可选：pnpm install

    progress_cb(percent: float) —— 下载/解压阶段的 0.0~1.0 进度。

    返回：{"ok": bool, "new_version": str, "backup": str, "message": str}
    """
    target_dir = Path(target_dir)
    if not target_dir.is_dir():
        raise RuntimeError(t("目标目录不存在：{target_dir}", target_dir=target_dir))
    if not _is_source_checkout(target_dir):
        raise RuntimeError(t("该目录不是 DeepSeek Harness 源码检出（package.json name 非 @deepseek-ai/dsh-root）"))
    if _is_port_open(3080):
        raise RuntimeError(
            t("检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n"
            "请先关闭正在运行的 DeepSeek Harness，再执行更新。")
        )

    old_version = _read_dir_version(target_dir)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    # 备份目录放同盘（默认同级父目录，保证 move 是瞬时的）
    backup_dir = (backup_root or target_dir.parent) / f"{target_dir.name}.dsh-bak-{ts}"

    tmp = Path(tempfile.mkdtemp(prefix="dsh-update-"))
    zip_path = tmp / "deepseek-harness.zip"
    extract_dir = tmp / "extract"
    extract_dir.mkdir()
    new_root = None
    rebuild_hint = ""
    try:
        # ---- 下载并解压 ----
        download_file(ZIP_URL, zip_path, log=log, progress_cb=progress_cb)
        new_root = _find_zip_root(zip_path, extract_dir, log=log, progress_cb=progress_cb)
        if progress_cb:
            progress_cb(1.0)
        new_version = _read_dir_version(new_root)
        log(t("官方源码版本：{new_version}（当前：{p1}）", new_version=new_version, p1=old_version or t('未知')))

        # ---- 备份（整体改名，快） ----
        log(t("备份原目录 → {backup_dir}", backup_dir=backup_dir))
        shutil.move(str(target_dir), str(backup_dir))
        log(t("备份完成（原目录已改名）"))

        try:
            # ---- 先放入新源码：此时目标路径不存在，move 即整体改名到位 ----
            log(t("写入官方源码 → {target_dir}", target_dir=target_dir))
            shutil.move(str(new_root), str(target_dir))
            new_root = None  # 已移走
            # ---- 再把 node_modules/.git 从备份目录移回新目录（加速后续 install） ----
            for k in _KEEP_DIRS:
                src = backup_dir / k
                if src.exists():
                    dst = target_dir / k
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    log(t("保留 {k}（移回新目录）…", k=k))
                    shutil.move(str(src), str(dst))
            log(t("新源码就位。"))
            # 构建产物不在官方源码 zip 里、也不在 _KEEP_DIRS 中，替换后必然消失。
            # 若用户依赖它直接启动 DSH，这里必须提示，否则更新完启动失败且看不出原因。
            try:
                _had = (backup_dir / "apps" / "cli" / "lib").exists()
                _has = (target_dir / "apps" / "cli" / "lib").exists()
                if _had and not _has:
                    rebuild_hint = t(
                        "注意：原目录中的构建产物（apps/cli/lib）未随源码保留。\n"
                        "若你用它直接启动 DSH，请重新执行：pnpm install && pnpm run build")
                    log(rebuild_hint)
            except Exception:  # noqa: BLE001
                pass
        except Exception as e:  # noqa: BLE001
            # 回滚
            log(t("替换失败，回滚中：{e}", e=e))
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            shutil.move(str(backup_dir), str(target_dir))
            raise RuntimeError(t("更新失败，已回滚：{e}", e=e)) from e

        # ---- 可选 pnpm install / pnpm run build ----
        # build 是源码版启动的必需步骤：构建产物（apps/cli/lib 等）不在源码 zip 里，
        # 也不在 _KEEP_DIRS 中，整目录替换后已经丢失。
        if run_pnpm_install:
            _run_pnpm_step(target_dir, ["install"], log, "pnpm install")
        if run_pnpm_build:
            _run_pnpm_step(target_dir, ["run", "build"], log, "pnpm run build")

        msg = t("更新完成：{p1} → {new_version}", p1=old_version or t('旧版本'), new_version=new_version)
        append_history({"kind": "source", "path": str(target_dir),
                        "old_version": old_version, "new_version": new_version,
                        "backup": str(backup_dir)})
        if rebuild_hint:
            msg = msg + "\n\n" + rebuild_hint
        if not keep_backup:
            shutil.rmtree(backup_dir, ignore_errors=True)
            backup_str = ""
        else:
            backup_str = str(backup_dir)
        log(msg)
        return {
            "ok": True,
            "new_version": new_version,
            "old_version": old_version,
            "backup": backup_str,
            "message": msg,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 插件内更新 DSH：先「暂存」，DSH 关闭后由后台看护进程应用
# ---------------------------------------------------------------------------
# 场景：DSH 网页插件必须从 DSH 正在运行的进程内部发起更新；而源码更新要整目录
# 改名 —— 实测 Windows 不允许改一个正被其他进程当作工作目录的目录（Move-Item
# 报「文件正被另一进程使用」）。所以拆成两段：
#   ① 暂存（DSH 运行中，安全）：下载官方源码 → 解压到目标同级暂存目录 → 写清单
#   ② 应用（DSH 关闭后，后台看护进程）：整目录替换（旧目录留作备份）→ 需要时
#      pnpm install / pnpm run build → 重新拉起 DSH
# 看护进程用 DETACHED_PROCESS 启动，DSH 退出不会带走它；它自己轮询端口，等 DSH
# 关掉之后再动手。
#
# 本节日志只写日志文件（排错用），刻意不经过 t()：插件界面上的文案由客户端按
# 结构化字段自己生成，`--json` 结果保持机器可读。
PENDING_SCHEMA = 1
DEFAULT_WEB_PORT = 3080
_UPDATE_WAIT_TIMEOUT = 1800.0     # 等待 DSH 关闭的最长时间（30 分钟）
_UPDATE_SWAP_RETRY = 120.0        # 目录仍被占用时的重试窗口（秒）

_UPDATE_WATCHER_TEMPLATE = '''# -*- coding: utf-8 -*-
"""dsh-updater 后台看护进程（由插件在暂存更新时自动生成）。

用法：python -X utf8 update-watcher.py <manifest.json> <updater_core.py 所在目录>

它只做一件事：等 DSH 关闭（轮询端口）→ 让 updater_core 应用暂存更新并重启 DSH。
用 DETACHED_PROCESS 启动，所以父进程（DSH）退出不会带走它。
"""
import json
import sys
import traceback
from pathlib import Path


def main() -> int:
    manifest_path = Path(sys.argv[1])
    sys.path.insert(0, sys.argv[2])
    import updater_core
    result = updater_core.watch_and_apply_pending_update(manifest_path)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # 兜底：脚本本身出错时，把 traceback 也写进清单里的日志文件
        try:
            manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
            log_path = Path(manifest.get("log_file") or (sys.argv[1] + ".log"))
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(traceback.format_exc() + "\\n")
        except Exception:
            pass
        sys.exit(1)
'''


def pending_update_file() -> Path:
    """待应用更新的清单文件（与设置同目录）。"""
    return _settings_dir() / "pending-update.json"


def update_watcher_file() -> Path:
    """看护脚本路径（每次暂存时重写；内容只依赖 updater_core）。"""
    return _settings_dir() / "update-watcher.py"


def update_watcher_log_file() -> Path:
    """看护进程日志（等待、替换、构建、重启都会写到这里）。"""
    return _settings_dir() / "update-watcher.log"


def _now_stamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _watcher_log(log_file: Path, message: str) -> None:
    """向看护日志追加一行；失败静默（日志永远不能拖垮更新）。"""
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(f"[{_now_stamp()}] {message}\n")
    except Exception:  # noqa: BLE001
        pass


def _write_pending_update(manifest: dict) -> bool:
    try:
        target = pending_update_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")
        os.replace(tmp, target)
        return True
    except Exception:  # noqa: BLE001
        return False


def load_pending_update() -> dict:
    """读取待应用更新清单；不存在/损坏时返回 {}。"""
    data = _read_json(pending_update_file())
    return data if isinstance(data, dict) and data.get("schema") == PENDING_SCHEMA else {}


def _set_pending_status(status: str, **fields) -> dict:
    """更新清单里的状态（waiting → applying → done/failed/expired/canceled）。"""
    manifest = load_pending_update()
    if not manifest:
        return {}
    manifest["status"] = status
    manifest["updated"] = _now_stamp()
    manifest.update(fields)
    _write_pending_update(manifest)
    return manifest


def _update_watcher_script() -> str:
    """生成看护脚本的源码（写盘后由 pythonw/python 脱离父进程执行）。"""
    return _UPDATE_WATCHER_TEMPLATE


def _auto_update_steps(target_dir: Path, new_root: Path) -> tuple:
    """推断这次更新要不要 pnpm install / pnpm run build。

    - build：目标目录里存在 apps/cli/lib 说明用户是从**构建产物**启动 DSH 的，
      替换源码后必须重新构建，否则重启还是旧代码；
    - install：新旧 pnpm-lock.yaml 内容不同才需要（依赖变了）。
    """
    run_build = (target_dir / "apps" / "cli" / "lib").is_dir()
    run_install = False
    try:
        # 先统一行尾再比：Windows 上 git 检出可能是 CRLF、官方 zip 是 LF，
        # 直接比字节会把「其实没变」误判成依赖变化，白白多跑一次 pnpm install。
        old_lock = (target_dir / "pnpm-lock.yaml").read_bytes().replace(b"\r\n", b"\n")
        new_lock = (new_root / "pnpm-lock.yaml").read_bytes().replace(b"\r\n", b"\n")
        run_install = old_lock != new_lock
    except Exception:  # noqa: BLE001
        run_install = False
    return run_install, run_build


def _download_source_staging(target_dir: Path, log=print) -> dict:
    """下载官方源码并解压到 target 同级的暂存目录（同分区，便于之后原子改名）。"""
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    staging = target_dir.parent / f".{target_dir.name}.dsh-stage-{ts}"
    tmp = Path(tempfile.mkdtemp(prefix="dsh-stage-"))
    try:
        zip_path = tmp / "deepseek-harness.zip"
        extract_dir = tmp / "extract"
        extract_dir.mkdir()
        log(f"开始下载官方源码：{ZIP_URL}")
        download_file(ZIP_URL, zip_path, log=log)
        new_root = _find_zip_root(zip_path, extract_dir, log=log)
        new_version = _read_dir_version(new_root)
        if not new_version:
            raise RuntimeError("下载的源码包缺少版本号")
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        shutil.move(str(new_root), str(staging))
        log(f"官方源码已暂存：{staging}（版本 {new_version}）")
        return {"staging": staging, "new_version": new_version}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _spawn_update_watcher(manifest_path: Path) -> int:
    """启动脱离 DSH 的看护进程，返回 pid（失败返回 0）。

    DETACHED_PROCESS + 无控制台解释器（pythonw）：DSH 退出后它继续干活。
    """
    script = update_watcher_file()
    try:
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(_update_watcher_script(), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        _watcher_log(update_watcher_log_file(), f"写入看护脚本失败：{type(e).__name__}: {e}")
        return 0
    python = sys.executable or "python"
    candidates = [python]
    if os.name == "nt" and python.lower().endswith("python.exe"):
        candidates.insert(0, python[: -len("python.exe")] + "pythonw.exe")
    core_dir = str(Path(__file__).resolve().parent)
    log_path = update_watcher_log_file()
    last_error = ""
    for exe in candidates[:2]:
        try:
            if not Path(exe).is_file():
                continue
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = open(log_path, "a", encoding="utf-8")
            kwargs = {
                "stdin": subprocess.DEVNULL,
                "stdout": log_handle,
                "stderr": subprocess.STDOUT,
                "cwd": str(script.parent),
                "close_fds": True,
            }
            if os.name == "nt":
                kwargs["creationflags"] = (subprocess.DETACHED_PROCESS
                                           | subprocess.CREATE_NEW_PROCESS_GROUP)
            proc = subprocess.Popen(
                [exe, "-X", "utf8", str(script), str(manifest_path), core_dir], **kwargs)
            log_handle.close()
            return int(proc.pid or 0)
        except Exception as e:  # noqa: BLE001
            last_error = f"{type(e).__name__}: {e}"
    _watcher_log(log_path, f"启动看护进程失败：{last_error or '没有可用的 Python 解释器'}")
    return 0


def _cleanup_staging(manifest: dict) -> None:
    try:
        staging = Path(str(manifest.get("staging") or ""))
        if staging and staging.is_dir():
            shutil.rmtree(staging, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass


def stage_source_update(target_dir: Path, restart: dict | None = None,
                        port: int = DEFAULT_WEB_PORT,
                        wait_timeout: float = _UPDATE_WAIT_TIMEOUT,
                        log=print) -> dict:
    """阶段一：下载官方源码到暂存目录，并启动看护进程等 DSH 关闭后应用。

    返回结构化结果（插件客户端自己出文案）：
      { ok, staged, target, staging, old_version, new_version,
        run_install, run_build, wait_port, restart, log_file, watcher_pid }
    """
    target_dir = Path(target_dir)
    if not target_dir.is_dir():
        raise RuntimeError(f"目标目录不存在：{target_dir}")
    if not _is_source_checkout(target_dir):
        raise RuntimeError("该目录不是 DeepSeek Harness 源码检出")
    # 旧任务先取消（避免两个看护进程抢同一个目标）
    previous = load_pending_update()
    if previous:
        try:
            cancel_pending_update(log=lambda *_: None)
        except Exception:  # noqa: BLE001
            pass
    old_version = _read_dir_version(target_dir)
    log(f"当前版本：{old_version or '未知'}；先下载官方源码到暂存目录…")
    got = _download_source_staging(target_dir, log=log)
    staging = got["staging"]
    new_version = got["new_version"]
    run_install, run_build = _auto_update_steps(target_dir, staging)
    restart_spec = dict(restart) if isinstance(restart, dict) else {}
    log_path = update_watcher_log_file()
    manifest = {
        "schema": PENDING_SCHEMA,
        "created": _now_stamp(),
        "updated": _now_stamp(),
        "status": "waiting",
        "target": str(target_dir),
        "staging": str(staging),
        "old_version": old_version,
        "new_version": new_version,
        "run_install": bool(run_install),
        "run_build": bool(run_build),
        "wait_port": int(port),
        "wait_timeout": float(wait_timeout),
        "restart": restart_spec,
        "log_file": str(log_path),
        "watcher_pid": 0,
        "error": "",
    }
    _write_pending_update(manifest)
    pid = _spawn_update_watcher(pending_update_file())
    manifest["watcher_pid"] = pid
    _write_pending_update(manifest)
    if not pid:
        _watcher_log(log_path, "看护进程没起来：更新已暂存，但关闭 DSH 后不会自动应用。")
    else:
        _watcher_log(log_path,
                     f"看护进程已启动（pid {pid}）：等待端口 {port} 关闭后应用更新。")
    log(f"更新已暂存：{old_version or '未知'} → {new_version}；关闭 DSH 后将自动替换并重启。")
    return {
        "ok": True,
        "staged": True,
        "target": str(target_dir),
        "staging": str(staging),
        "old_version": old_version,
        "new_version": new_version,
        "run_install": bool(run_install),
        "run_build": bool(run_build),
        "wait_port": int(port),
        "restart": bool(restart_spec),
        "log_file": str(log_path),
        "watcher_pid": pid,
    }


def _wait_dir_free(target_dir: Path, log) -> None:
    """占位兼容：真正的重试已经并入 _apply_staged_tree 的换目录循环。"""
    return None


def _apply_staged_tree(target_dir: Path, staging: Path, old_version: str,
                       new_version: str, run_install: bool, run_build: bool,
                       log=print) -> dict:
    """阶段二核心：把暂存源码换进目标目录（备份旧目录，保留 node_modules/.git）。

    失败时自动回滚到旧版本；成功返回 {ok, backup, new_version, run_install, run_build}。
    """
    target_dir = Path(target_dir)
    staging = Path(staging)
    if not target_dir.is_dir():
        raise RuntimeError(f"目标目录不存在：{target_dir}")
    if not staging.is_dir():
        raise RuntimeError(f"暂存目录不存在（更新包可能已被清理）：{staging}")
    if not _is_source_checkout(staging):
        raise RuntimeError("暂存目录不是有效的 DeepSeek Harness 源码")
    staged_version = _read_dir_version(staging)
    if new_version and staged_version and staged_version != new_version:
        raise RuntimeError(f"暂存版本不符（清单 {new_version}，实际 {staged_version}）")
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = target_dir.parent / f"{target_dir.name}.dsh-bak-{ts}"
    log(f"备份原目录 → {backup_dir}")
    # 目标目录可能还被别的进程当作工作目录（别的 DSH 实例/终端没关）：
    # 直接重试「真正的改名操作」，最多等 _UPDATE_SWAP_RETRY 秒。
    deadline = time.monotonic() + _UPDATE_SWAP_RETRY
    while True:
        try:
            shutil.move(str(target_dir), str(backup_dir))
            break
        except OSError as e:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "目标目录仍被其他进程占用（可能还有其他 DSH 实例或终端从该目录启动）。"
                    f" 请全部关闭后再试：{e}") from e
            log(f"目录仍被占用（{e}），3 秒后重试…")
            time.sleep(3)
    try:
        shutil.move(str(staging), str(target_dir))
        for keep in _KEEP_DIRS:
            src = backup_dir / keep
            if src.exists():
                log(f"保留 {keep}（移回新目录）…")
                shutil.move(str(src), str(target_dir / keep))
        if run_install:
            log("依赖可能有变化，执行 pnpm install …")
            _run_pnpm_step(target_dir, ["install"], log, "pnpm install")
        if run_build:
            log("执行 pnpm run build（源码替换后必须重建构建产物）…")
            _run_pnpm_step(target_dir, ["run", "build"], log, "pnpm run build")
    except Exception as e:  # noqa: BLE001
        log(f"应用更新失败，回滚：{type(e).__name__}: {e}")
        rollback_ok = False
        try:
            for keep in _KEEP_DIRS:
                src = target_dir / keep
                dst = backup_dir / keep
                if src.exists() and not dst.exists():
                    shutil.move(str(src), str(dst))
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            shutil.move(str(backup_dir), str(target_dir))
            rollback_ok = True
            log("已回滚到旧版本。")
        except Exception as e2:  # noqa: BLE001
            log(f"回滚失败（请手动从备份恢复）：{type(e2).__name__}: {e2}")
        raise RuntimeError(
            f"更新失败{'，已回滚到旧版本' if rollback_ok else '，回滚也失败'}：{e}") from e
    append_history({"kind": "source", "path": str(target_dir),
                    "old_version": old_version, "new_version": new_version,
                    "backup": str(backup_dir)})
    log(f"更新完成：{old_version or '旧版本'} → {new_version}（旧版本备份：{backup_dir}）")
    return {"ok": True, "new_version": new_version, "old_version": old_version,
            "backup": str(backup_dir), "run_install": run_install,
            "run_build": run_build}


def update_source_immediate(target_dir: Path, log=print) -> dict:
    """目标目录**没有被运行中的 DSH 占用**时：暂存并立即应用（不等待、不重启）。"""
    target_dir = Path(target_dir)
    if not target_dir.is_dir():
        raise RuntimeError(f"目标目录不存在：{target_dir}")
    if not _is_source_checkout(target_dir):
        raise RuntimeError("该目录不是 DeepSeek Harness 源码检出")
    old_version = _read_dir_version(target_dir)
    got = _download_source_staging(target_dir, log=log)
    staging = got["staging"]
    new_version = got["new_version"]
    run_install, run_build = _auto_update_steps(target_dir, staging)
    try:
        result = _apply_staged_tree(target_dir, staging, old_version, new_version,
                                    run_install, run_build, log=log)
    finally:
        if staging.is_dir():
            shutil.rmtree(staging, ignore_errors=True)
    result.update({"applied": True, "staged": False, "old_version": old_version,
                   "run_install": run_install, "run_build": run_build})
    return result


def apply_pending_update(manifest_path: Path | None = None, log=None) -> dict:
    """阶段二：按清单应用暂存更新（假定 DSH 已关闭）。失败自动回滚。"""
    manifest_path = Path(manifest_path or pending_update_file())
    manifest = _read_json(manifest_path)
    log_file = Path(str(manifest.get("log_file") or update_watcher_log_file()))
    logger = log or (lambda message: _watcher_log(log_file, str(message)))
    if not manifest or manifest.get("schema") != PENDING_SCHEMA:
        raise RuntimeError("没有可应用的更新清单")
    status = manifest.get("status")
    if status != "waiting":
        raise RuntimeError(f"更新状态不是 waiting（当前 {status}）")
    target_dir = Path(str(manifest.get("target") or ""))
    staging = Path(str(manifest.get("staging") or ""))
    old_version = str(manifest.get("old_version") or "")
    new_version = str(manifest.get("new_version") or "")
    if not target_dir.is_dir():
        raise RuntimeError(f"目标目录不存在：{target_dir}")
    if not _is_source_checkout(target_dir):
        raise RuntimeError("目标目录已不是 DeepSeek Harness 源码检出")
    current_version = _read_dir_version(target_dir)
    if old_version and current_version and current_version != old_version:
        raise RuntimeError(
            f"目标版本已变化（清单 {old_version}，实际 {current_version}），放弃本次更新")
    _set_pending_status("applying")
    logger(f"开始应用更新：{old_version or '未知'} → {new_version}")
    try:
        result = _apply_staged_tree(target_dir, staging, old_version, new_version,
                                    bool(manifest.get("run_install")),
                                    bool(manifest.get("run_build")), log=logger)
    except Exception as e:  # noqa: BLE001
        message = f"{type(e).__name__}: {e}"
        # 目录仍被别的进程占用属于「可以稍后重试」的情况：暂存目录还在，
        # 状态退回 waiting（附错误说明），用户关掉占用进程后可点「重试应用」。
        occupied = ("占用" in str(e) or "occupied" in str(e).lower()) and staging.is_dir()
        if occupied:
            _set_pending_status("waiting", error=message)
            logger("目标目录仍被占用：保留暂存更新，关闭占用进程后可重试应用。")
        else:
            _set_pending_status("failed", error=message, finished=_now_stamp())
            logger(f"更新失败：{message}")
        raise
    _set_pending_status("done", finished=_now_stamp(), backup=result.get("backup", ""))
    logger("更新已应用，状态已标记 done。")
    return result


def resume_pending_update(log=print) -> dict:
    """重新启动看护进程，把「等待中/失败但仍保留暂存」的更新再试一次。"""
    manifest = load_pending_update()
    if not manifest:
        raise RuntimeError("没有待应用的更新")
    status = manifest.get("status")
    if status == "applying":
        raise RuntimeError("更新正在应用中，无法重试")
    staging = Path(str(manifest.get("staging") or ""))
    if not staging.is_dir():
        raise RuntimeError("暂存目录已不存在，请重新点击「更新」下载一次")
    pid = int(manifest.get("watcher_pid") or 0)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:  # noqa: BLE001
            pass
    _set_pending_status("waiting", error="", finished="")
    new_pid = _spawn_update_watcher(pending_update_file())
    manifest = load_pending_update()
    manifest["watcher_pid"] = new_pid
    _write_pending_update(manifest)
    log(f"已重新启动看护进程（pid {new_pid}）：关闭 DSH 后会再次尝试应用更新。")
    return {"ok": True, "resumed": True, "watcher_pid": new_pid,
            "old_version": str(manifest.get("old_version") or ""),
            "new_version": str(manifest.get("new_version") or "")}


def _restart_dsh_after_update(restart: dict, port: int, logger) -> bool:
    """按清单里的启动信息重新拉起 DSH（失败只记日志，不抛异常）。"""
    if not isinstance(restart, dict):
        logger("没有可用的重启信息，请手动启动 DSH。")
        return False
    exe = str(restart.get("execPath") or "")
    args = [str(item) for item in (restart.get("args") or [])]
    cwd = restart.get("cwd")
    if not exe or not Path(exe).is_file():
        logger(f"无法自动重启 DSH：可执行文件不存在（{exe or '空'}），请手动启动。")
        return False
    if cwd and not Path(str(cwd)).is_dir():
        logger(f"原工作目录不存在（{cwd}），改为不指定工作目录。")
        cwd = None
    log_path = update_watcher_log_file()
    try:
        log_handle = open(log_path, "a", encoding="utf-8")
        kwargs = {
            "cwd": str(cwd) if cwd else None,
            "stdin": subprocess.DEVNULL,
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "close_fds": True,
        }
        if os.name == "nt":
            kwargs["creationflags"] = (subprocess.DETACHED_PROCESS
                                       | subprocess.CREATE_NEW_PROCESS_GROUP)
        proc = subprocess.Popen([exe, *args], **kwargs)
        log_handle.close()
    except Exception as e:  # noqa: BLE001
        logger(f"自动重启 DSH 失败：{type(e).__name__}: {e}；请手动启动。")
        return False
    logger(f"已重新启动 DSH（pid {proc.pid}）；最多等 60 秒让它监听端口 {port}…")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if _is_port_open(port):
            logger(f"DSH 已就绪：http://127.0.0.1:{port}")
            return True
        time.sleep(2)
    logger("DSH 已启动，但 60 秒内没等到端口监听；请查看日志或手动打开。")
    return True


def watch_and_apply_pending_update(manifest_path: Path | None = None) -> dict:
    """看护进程主流程：等 DSH 关闭 → 应用更新 → 重新启动 DSH。"""
    manifest_path = Path(manifest_path or pending_update_file())
    manifest = _read_json(manifest_path)
    log_file = Path(str(manifest.get("log_file") or update_watcher_log_file()))
    logger = lambda message: _watcher_log(log_file, str(message))  # noqa: E731
    port = int(manifest.get("wait_port") or DEFAULT_WEB_PORT)
    timeout = float(manifest.get("wait_timeout") or _UPDATE_WAIT_TIMEOUT)
    logger(f"看护进程启动（pid {os.getpid()}）：等待端口 {port} 关闭，最多 {timeout / 60:.0f} 分钟。")
    closed = 0
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_port_open(port):
            closed = 0
            time.sleep(2)
            continue
        closed += 1
        if closed >= 2:
            break
        time.sleep(1)
    else:
        logger("等待超时：DSH 一直没关闭，放弃本次更新。")
        _set_pending_status("expired", error="等待 DSH 关闭超时", finished=_now_stamp())
        _cleanup_staging(manifest)
        return {"ok": False, "reason": "timeout"}
    logger("DSH 已关闭，2 秒后开始应用更新…")
    time.sleep(2)
    applied = False
    error = ""
    try:
        apply_pending_update(manifest_path, log=logger)
        applied = True
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"
        logger(f"应用更新失败：{error}")
    restarted = _restart_dsh_after_update(manifest.get("restart") or {}, port, logger)
    return {"ok": applied, "applied": applied, "restarted": restarted, "error": error}


def pending_update_status() -> dict:
    """给插件界面用的待应用更新状态（含日志尾部）；没有清单时 present=False。"""
    manifest = load_pending_update()
    if not manifest:
        return {"present": False}
    log_file = Path(str(manifest.get("log_file") or update_watcher_log_file()))
    staging = Path(str(manifest.get("staging") or "")) if manifest.get("staging") else None
    status = str(manifest.get("status") or "")
    tail = []
    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-40:]
    except Exception:  # noqa: BLE001
        tail = []
    return {
        "present": True,
        "status": status,
        "can_retry": bool(staging is not None and staging.is_dir()
                          and status in ("waiting", "failed")),
        "created": str(manifest.get("created") or ""),
        "updated": str(manifest.get("updated") or ""),
        "finished": str(manifest.get("finished") or ""),
        "target": str(manifest.get("target") or ""),
        "staging": str(manifest.get("staging") or ""),
        "old_version": str(manifest.get("old_version") or ""),
        "new_version": str(manifest.get("new_version") or ""),
        "run_install": bool(manifest.get("run_install")),
        "run_build": bool(manifest.get("run_build")),
        "wait_port": int(manifest.get("wait_port") or DEFAULT_WEB_PORT),
        "restart": bool(manifest.get("restart")),
        "watcher_pid": int(manifest.get("watcher_pid") or 0),
        "backup": str(manifest.get("backup") or ""),
        "error": str(manifest.get("error") or ""),
        "log_file": str(log_file),
        "log_tail": tail,
    }


def cancel_pending_update(log=print) -> dict:
    """取消待应用的更新：杀掉看护进程、删掉暂存目录、状态置 canceled。

    正在应用（applying）时拒绝取消，避免把目录换到一半。
    """
    manifest = load_pending_update()
    if not manifest:
        return {"ok": True, "canceled": False, "message": "没有待应用的更新"}
    status = manifest.get("status")
    if status == "applying":
        raise RuntimeError("更新正在应用中，无法取消")
    if status not in ("waiting", "failed"):
        # done / expired / canceled：没有东西可取消，静默返回
        return {"ok": True, "canceled": False,
                "message": f"更新状态为 {status}，无需取消"}
    pid = int(manifest.get("watcher_pid") or 0)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            log(f"已结束看护进程（pid {pid}）")
        except Exception:  # noqa: BLE001
            pass
    _cleanup_staging(manifest)
    _set_pending_status("canceled", finished=_now_stamp())
    log("已取消待应用的更新并清理暂存目录。")
    return {"ok": True, "canceled": True, "message": "已取消"}


def _decode_restart_spec(raw: str) -> dict:
    """解出 JS 传来的 base64 JSON 重启信息（execPath/args/cwd）；坏数据返回 {}。"""
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(base64.b64decode(text.encode("ascii")).decode("utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(data, dict):
        return {}
    spec = {}
    if isinstance(data.get("execPath"), str):
        spec["execPath"] = data["execPath"]
    if isinstance(data.get("args"), list):
        spec["args"] = [str(item) for item in data["args"]]
    if isinstance(data.get("cwd"), str):
        spec["cwd"] = data["cwd"]
    return spec


def _parse_port_arg(argv: list, default: int = DEFAULT_WEB_PORT) -> int:
    """从 CLI 参数里取 `--port N`（没写就用默认 3080）。"""
    try:
        idx = argv.index("--port")
        return int(argv[idx + 1])
    except Exception:  # noqa: BLE001
        return default


# ---------------------------------------------------------------------------
# npm 全局更新
# ---------------------------------------------------------------------------
def running_node_count() -> int:
    """统计正在运行的 node 进程数。

    更新 npm 全局安装前用它做提示：DSH（或任何 node 进程）占用着原生模块
    （如 sharp-win32-x64-*.node）时，npm 无法替换这些文件，会以
    「EPERM: operation not permitted, unlink ...」失败，并可能留下**损坏的
    安装树**（缺少子模块文件）。所以必须在动手前拦住用户。
    """
    if os.name != "nt":
        try:
            r = subprocess.run(["pgrep", "-c", "node"], capture_output=True,
                               text=True, timeout=10)
            return int((r.stdout or "0").strip() or 0) if r.returncode == 0 else 0
        except Exception:  # noqa: BLE001
            return 0
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq node.exe", "/NH"],
                           capture_output=True, text=True, timeout=15,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            return 0
        return sum(1 for ln in (r.stdout or "").splitlines() if "node.exe" in ln.lower())
    except Exception:  # noqa: BLE001
        return 0


def update_npm_global(pkg_dir: Path, log=print) -> dict:
    """通过 `npm install -g @deepseek-ai/dsh@latest` 更新 npm 全局安装。"""
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise RuntimeError(t("未找到 npm，无法执行全局更新"))
    # DSH 正在运行时原生模块被占用，npm 替换会以 EPERM 失败，并可能留下
    # 损坏的安装树 —— 先拦住，而不是让用户去猜那句 EPERM。
    if _is_port_open(3080):
        raise RuntimeError(t("检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n更新 npm 全局安装会替换正在使用的原生模块，可能失败甚至损坏安装。\n请先关闭 DeepSeek Harness，再执行更新。"))
    _nodes = running_node_count()
    if _nodes:
        log(t("提示：检测到 {p1} 个 node 进程。若它们正在使用 dsh，npm 可能因文件占用而失败；建议先全部关闭。", p1=_nodes))
    old_ver = _read_dir_version(pkg_dir)
    log(t("执行：npm install -g @deepseek-ai/dsh@latest"))
    proc = subprocess.Popen(
        [npm, "install", "-g", "@deepseek-ai/dsh@latest"],
        cwd=str(pkg_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            log(line)
    code = proc.wait()
    if code != 0:
        raise RuntimeError(t("npm install -g 失败（退出码 {code}）", code=code))
    # 重新读版本
    ver = _read_dir_version(pkg_dir)
    append_history({"kind": "npm", "path": str(pkg_dir),
                    "old_version": old_ver, "new_version": ver})
    return {"ok": True, "new_version": ver, "message": t("npm 全局更新完成，版本：{p1}", p1=ver or '?')}


def preferences_file() -> Path:
    """统一的本地信息文件（类似游戏的「玩家偏好」档）。

    结构：{"schema": 1, "settings": {...}, "cache": {...}, "sources": {...}}
    原先分散的 settings.json / cache.json / sources.json 会自动迁移过来
    （只迁移一次，旧文件保留不删，便于回退）。
    """
    return _settings_dir() / "preferences.json"


def _legacy_path(name: str) -> Path:
    return _settings_dir() / name


_EMPTY_PREFS = {"schema": 1, "settings": {}, "cache": {}, "sources": {}}


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def read_preferences() -> dict:
    """读取统一偏好档；不存在时尝试从旧文件迁移一次。"""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _EMPTY_PREFS.items()}
    data = _read_json(preferences_file())
    if data:
        for key in ("settings", "cache", "sources"):
            if isinstance(data.get(key), dict):
                out[key] = data[key]
        # 更新历史是列表，单独处理；漏掉它会导致写入的历史被静默丢弃
        if isinstance(data.get("history"), list):
            out["history"] = data["history"]
        if isinstance(data.get("schema"), int):
            out["schema"] = data["schema"]
        return out

    # 首次运行或旧版升级：把旧文件内容搬进统一档
    legacy = {"settings": _legacy_path("settings.json"),
              "cache": _legacy_path("cache.json"),
              "sources": _legacy_path("sources.json")}
    migrated = False
    for key, path in legacy.items():
        got = _read_json(path)
        if got:
            out[key] = got
            migrated = True
    if migrated:
        write_preferences(out)
    return out


def write_preferences(data: dict) -> bool:
    """原子写入统一偏好档。失败返回 False 而不抛异常。"""
    try:
        target = preferences_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")
        os.replace(tmp, target)
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# 本地偏好设置（持久化到用户配置目录）
# ---------------------------------------------------------------------------
# 注意：gpu_acceleration 目前只是「记录偏好」。DSH 本身没有提供 GPU 加速
# 开关（源码与 profile 配置里均无相关键），所以这个值暂不影响任何行为。
# 等 DSH 真正支持后，再在这里接入实际动作。
SETTINGS_DEFAULTS = {
    "gpu_acceleration": False,
    "language": "auto",      # "auto"=跟随系统；否则 zh-CN / zh-TW / en / ja / ko
    # 注意：load_settings 只接受这里列出的键，新键忘了加就会「写进去读不出来」
    #（深色模式偏好就踩过这个坑：切换时写得进去，重启后读回来被丢掉）
    "dark_mode": False,      # 深色主题（切换后记住，下次启动沿用）
}


def _settings_dir() -> Path:
    """设置文件所在目录。可用 DSH_UPDATER_SETTINGS_DIR 覆盖（测试/便携用）。"""
    custom = os.environ.get("DSH_UPDATER_SETTINGS_DIR")
    if custom:
        return Path(custom)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "dsh-updater"
    return Path.home() / ".config" / "dsh-updater"


def settings_file() -> Path:
    """设置文件完整路径。"""
    return _settings_dir() / "settings.json"


def load_settings() -> dict:
    """读取本地偏好设置。

    文件不存在 / 内容损坏 / 类型不符时一律回退到默认值，绝不抛异常
    —— 启动阶段不能因为一个坏掉的配置文件就崩掉。
    只接受 SETTINGS_DEFAULTS 里已知的键，且类型必须与默认值一致，
    避免把外部写入的垃圾数据带进程序。
    """
    out = dict(SETTINGS_DEFAULTS)
    data = read_preferences().get("settings") or {}
    for key, default in SETTINGS_DEFAULTS.items():
        if key in data and isinstance(data[key], type(default)):
            out[key] = data[key]
    return out


def save_settings(data: dict) -> bool:
    """保存偏好设置（原子写入）。成功返回 True，失败返回 False 而不抛异常。"""
    prefs = read_preferences()
    prefs["settings"] = dict(data)
    return write_preferences(prefs)


# ---------------------------------------------------------------------------
# 检测结果缓存
# ---------------------------------------------------------------------------
def cache_file() -> Path:
    """检测结果缓存文件（与设置文件同目录）。"""
    return _settings_dir() / "cache.json"


def cache_time_text(saved_at: str) -> str:
    """把缓存时间戳格式化为「2026-09-10 18:30」；解析不了则原样截断返回。"""
    if not saved_at:
        return ""
    try:
        return datetime.datetime.fromisoformat(str(saved_at)).strftime("%Y-%m-%d %H:%M")
    except Exception:  # noqa: BLE001
        return str(saved_at)[:16]


def save_detection_cache(result: dict, saved_at: str | None = None) -> str:
    """缓存一次检测结果，返回写入的时间戳；失败返回空串（不抛异常）。

    用 default=str 兜底：检测结果里可能混有 Path 等非 JSON 类型。
    """
    stamp = saved_at or datetime.datetime.now().isoformat(timespec="seconds")
    prefs = read_preferences()
    prefs["cache"] = {"saved_at": stamp, "result": result}
    return stamp if write_preferences(prefs) else ""


def load_detection_cache() -> dict:
    """读取缓存，返回 {"saved_at": str, "result": dict}。

    文件缺失、损坏或结构不对时返回 {}，调用方据此走「无缓存」路径。
    """
    cache = read_preferences().get("cache") or {}
    if not isinstance(cache, dict) or not isinstance(cache.get("result"), dict):
        return {}
    return cache


# ---------------------------------------------------------------------------
# 插件 / 技能的下载来源
# ---------------------------------------------------------------------------
# 插件本质是 npm 包，所以「下载页」就是 npm 包页；技能没有官方市场，
# 只能回溯它自己的 git 来源。两者都拿不到时，退回用户此前记住的来源。
NPM_PACKAGE_URL = "https://www.npmjs.com/package/"


def sources_file() -> Path:
    """「记住的来源」存储文件（与设置同目录）。"""
    return _settings_dir() / "sources.json"


def normalize_git_url(url: str) -> str:
    """把 ssh 形式的 git 地址转成可在浏览器打开的 https 地址。"""
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("git@") and ":" in u:
        host, path = u[4:].split(":", 1)
        u = f"https://{host}/{path}"
    elif u.startswith("ssh://git@"):
        u = "https://" + u[len("ssh://git@"):]
    if u.endswith(".git"):
        u = u[:-4]
    return u


def npm_url_for(name: str) -> str:
    """插件名 → npm 包页地址（保留 scoped 包的 @ 与 /）。"""
    n = (name or "").strip()
    if not n or n.startswith(("（", "(", "—")):
        return ""
    return NPM_PACKAGE_URL + n


def git_remote_url(path: str | Path) -> str:
    """取目录的 git origin 地址并转成 https；没有 git 来源时返回空串。

    注意：空路径必须先挡掉——`Path("").is_dir()` 为 True（等于当前目录），
    否则会误取到本程序自己仓库的 remote。
    """
    if path is None or not str(path).strip():
        return ""
    p = Path(path)
    if not p.is_dir() or not (p / ".git").exists():
        return ""
    try:
        r = subprocess.run(
            ["git", "-C", str(p), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode == 0:
            return normalize_git_url(r.stdout)
    except Exception:  # noqa: BLE001
        pass
    return ""


def load_sources() -> dict:
    """读取「记住的来源」；损坏时返回 {}。"""
    data = read_preferences().get("sources") or {}
    return data if isinstance(data, dict) else {}


def remember_source(key: str, url: str) -> bool:
    """记住某个条目的来源地址，便于以后再次打开或据此检测更新。"""
    if not key or not url:
        return False
    prefs = read_preferences()
    data = prefs.get("sources")
    if not isinstance(data, dict):
        data = {}
    data[key] = {"url": url, "saved_at": datetime.datetime.now().isoformat(timespec="seconds")}
    prefs["sources"] = data
    return write_preferences(prefs)


def source_key(kind: str, name: str) -> str:
    """来源记忆的键：类型 + 名称。"""
    return f"{kind}:{name}".strip()


def source_url_for(item: dict, kind: str = "skill", remembered: dict | None = None) -> str:
    """推导某条插件/技能的下载来源地址。

    优先级：git 来源（技能）→ npm 包页（插件）→ 记住的来源。
    取不到时返回空串，由界面提示用户。
    """
    kind = str(kind or "skill")
    name = str(item.get("name") or "")
    path = item.get("path") or ""

    if kind.startswith("skill"):
        url = git_remote_url(path)
        if url:
            return url
    else:
        url = npm_url_for(name)
        if url:
            return url

    store = remembered if isinstance(remembered, dict) else load_sources()
    entry = store.get(source_key(kind, name))
    if isinstance(entry, dict):
        return str(entry.get("url") or "")
    if isinstance(entry, str):
        return entry
    return ""


# ---------------------------------------------------------------------------
# 自测
# ---------------------------------------------------------------------------
def _selftest() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass
    print("=" * 70)
    print(t("DeepSeek Harness 更新器核心自测"))
    print("=" * 70)

    print(t("\n[1] 检测本机安装"))
    result = detect_all()
    for inst in result["installs"]:
        print(
            t("  • [{p1}] {p2}  version={p3}  状态={p4}", p1=inst['kind_label'], p2=inst['path'], p3=inst['version'] or '?', p4=inst.get('status', '?'))
        )
    if not result["installs"]:
        print(t("  （未自动发现任何安装——源码检出可用 --add 手动指定）"))

    print(t("\n[2] 官方版本"))
    off = result["official"]
    gh = off["github"]
    npm = off["npm"]
    print(f"  GitHub master: {gh.get('version')}  commit={gh.get('commit')}  date={gh.get('date')}  ok={gh['ok']}")
    if gh.get("error"):
        print(f"    github error: {gh['error']}")
    print(f"  npm latest   : {npm.get('version')}  ok={npm['ok']}")
    if npm.get("error"):
        print(f"    npm error: {npm['error']}")

    print(t("\n[3] 版本比较"))
    pairs = [("0.1.0-rc.5", "0.1.3-alpha.1"), ("0.1.2-rc.1", "0.1.2-rc.1"), ("1.0.0", "0.9.9")]
    for a, b in pairs:
        print(f"  {a} vs {b} -> {compare_versions(a, b)}")

    print(t("\n[4] 插件扫描（启用 + 运行时内置，含效率统计）"))
    plugins = scan_plugins(include_core=True)
    enabled = [p for p in plugins["items"] if p["enabled"]]
    core = [p for p in plugins["items"] if not p["enabled"]]
    print(t("  共 {p1} 项：启用 {p2}，运行时内置 {p3}｜用时 {p4:.2f}s｜约 {p5:.1f} 项/秒", p1=len(plugins['items']), p2=len(enabled), p3=len(core), p4=plugins.get('elapsed', 0), p5=plugins.get('speed', 0)))
    for p in enabled[:12]:
        print(f"  ✔ {p['name']}  v{p['version'] or '?'}  {p['size_text']}")
    if len(enabled) > 12:
        print(t("  … 其余 {p1} 项", p1=len(enabled) - 12))
    for e in plugins.get("errors", [])[:5]:
        print(f"  ! {e}")

    print(t("\n[5] 技能扫描（含效率统计）"))
    skills = scan_skills()
    print(t("  技能目录：{p1}", p1=skills.get('root')))
    print(t("  技能数量：{p1}｜用时 {p2:.2f}s｜约 {p3:.1f} 项/秒", p1=len(skills['items']), p2=skills.get('elapsed', 0), p3=skills.get('speed', 0)))
    for s in skills["items"][:8]:
        print(f"  • {s['name']}  v{s['version'] or '-'}  {s['size_text']}")
    if len(skills["items"]) > 8:
        print(t("  … 其余 {p1} 项", p1=len(skills['items']) - 8))
    for e in skills.get("errors", []):
        print(f"  ! {e}")

    print(t("\n[5b] 进度回调演示（skills 前 5 项）"))
    counts = {"n": 0}
    def _cb(rep):
        counts["n"] += 1
        if counts["n"] <= 5:
            print(f"    progress done={rep['done']}/{rep['total']} current={rep.get('current','')}")
    scan_skills(on_progress=_cb)

    print(t("\n[6] zip 可达性（仅探测，不下载）"))
    try:
        req = urllib.request.Request(ZIP_URL, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as resp:
            total = resp.headers.get("Content-Length")
            print(t("  {ZIP_URL}\n  HTTP {p1}  大小约 {p2}", ZIP_URL=ZIP_URL, p1=resp.status, p2=human_size(int(total or 0))))
    except Exception as e:  # noqa: BLE001
        print(t("  探测失败：{e}", e=e))

    print(t("\n[7] 端口占用检测（DSH Web 3080）"))
    print(t("  3080 监听中：{p1}", p1=_is_port_open(3080)))

    print(t("\n自测结束。"))
    return 0


# ---------------------------------------------------------------------------
# JSON CLI —— 供 DSH 插件等外部调用（`python updater_core.py --json <动作>`）
# ---------------------------------------------------------------------------
CLI_ACTIONS = ("detect", "version", "rollback-targets", "rollback-source", "rollback-npm",
               "stage-source", "update-source", "update-status", "cancel-staged",
               "resume-staged")


def _cli_status_code(local: str, ref: str) -> str:
    """把「本地 vs 参照版本」折算成机器可读的状态码，便于前端自己出文案。"""
    if not local or not ref:
        return "unknown"
    try:
        return "update-available" if compare_versions(ref, local) > 0 else "latest"
    except Exception:  # noqa: BLE001
        return "unknown"


def _cli_detect(offline: bool = False, fresh: bool = False) -> dict:
    """检测结果精简版：只保留界面需要的字段，且不带任何翻译文案。"""
    raw = detect_all(fetch_official=not offline, fresh=fresh)
    installs = []
    for inst in raw.get("installs", []):
        local = str(inst.get("version") or "")
        ref = str(inst.get("ref_version") or "")
        update_target = str(inst.get("update_target") or "")
        installs.append({
            "path": str(inst.get("path") or ""),
            "kind": str(inst.get("kind") or ""),
            "version": local,
            "ref_version": ref,
            "ref_kind": str(inst.get("ref_kind") or ""),
            "status": _cli_status_code(local, ref),
            "grade": str(inst.get("grade") or ""),
            # 插件里的「更新」按钮按这个判断：有可更新的目标目录才显示。
            # 源码检出 → 自身目录；运行时 profile → 它 junction 指向的源码检出。
            "updateable": bool(update_target),
            "update_target": update_target,
        })
    official = raw.get("official")
    github = (official or {}).get("github") or {}
    npm = (official or {}).get("npm") or {}
    return {
        "installs": installs,
        "offline": offline,
        "official": None if not official else {
            "github": {"version": str(github.get("version") or "")},
            "npm": {"version": str(npm.get("version") or "")},
        },
        "errors": [str(e) for e in raw.get("errors", [])],
        "summary": {
            "total": len(installs),
            "update_available": sum(1 for i in installs if i["status"] == "update-available"),
        },
    }


def _self_version() -> str:
    """本工具自身版本 —— 以 package.json 为唯一来源（GUI 的 APP_VERSION 有测试锁同步）。"""
    try:
        pkg = Path(__file__).with_name("package.json")
        return str(json.loads(pkg.read_text(encoding="utf-8-sig")).get("version") or "")
    except Exception:  # noqa: BLE001
        return ""


def _cli_version(fresh: bool = False) -> dict:
    """轻量版本信息：本机更新器自身版本 + 官方最新版本（不扫盘）。"""
    return {
        "updater": fetch_self_latest(_self_version(), fresh=fresh),
        "official": fetch_official_versions(fresh=fresh),
    }


def _cli_main(argv: list) -> int:
    """`--json <动作>` 入口：始终输出一行 JSON，退出码 0/1。

    可选 `--offline`：一个网络请求都不发（本地扫描照常），用于界面秒开。
    可选 `--fresh`：忽略官方版本缓存，强制重新联网抓取。
    更新相关动作（供 DSH 插件里「更新」按钮用）：
      stage-source <目录> [重启信息b64] [--port N]  暂存更新并挂后台看护进程
      update-source <目录>                          目标未被占用时直接更新
      update-status                                待应用更新的状态 + 日志尾部
      cancel-staged                                取消待应用的更新
    """
    argv = list(argv)
    offline = "--offline" in argv
    fresh = "--fresh" in argv
    argv = [a for a in argv if a not in ("--offline", "--fresh")]
    action = (argv[0] if argv else "").strip() or "detect"
    envelope = {"ok": False, "action": action, "data": None, "error": None, "log": []}
    lines: list = []
    try:
        if action == "detect":
            envelope["data"] = _cli_detect(offline, fresh=fresh)
        elif action == "version":
            envelope["data"] = _cli_version(fresh=fresh)
        elif action == "rollback-targets":
            envelope["data"] = rollback_targets()
        elif action == "rollback-source":
            if len(argv) < 3:
                raise RuntimeError(t("用法：--json rollback-source <目标目录> <备份目录>"))
            envelope["data"] = rollback_source(Path(argv[1]), Path(argv[2]), log=lines.append)
        elif action == "rollback-npm":
            if len(argv) < 2:
                raise RuntimeError(t("用法：--json rollback-npm <版本号>"))
            envelope["data"] = rollback_npm(argv[1], log=lines.append)
        elif action == "stage-source":
            if len(argv) < 2:
                raise RuntimeError("用法：--json stage-source <目标目录> [重启信息] [--port N]")
            restart = _decode_restart_spec(argv[2] if len(argv) > 2 else "")
            envelope["data"] = stage_source_update(
                Path(argv[1]), restart=restart, port=_parse_port_arg(argv), log=lines.append)
        elif action == "update-source":
            if len(argv) < 2:
                raise RuntimeError("用法：--json update-source <目标目录>")
            envelope["data"] = update_source_immediate(Path(argv[1]), log=lines.append)
        elif action == "update-status":
            envelope["data"] = pending_update_status()
        elif action == "cancel-staged":
            envelope["data"] = cancel_pending_update(log=lines.append)
        elif action == "resume-staged":
            envelope["data"] = resume_pending_update(log=lines.append)
        else:
            raise RuntimeError(t("未知动作：{p1}", p1=action))
        envelope["ok"] = True
    except Exception as e:  # noqa: BLE001
        envelope["error"] = f"{type(e).__name__}: {e}"
    envelope["log"] = lines[-200:]
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False, default=str))
    sys.stdout.write("\n")
    return 0 if envelope["ok"] else 1


if __name__ == "__main__":
    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        sys.exit(_cli_main(sys.argv[idx + 1:]))
    sys.exit(_selftest())
