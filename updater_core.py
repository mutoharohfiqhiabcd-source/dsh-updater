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

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

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
def http_get(url: str, timeout: float = 25.0, binary: bool = False) -> bytes:
    """GET 并返回原始字节；失败抛 RuntimeError。"""
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_json(url: str, timeout: float = 25.0):
    return json.loads(http_get(url, timeout=timeout).decode("utf-8", "replace"))


def http_get_text(url: str, timeout: float = 25.0) -> str:
    return http_get(url, timeout=timeout).decode("utf-8", "replace")


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
# 官方版本
# ---------------------------------------------------------------------------
def fetch_official_versions() -> dict:
    """
    返回形如：
      {
        "github": {"ok": bool, "version": str|None, "commit": str|None,
                    "date": str|None, "error": str|None},
        "npm":    {"ok": bool, "version": str|None, "error": str|None},
      }
    """
    out = {
        "github": {"ok": False, "version": None, "commit": None, "date": None, "error": None},
        "npm": {"ok": False, "version": None, "error": None},
    }
    # GitHub master package.json
    try:
        text = http_get_text(RAW_PACKAGE_URL, timeout=25)
        data = json.loads(text)
        out["github"]["version"] = data.get("version") or _parse_package_version(text)
        out["github"]["ok"] = bool(out["github"]["version"])
    except Exception as e:  # noqa: BLE001
        out["github"]["error"] = str(e)
    # GitHub 最近一次提交（显示更新时间）
    if out["github"]["ok"]:
        try:
            commit = http_get_json(API_COMMIT_URL, timeout=20)
            out["github"]["commit"] = str(commit.get("sha", ""))[:10]
            out["github"]["date"] = (commit.get("commit", {}).get("committer", {}) or {}).get("date")
        except Exception:  # noqa: BLE001
            pass
    # npm registry 发布版
    try:
        data = http_get_json(NPM_LATEST_URL, timeout=25)
        out["npm"]["version"] = data.get("version")
        out["npm"]["ok"] = bool(out["npm"]["version"])
    except Exception as e:  # noqa: BLE001
        out["npm"]["error"] = str(e)
    # 官方近期提交（用于“更新了些什么”提示）
    try:
        commits = http_get_json(
            f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits?per_page=6",
            timeout=20,
        )
        out["github"]["recent"] = []
        for c in commits:
            cm = (c.get("commit") or {}).get("message") or ""
            first = cm.splitlines()[0].strip()[:110] if cm else ""
            date = ((c.get("commit") or {}).get("committer") or {}).get("date") or ""
            out["github"]["recent"].append({"sha": str(c.get("sha", ""))[:8], "msg": first, "date": date[:10]})
    except Exception:  # noqa: BLE001
        out["github"]["recent"] = []
    return out


# ---------------------------------------------------------------------------
# 源码检出检测
# ---------------------------------------------------------------------------
def _is_source_checkout(path: Path) -> bool:
    """判定目录是否为 DSH 源码检出根：package.json name == @deepseek-ai/dsh-root。"""
    pkg = path / "package.json"
    if not pkg.is_file():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
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
        data = json.loads((path / "package.json").read_text(encoding="utf-8", errors="replace"))
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
        data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
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
            cli_version = json.loads(cli_pkg.read_text(encoding="utf-8", errors="replace")).get(
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
            data = json.loads(manifest.read_text(encoding="utf-8", errors="replace"))
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
                        cand.read_text(encoding="utf-8", errors="replace")
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


# ---------------------------------------------------------------------------
# 汇总检测
# ---------------------------------------------------------------------------
def detect_all() -> dict:
    """检测本机所有 DSH 安装并拉取官方版本。返回 dict。"""
    result = {"installs": [], "official": None, "errors": []}
    # 源码检出
    for path, kind, ver in find_source_checkouts():
        result["installs"].append(
            {
                "path": str(path),
                "kind": kind,
                "kind_label": "源码检出",
                "version": ver,
                "updateable": True,  # 源码检出支持整目录替换
            }
        )
    # npm 全局
    for path, kind, ver in find_npm_global():
        result["installs"].append(
            {
                "path": str(path),
                "kind": kind,
                "kind_label": "npm 全局",
                "version": ver,
                "updateable": False,  # npm 全局走 npm i -g，另行处理
            }
        )
    # profile
    for path, kind, ver, cli_ver in find_profiles():
        result["installs"].append(
            {
                "path": str(path),
                "kind": kind,
                "kind_label": f"运行时 profile ({Path(path).name})",
                "version": ver,
                "cli_version": cli_ver,
                "updateable": False,
            }
        )
    # 官方版本
    result["official"] = fetch_official_versions()
    # 状态标注：源码检出对比 GitHub master；npm/profile 对比 npm 发布版
    official_gh = result["official"]["github"]["version"]
    official_npm = result["official"]["npm"]["version"]
    for inst in result["installs"]:
        local = inst["version"] or ""
        if not local:
            inst["status"] = "无法读取版本"
            continue
        if inst["kind"] == INSTALL_KIND_SOURCE:
            ref, ref_ok = official_gh, bool(official_gh)
        else:
            ref, ref_ok = official_npm, bool(official_npm)
        if ref_ok and compare_versions(ref, local) > 0:
            inst["status"] = "可更新"
        elif not ref_ok and not (official_gh and official_npm):
            inst["status"] = "官方版本获取失败"
        else:
            inst["status"] = "已是最新"
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
        return json.loads((path / "package.json").read_text(encoding="utf-8", errors="replace"))
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
    rep.announce("准备就绪，开始枚举插件目录…" if not task_names else "")

    for kind, name, profile_name in task_names:
        if kind == "enabled":
            rep.announce(f"解析启用插件 {name}")
            pkg_dir = _find_package_dir(name, search_roots)
            if pkg_dir is None:
                errors.append(f"无法解析已启用插件 {name}（未在 node_modules 找到）")
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
                }
            )
        else:  # core
            c = Path(name)
            rep.announce(f"统计内置包 @deepseek-ai/{c.name} 大小…")
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
                    "source": "运行时内置",
                }
            )
        rep.step(name)
    rep.finish()
    elapsed = time.monotonic() - start
    # 按启用优先、名称排序，方便阅读
    items.sort(key=lambda x: (not x["enabled"], x["name"].lower()))
    if not items and not errors:
        errors.append(
            "未找到任何插件：请检查 DSH 数据目录是否存在，或本机是否安装了运行时插件包。"
            f"\n当前搜索位置：{DSH_HOME}"
        )
    return {
        "items": items,
        "total_items": len(items),
        "errors": errors,
        "elapsed": elapsed,
        "speed": (len(items) / elapsed) if elapsed > 0 else 0.0,
    }


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
        text = md.read_text(encoding="utf-8", errors="replace")[:4000]
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
            "errors": ["技能目录不存在: " + str(skills_root)],
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
        rep.announce("未发现技能目录…")
    for e in candidates:
        # 目录技能：含 SKILL.md（或本身就是技能目录）
        if e.is_dir():
            name = e.name
            rep.announce(f"统计技能 {name} 文件与大小…")
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
                }
            )
        # 平铺单文件技能（*.md）
        else:
            name = e.stem
            rep.announce(f"读取技能 {name}")
            size = e.stat().st_size if e.is_file() else 0
            items.append(
                {
                    "name": name,
                    "version": "",
                    "size": size,
                    "size_text": human_size(size),
                    "path": str(e),
                    "has_skill_md": False,
                }
            )
        rep.step(e.name)
    rep.finish()
    elapsed = time.monotonic() - start
    return {
        "items": items,
        "root": str(skills_root),
        "errors": errors,
        "elapsed": elapsed,
        "speed": (len(items) / elapsed) if elapsed > 0 else 0.0,
    }


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
        return "计算中…"
    if seconds < 60:
        return f"{seconds:.0f} 秒"
    return f"{int(seconds // 60)} 分 {int(seconds % 60)} 秒"


def _fmt_dl_progress(got: int, total: int, elapsed: float) -> str:
    pct = (got / total * 100) if total else 0.0
    remain = max(total - got, 0) if total else 0
    speed = (got / elapsed) if elapsed > 1.0 else (got / max(elapsed, 1e-9))
    eta = (remain / speed) if speed > 0 and total else 0.0
    return (
        f"已下载 {got / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB"
        f"（{pct:.0f}%）｜剩余 {human_size(remain)}｜速度 {speed / 1024 / 1024:.2f} MB/s"
        f"｜预计还需 {_fmt_eta(eta)}｜已用 {elapsed:.1f} 秒"
    )


def download_file(url: str, dest: Path, log=print, timeout: float = 120.0,
                  progress_cb=None) -> Path:
    """流式下载到 dest，返回 dest。进度行经 log 输出（限流），数值经 progress_cb 回调。"""
    req = urllib.request.Request(url, headers=UA)
    log(f"开始下载：{url}")
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
                        log(f"[下载] {_fmt_dl_progress(got, total, elapsed)}")
                    if progress_cb:
                        progress_cb(min(pct / 100.0, 1.0))
    if progress_cb:
        progress_cb(1.0)
    log(f"下载完成：{dest}（{human_size(got)}，用时 {time.monotonic() - t0:.1f} 秒）")
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
                log(f"解压跳过异常文件 {info.filename}: {e}")
            done_bytes += info.file_size
            done_files += 1
            if total_bytes:
                pct = done_bytes / total_bytes * 100
                if throttle.allow(pct):
                    elapsed = time.monotonic() - t0
                    speed = (done_bytes / elapsed) if elapsed > 1.0 else (done_bytes / max(elapsed, 1e-9))
                    eta = ((total_bytes - done_bytes) / speed) if speed > 0 else 0.0
                    log(
                        f"[解压] 文件 {done_files}/{len(infos)}｜"
                        f"{done_bytes / 1024 / 1024:.1f}/{total_bytes / 1024 / 1024:.1f} MB"
                        f"（{pct:.0f}%）｜速度 {speed / 1024 / 1024:.2f} MB/s"
                        f"｜预计还需 {_fmt_eta(eta)}｜已用 {elapsed:.1f} 秒"
                    )
                if progress_cb:
                    progress_cb(min(pct / 100.0, 1.0))
        if progress_cb:
            progress_cb(1.0)
        log(f"解压完成：{done_files} 个文件，用时 {time.monotonic() - t0:.1f} 秒")


def _find_zip_root(zip_path: Path, extract_dir: Path, log=print, progress_cb=None) -> Path:
    """解压 zip 并返回其中包含 dsh-root package.json 的顶层目录。"""
    log(f"解压中：{zip_path.name}")
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
    raise RuntimeError("下载的压缩包中未找到 DeepSeek Harness 源码根目录")


def _is_port_open(port: int = 3080, host: str = "127.0.0.1") -> bool:
    """检测本地端口是否被监听（DSH Web UI 默认 3080）。"""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def update_source_from_zip(
    target_dir: Path,
    run_pnpm_install: bool = False,
    log=print,
    keep_backup: bool = True,
    backup_root: Path | None = None,
    progress_cb=None,
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
        raise RuntimeError(f"目标目录不存在：{target_dir}")
    if not _is_source_checkout(target_dir):
        raise RuntimeError("该目录不是 DeepSeek Harness 源码检出（package.json name 非 @deepseek-ai/dsh-root）")
    if _is_port_open(3080):
        raise RuntimeError(
            "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n"
            "请先关闭正在运行的 DeepSeek Harness，再执行更新。"
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
    try:
        # ---- 下载并解压 ----
        download_file(ZIP_URL, zip_path, log=log, progress_cb=progress_cb)
        new_root = _find_zip_root(zip_path, extract_dir, log=log, progress_cb=progress_cb)
        if progress_cb:
            progress_cb(1.0)
        new_version = _read_dir_version(new_root)
        log(f"官方源码版本：{new_version}（当前：{old_version or '未知'}）")

        # ---- 备份（整体改名，快） ----
        log(f"备份原目录 → {backup_dir}")
        shutil.move(str(target_dir), str(backup_dir))
        log("备份完成（原目录已改名）")

        try:
            # ---- 先放入新源码：此时目标路径不存在，move 即整体改名到位 ----
            log(f"写入官方源码 → {target_dir}")
            shutil.move(str(new_root), str(target_dir))
            new_root = None  # 已移走
            # ---- 再把 node_modules/.git 从备份目录移回新目录（加速后续 install） ----
            for k in _KEEP_DIRS:
                src = backup_dir / k
                if src.exists():
                    dst = target_dir / k
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    log(f"保留 {k}（移回新目录）…")
                    shutil.move(str(src), str(dst))
            log("新源码就位。")
        except Exception as e:  # noqa: BLE001
            # 回滚
            log(f"替换失败，回滚中：{e}")
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            shutil.move(str(backup_dir), str(target_dir))
            raise RuntimeError(f"更新失败，已回滚：{e}") from e

        # ---- 可选 pnpm install ----
        if run_pnpm_install:
            log("执行 pnpm install（新目录中安装依赖）…")
            pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
            if not pnpm:
                raise RuntimeError("未找到 pnpm。已替换源码，但未安装依赖；请手动运行 pnpm install")
            proc = subprocess.Popen(
                [pnpm, "install"],
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
                raise RuntimeError(f"pnpm install 失败（退出码 {code}）。源码已替换，请手动排查依赖。")

        msg = f"更新完成：{old_version or '旧版本'} → {new_version}"
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
# npm 全局更新
# ---------------------------------------------------------------------------
def update_npm_global(pkg_dir: Path, log=print) -> dict:
    """通过 `npm install -g @deepseek-ai/dsh@latest` 更新 npm 全局安装。"""
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise RuntimeError("未找到 npm，无法执行全局更新")
    log("执行：npm install -g @deepseek-ai/dsh@latest")
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
        raise RuntimeError(f"npm install -g 失败（退出码 {code}）")
    # 重新读版本
    ver = _read_dir_version(pkg_dir)
    return {"ok": True, "new_version": ver, "message": f"npm 全局更新完成，版本：{ver or '?'}"}


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
    print("DeepSeek Harness 更新器核心自测")
    print("=" * 70)

    print("\n[1] 检测本机安装")
    result = detect_all()
    for inst in result["installs"]:
        print(
            f"  • [{inst['kind_label']}] {inst['path']}  "
            f"version={inst['version'] or '?'}  状态={inst.get('status', '?')}"
        )
    if not result["installs"]:
        print("  （未自动发现任何安装——源码检出可用 --add 手动指定）")

    print("\n[2] 官方版本")
    off = result["official"]
    gh = off["github"]
    npm = off["npm"]
    print(f"  GitHub master: {gh.get('version')}  commit={gh.get('commit')}  date={gh.get('date')}  ok={gh['ok']}")
    if gh.get("error"):
        print(f"    github error: {gh['error']}")
    print(f"  npm latest   : {npm.get('version')}  ok={npm['ok']}")
    if npm.get("error"):
        print(f"    npm error: {npm['error']}")

    print("\n[3] 版本比较")
    pairs = [("0.1.0-rc.5", "0.1.3-alpha.1"), ("0.1.2-rc.1", "0.1.2-rc.1"), ("1.0.0", "0.9.9")]
    for a, b in pairs:
        print(f"  {a} vs {b} -> {compare_versions(a, b)}")

    print("\n[4] 插件扫描（启用 + 运行时内置，含效率统计）")
    plugins = scan_plugins(include_core=True)
    enabled = [p for p in plugins["items"] if p["enabled"]]
    core = [p for p in plugins["items"] if not p["enabled"]]
    print(f"  共 {len(plugins['items'])} 项：启用 {len(enabled)}，运行时内置 {len(core)}"
          f"｜用时 {plugins.get('elapsed', 0):.2f}s｜"
          f"约 {plugins.get('speed', 0):.1f} 项/秒")
    for p in enabled[:12]:
        print(f"  ✔ {p['name']}  v{p['version'] or '?'}  {p['size_text']}")
    if len(enabled) > 12:
        print(f"  … 其余 {len(enabled) - 12} 项")
    for e in plugins.get("errors", [])[:5]:
        print(f"  ! {e}")

    print("\n[5] 技能扫描（含效率统计）")
    skills = scan_skills()
    print(f"  技能目录：{skills.get('root')}")
    print(f"  技能数量：{len(skills['items'])}"
          f"｜用时 {skills.get('elapsed', 0):.2f}s｜"
          f"约 {skills.get('speed', 0):.1f} 项/秒")
    for s in skills["items"][:8]:
        print(f"  • {s['name']}  v{s['version'] or '-'}  {s['size_text']}")
    if len(skills["items"]) > 8:
        print(f"  … 其余 {len(skills['items']) - 8} 项")
    for e in skills.get("errors", []):
        print(f"  ! {e}")

    print("\n[5b] 进度回调演示（skills 前 5 项）")
    counts = {"n": 0}
    def _cb(rep):
        counts["n"] += 1
        if counts["n"] <= 5:
            print(f"    progress done={rep['done']}/{rep['total']} current={rep.get('current','')}")
    scan_skills(on_progress=_cb)

    print("\n[6] zip 可达性（仅探测，不下载）")
    try:
        req = urllib.request.Request(ZIP_URL, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as resp:
            total = resp.headers.get("Content-Length")
            print(f"  {ZIP_URL}\n  HTTP {resp.status}  大小约 {human_size(int(total or 0))}")
    except Exception as e:  # noqa: BLE001
        print(f"  探测失败：{e}")

    print("\n[7] 端口占用检测（DSH Web 3080）")
    print(f"  3080 监听中：{_is_port_open(3080)}")

    print("\n自测结束。")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest())
