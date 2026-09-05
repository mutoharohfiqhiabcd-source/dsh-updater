# -*- coding: utf-8 -*-
"""
updater_gui.pyw —— DeepSeek Harness 自动检测与更新器（Tkinter 图形界面）
========================================================================
运行：双击本文件（.pyw，用 pythonw 无控制台启动），或：
      python updater_gui.pyw
冒烟测试（构建窗口后自动关闭）：python updater_gui.pyw --smoke
"""
from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

import updater_core as core

APP_TITLE = "DeepSeek Harness 自动检测与更新器"


def resource_path(name: str) -> str:
    """定位资源文件：开发时返回脚本同目录，PyInstaller 打包后返回内置资源（_MEIPASS）。"""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return str(Path(base) / name)
    return str(Path(__file__).resolve().parent / name)


def app_dir() -> Path:
    """返回“程序所在目录”：打包后为 exe 所在目录，开发时为脚本目录（用于导出 CSV 等）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 主题色板（美工）
# ---------------------------------------------------------------------------
CLR = {
    "bg": "#f2f5f9",
    "panel": "#ffffff",
    "panel_line": "#d7dee8",
    "accent": "#0b57d0",
    "accent_hover": "#0842a0",
    "accent_fg": "#ffffff",
    "text": "#1c2733",
    "text_dim": "#5a6a7a",
    "ok": "#1a7f37",
    "warn": "#b35900",
    "err": "#c5221f",
    "heading_bg": "#dfe8f6",
    "heading_fg": "#12315f",
    "log_bg": "#0f1722",
    "log_fg": "#d7e1ee",
}

# 各安装类型在此程序浮窗中的说明
KIND_INFO = {
    core.INSTALL_KIND_SOURCE: {
        "badge": "源码检出",
        "title": "源码检出 · Source Checkout",
        "what": "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。"
                "一般来自 git clone 或 GitHub 源码 zip 解压，包含 apps/cli 等全部源码。",
        "role": "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），"
                "内置 dsh-* 插件包大多源自这里的 packages 工程。",
        "how": "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换"
               "（node_modules/.git 会保留并移回，可勾选随后 pnpm install）。",
        "ref": "GitHub master",
    },
    core.INSTALL_KIND_NPM: {
        "badge": "npm 全局",
        "title": "npm 全局安装 · @deepseek-ai/dsh",
        "what": "通过 npm 全局安装的 dsh 命令行工具包（node_modules/@deepseek-ai/dsh）。",
        "role": "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、"
                "加载当前安装的运行时插件。",
        "how": "对比 npm registry 的 latest 发布版；更新方式：npm install -g @deepseek-ai/dsh@latest。",
        "ref": "npm latest",
    },
    core.INSTALL_KIND_PROFILE: {
        "badge": "运行时 profile",
        "title": "运行时 Profile · 插件装载实例",
        "what": "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理"
                "该 profile 启用的插件清单（package.json 的 dsh.profile.bundles）与本地配置。",
        "role": "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”"
                "层面的宿主目录，随 dsh CLI / 源码安装自动生成。",
        "how": "本身不单独更新：升级其来源（npm 全局 dsh 或源码检出）后，重启 DSH 即用新版。",
        "ref": "npm latest",
    },
}

# Treeview 状态/性质 tag → 颜色（可更新/最新/候选/预发布/不稳定）
STATUS_TAG = {
    "update": "#b35900",
    "ok": "#1a7f37",
    "err": "#c5221f",
    "dim": "#5a6a7a",
    "candidate": "#8a5a00",      # 候选版 rc（琥珀偏深）
    "prerelease": "#7b1fa2",     # 预发布 alpha（紫）
    "unstable": "#c2185b",       # 不稳定版（洋红，特殊醒目色）
}

# ---------------------------------------------------------------------------
# 后台任务辅助：把耗时操作放进线程，日志经 queue 送回主线程
# ---------------------------------------------------------------------------
class Worker:
    def __init__(self, on_log, on_finish, on_progress=None):
        self.q: queue.Queue = queue.Queue()
        self.on_log = on_log
        self.on_finish = on_finish
        self.on_progress = on_progress
        self._thread: threading.Thread | None = None

    def start(self, fn, *args):
        def runner():
            try:
                result = fn(*args)
                self.q.put(("finish", result, None))
            except Exception as e:  # noqa: BLE001
                self.q.put(("finish", None, e))
            finally:
                self.q.put(("done", None, None))

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()

    # ---- 供工作线程调用的线程安全发射器（把消息送回主线程 queue） ----
    def emit_log(self, msg: str):
        self.q.put(("log", str(msg), None))

    def emit_progress(self, value: float):
        self.q.put(("progress", float(value), None))

    def pump(self):
        """由 root.after 周期调用。"""
        got_finish = False
        try:
            while True:
                kind, payload, err = self.q.get_nowait()
                if kind == "log":
                    self.on_log(payload)
                elif kind == "progress":
                    if self.on_progress:
                        self.on_progress(payload)
                elif kind == "finish":
                    got_finish = True
                    self.on_finish(payload, err)
                elif kind == "done":
                    pass
        except queue.Empty:
            pass
        return got_finish


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------
class UpdaterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("1020x660")
        root.minsize(860, 560)

        font = ("Microsoft YaHei UI", 10)
        import tkinter.font as tkfont
        default = tkfont.nametofont("TkDefaultFont")
        default.configure(family="Microsoft YaHei UI", size=10)
        for name in ("TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(family="Microsoft YaHei UI")
            except Exception:  # noqa: BLE001
                pass

        self.install_rows: list = []      # Treeview iid -> install dict
        self.official = None
        self.busy = False
        self._after_id = None

        # 应用图标（开发时与脚本同目录；PyInstaller 打包后内置在 exe 资源中）
        self._icon_path = str(resource_path("dsh_updater.ico"))
        if Path(self._icon_path).is_file():
            try:
                root.iconbitmap(self._icon_path)
            except Exception:  # noqa: BLE001
                pass

        self._setup_style()
        self._build_ui()
        self._log(f"{APP_TITLE} 已启动。\nDSH 数据目录：{core.DSH_HOME}")
        self._log("正在自动检测本机安装与官方版本…")
        self.refresh_all()

    # ---------------- UI 构建 ----------------
    def _apply_icon(self, win: tk.Toplevel):
        """给子窗口套用应用图标。"""
        try:
            if hasattr(self, "_icon_path") and Path(self._icon_path).is_file():
                win.iconbitmap(self._icon_path)
        except Exception:  # noqa: BLE001
            pass

    def _setup_style(self):
        """统一美工：配色 / 字体 / 组件样式。"""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except Exception:  # noqa: BLE001
            pass
        s = self.style
        s.configure(".", background=CLR["bg"], foreground=CLR["text"],
                    font=("Microsoft YaHei UI", 10))
        s.configure("TFrame", background=CLR["bg"])
        s.configure("Panel.TFrame", background=CLR["panel"])
        s.configure("TLabelframe", background=CLR["bg"], bordercolor=CLR["panel_line"],
                    relief="flat", padding=6)
        s.configure("TLabelframe.Label", background=CLR["bg"], foreground=CLR["heading_fg"],
                    font=("Microsoft YaHei UI", 10, "bold"))
        s.configure("TLabel", background=CLR["bg"])
        s.configure("Panel.TLabel", background=CLR["panel"])
        s.configure("Heading.TLabel", background=CLR["panel"], foreground=CLR["text"],
                    font=("Microsoft YaHei UI", 16, "bold"))
        s.configure("Dim.TLabel", background=CLR["panel"], foreground=CLR["text_dim"])

        # 按钮
        s.configure("TButton", background=CLR["panel"], foreground=CLR["text"],
                    bordercolor=CLR["panel_line"], focusthickness=0, padding=(14, 6))
        s.map("TButton", background=[("active", "#e6edf7"), ("pressed", "#d5e1f2")])
        s.configure("Accent.TButton", background=CLR["accent"], foreground=CLR["accent_fg"],
                    bordercolor=CLR["accent"], padding=(16, 7))
        s.map("Accent.TButton",
              background=[("active", CLR["accent_hover"]), ("pressed", CLR["accent_hover"]),
                          ("disabled", "#9db8e2")],
              foreground=[("disabled", "#eef2f9")])
        s.configure("Warn.TButton", background="#e8710a", foreground="#ffffff",
                    bordercolor="#e8710a", padding=(16, 7))
        s.map("Warn.TButton", background=[("active", "#cf6407"), ("disabled", "#f0b98a")],
              foreground=[("disabled", "#ffffff")])

        # 进度条
        s.configure("TProgressbar", background=CLR["accent"], troughcolor="#dfe6f0",
                    bordercolor=CLR["bg"], lightcolor=CLR["accent"], darkcolor=CLR["accent"])

        # Treeview
        s.configure("Treeview", background="#ffffff", fieldbackground="#ffffff",
                    foreground=CLR["text"], rowheight=30, bordercolor=CLR["panel_line"])
        s.map("Treeview", background=[("selected", "#cfe0f7")],
              foreground=[("selected", CLR["text"])])
        s.configure("Treeview.Heading", background=CLR["heading_bg"],
                    foreground=CLR["heading_fg"], padding=(8, 6),
                    font=("Microsoft YaHei UI", 10, "bold"))
        s.map("Treeview.Heading", background=[("active", "#cddbf0")])

        # 滚动条
        s.configure("Vertical.TScrollbar", background="#b9c6d6", troughcolor=CLR["bg"],
                    bordercolor=CLR["bg"], arrowcolor="#5a6a7a")
        s.configure("Horizontal.TScrollbar", background="#b9c6d6", troughcolor=CLR["bg"],
                    bordercolor=CLR["bg"], arrowcolor="#5a6a7a")
        s.configure("TCheckbutton", background=CLR["panel"], foreground=CLR["text"])

        # 状态 tag 颜色（Treeview 行内使用）
        for tag, col in STATUS_TAG.items():
            self.tree_tags = getattr(self, "tree_tags", {})
            self.tree_tags[tag] = col

    def _build_ui(self):
        self.root.configure(bg=CLR["bg"])

        # ── 顶部横幅：标题与官方版本条 ──
        top = ttk.Frame(self.root, style="Panel.TFrame")
        top.pack(fill="x", padx=10, pady=(10, 4))
        # 左侧标题区
        titlebox = ttk.Frame(top, style="Panel.TFrame")
        titlebox.pack(side="left", padx=12, pady=8)
        ttk.Label(titlebox, text="DeepSeek Harness 更新器",
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(titlebox, text="自动检测本机安装 · 对比官方版本 · 插件/技能扫描 · 一键更新",
                  style="Dim.TLabel").pack(anchor="w", pady=(2, 0))
        # 右侧版本条（白底卡片）
        verbox = ttk.Frame(top, style="Panel.TFrame")
        verbox.pack(side="right", padx=12, pady=8)
        self.lbl_github = ttk.Label(verbox, text="🌐 官方 GitHub master：检测中…",
                                    foreground=CLR["accent"], background=CLR["panel"])
        self.lbl_github.pack(anchor="e")
        self.lbl_npm = ttk.Label(verbox, text="📦 npm 发布版：检测中…",
                                 foreground="#7a4a0b", background=CLR["panel"])
        self.lbl_npm.pack(anchor="e", pady=(2, 0))

        # ── 中部：安装列表 ──
        mid = ttk.LabelFrame(self.root, text="本机检测到的 DeepSeek Harness 安装（悬停“类型/状态/性质”列查看说明）")
        mid.pack(fill="both", expand=False, padx=10, pady=6)
        cols = ("kind", "path", "version", "nature", "ref", "status")
        heads = {"kind": "类型", "path": "位置", "version": "当前版本",
                 "nature": "版本性质", "ref": "官方参考版本", "status": "状态"}
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=6)
        for c in cols:
            self.tree.heading(c, text=heads[c])
        widths = {"kind": 112, "path": 372, "version": 100, "nature": 92, "ref": 112, "status": 96}
        for c in cols:
            self.tree.column(c, width=widths[c], anchor="w", stretch=(c == "path"))
        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        vsb.pack(side="right", fill="y", padx=(0, 6), pady=6)
        # 状态/性质 tag（含整行背景色，让“不稳定版”特别醒目）
        tag_bg = {
            "update": "#fff3e0", "ok": "#e8f5e9", "err": "#fdecea",
            "dim": "#f4f6f9", "candidate": "#fff8e1", "prerelease": "#f3e5f5",
            "unstable": "#fce4ec",
        }
        for tag, col in STATUS_TAG.items():
            self.tree.tag_configure(tag, foreground=col, background=tag_bg.get(tag, "#ffffff"))
        self.tree.bind("<Double-1>", self._on_row_double)
        # hover 浮窗（“类型”列 / 状态列 / 性质列均有说明）
        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tree.bind("<Leave>", lambda e: self._hide_tip())
        self._tip_win = None

        # ── 操作按钮区 ──
        btns = ttk.Frame(self.root)
        btns.pack(fill="x", padx=10, pady=(6, 2))
        self.btn_update = ttk.Button(btns, text="⬇ 更新所选安装", style="Accent.TButton",
                                     command=self.update_selected)
        self.btn_update.pack(side="left", padx=(0, 8))
        self.btn_plugins = ttk.Button(btns, text="🧩 插件检测", command=self.open_plugins)
        self.btn_plugins.pack(side="left", padx=(0, 8))
        self.btn_skills = ttk.Button(btns, text="📚 技能检测", command=self.open_skills)
        self.btn_skills.pack(side="left", padx=(0, 8))
        self.btn_refresh = ttk.Button(btns, text="🔄 重新检测", command=self.refresh_all)
        self.btn_refresh.pack(side="left")
        self.btn_settings = ttk.Button(btns, text="⚙ 数据目录", command=self.show_settings)
        self.btn_settings.pack(side="right", padx=(8, 0))
        self.btn_export = ttk.Button(btns, text="💾 导出 CSV", command=self.export_csv)
        self.btn_export.pack(side="right")

        # ── 当前操作进度横幅（扫描/下载/更新通用） ──
        progframe = ttk.LabelFrame(self.root, text="当前任务")
        progframe.pack(fill="x", padx=10, pady=4)
        inner = ttk.Frame(progframe)
        inner.pack(fill="x", padx=6, pady=6)
        self.prog = ttk.Progressbar(inner, mode="determinate", maximum=1000)
        self.prog.pack(side="left", fill="x", expand=True)
        self.lbl_progress = ttk.Label(inner, text="等待任务…", width=60, anchor="e")
        self.lbl_progress.pack(side="right", padx=(10, 0))

        # ── 日志区 ──
        logframe = ttk.LabelFrame(self.root, text="日志 / 进度")
        logframe.pack(fill="both", expand=True, padx=10, pady=6)
        self.txt = tk.Text(logframe, height=9, wrap="word", state="disabled",
                           font=("Consolas", 9), background=CLR["log_bg"],
                           foreground=CLR["log_fg"], borderwidth=0, padx=8, pady=6)
        logvsb = ttk.Scrollbar(logframe, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=logvsb.set)
        self.txt.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        logvsb.pack(side="right", fill="y", padx=(0, 6), pady=6)

        # 底部状态栏
        self.status = ttk.Label(self.root, text="就绪", relief="flat", anchor="w",
                                background="#e4ebf5", padding=(10, 5))
        self.status.pack(fill="x", side="bottom")

    # ---------------- 日志 ----------------
    def _log(self, msg: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", str(msg) + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _set_status(self, text: str):
        self.status.configure(text=text)

    # ---------------- 进度横幅 ----------------
    def _prog_reset(self, text: str = ""):
        self.prog.configure(value=0)
        self.lbl_progress.configure(text=text or "准备中…")

    def _prog_set(self, value: float, text: str | None = None):
        """value 0.0~1.0；text 留空则自动显示百分比。"""
        self.prog.configure(value=int(max(0.0, min(value, 1.0)) * 1000))
        if text is None:
            text = f"进度：{value * 100:.1f}%"
        self.lbl_progress.configure(text=text)

    def _prog_done(self, text: str = "完成"):
        self.prog.configure(value=1000)
        self.lbl_progress.configure(text=text)

    # ---------------- 按钮状态 ----------------
    def _set_busy(self, busy: bool):
        self.busy = busy
        state = "disabled" if busy else "normal"
        for b in (self.btn_refresh, self.btn_update, self.btn_plugins, self.btn_skills,
                  self.btn_export):
            b.configure(state=state)

    # ---------------- 重新检测 ----------------
    def refresh_all(self):
        if self.busy:
            return
        self._set_busy(True)
        self._set_status("正在检测本机安装与官方版本…")
        self._log("\n── 开始检测 ──")
        worker = Worker(self._log, self._on_detect_done)
        self._worker = worker
        worker.start(core.detect_all)
        self._poll(worker)

    def _poll(self, worker: Worker):
        try:
            if worker.pump():
                return
            self._after_id = self.root.after(120, lambda: self._poll(worker))
        except tk.TclError:
            return  # 窗口已关闭

    def _on_detect_done(self, result, err):
        self._set_busy(False)
        if err is not None:
            messagebox.showerror(APP_TITLE, f"检测失败：\n{err}")
            self._set_status("检测失败")
            return
        self.official = result["official"]
        gh = result["official"]["github"]
        npm = result["official"]["npm"]
        gh_txt = gh.get("version") or "获取失败"
        npm_txt = npm.get("version") or "获取失败"
        if gh.get("version"):
            gh_txt += f"（{gh.get('date', '')[:10]}）"
        gh_assess = gh.get("assess") or {}
        npm_assess = npm.get("assess") or {}
        if gh_assess.get("grade") in ("prerelease", "unstable"):
            gh_txt += f"〔{gh_assess.get('grade_label', '')}〕"
        if npm_assess.get("grade") in ("prerelease", "unstable", "candidate"):
            npm_txt += f"〔{npm_assess.get('grade_label', '')}〕"
        self.lbl_github.configure(text=f"🌐 官方 GitHub master：{gh_txt}")
        self.lbl_npm.configure(text=f"📦 npm 发布版：{npm_txt}")

        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.install_rows = []
        for inst in result["installs"]:
            if inst["kind"] == core.INSTALL_KIND_SOURCE:
                ref = gh.get("version") or ""
            else:
                ref = npm.get("version") or ""
            nature = inst.get("grade_label", "—")
            row = (inst["kind_label"], inst["path"], inst["version"] or "—",
                   nature, ref or "—", inst.get("status", "—"))
            tag = self._row_tag(inst)
            iid = self.tree.insert("", "end", values=row, tags=(tag,))
            self.install_rows.append({"iid": iid, "data": inst})
            self._log(
                f"[{inst['kind_label']}] {inst['path']}\n"
                f"    当前 {inst['version'] or '—'} / 性质 {nature} / 官方 {ref or '—'} / {inst.get('status', '—')}"
            )
            assess = inst.get("assess") or {}
            if assess.get("reason") and assess.get("grade") != "stable":
                self._log(f"    └ 稳定性判定：{assess['reason']}")
        # —— 自检结果 ——
        sc = result.get("selfcheck") or {}
        if sc.get("duplicates"):
            self._log(f"🛡 自检：发现并合并 {sc['duplicates']} 处重复安装（同一真实路径）")
            for n in sc.get("notes", []):
                self._log(f"    └ {n}")
        self._set_status(f"检测完成：发现 {len(result['installs'])} 处安装"
                         + (f"（自检合并重复 {sc.get('duplicates', 0)} 处）" if sc.get("duplicates") else ""))
        if not result["installs"]:
            self._log("未自动发现安装，可使用界面按钮或自行检查路径。")

    @staticmethod
    def _row_tag(inst: dict) -> str:
        """行 tag 优先级：不稳定/预发布最醒目，其次可更新状态。"""
        grade = inst.get("grade", "")
        if grade == "unstable":
            return "unstable"
        if grade == "prerelease":
            return "prerelease"
        status = inst.get("status", "")
        if "可更新" in status:
            return "update"
        if grade == "candidate":
            return "candidate"
        if status == "已是最新":
            return "ok"
        if status and "失败" in status:
            return "err"
        return "dim"

    @staticmethod
    def _status_tag(status: str) -> str:
        if "可更新" in status:
            return "update"
        if status == "已是最新":
            return "ok"
        if status and "失败" in status:
            return "err"
        return "dim"

    # ---------------- 更新 ----------------
    def _selected_install(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "请先在列表中选中一行安装。")
            return None
        for r in self.install_rows:
            if r["iid"] == sel[0]:
                return r["data"]
        return None

    def update_selected(self):
        inst = self._selected_install()
        if inst is None:
            return
        if self.busy:
            return
        if inst["kind"] == core.INSTALL_KIND_NPM:
            self._confirm_npm_update(inst)
        elif inst["kind"] == core.INSTALL_KIND_SOURCE:
            self._confirm_source_update(inst)
        else:
            messagebox.showinfo(
                APP_TITLE,
                "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n"
                "请更新其对应的源码检出或 npm 全局安装。",
            )

    def _confirm_npm_update(self, inst):
        if not messagebox.askyesno(
            APP_TITLE,
            f"将更新 npm 全局安装：\n{inst['path']}\n"
            f"当前版本：{inst['version'] or '—'}\n"
            f"将执行：npm install -g @deepseek-ai/dsh@latest\n\n"
            f"是否继续？",
        ):
            return
        self._set_busy(True)
        self._set_status("正在通过 npm 更新全局安装…")
        self._prog_reset("npm install -g @deepseek-ai/dsh@latest")
        worker = Worker(self._log, self._on_npm_update_done)
        self._worker = worker
        worker.start(
            lambda: core.update_npm_global(Path(inst["path"]), log=worker.emit_log)
        )
        self._poll(worker)

    def _on_npm_update_done(self, result, err):
        self._set_busy(False)
        if err is not None:
            messagebox.showerror(APP_TITLE, f"npm 更新失败：\n{err}")
            self._set_status("npm 更新失败")
            self._prog_reset("npm 更新失败")
            return
        messagebox.showinfo(APP_TITLE, result.get("message", "npm 更新完成"))
        self._set_status("npm 更新完成")
        self._prog_done("npm 更新完成")
        self.refresh_all()

    def _confirm_source_update(self, inst):
        # 询问是否运行 pnpm install
        ask = tk.Toplevel(self.root)
        ask.title("更新源码检出")
        self._apply_icon(ask)
        ask.transient(self.root)
        ask.grab_set()
        ask.resizable(False, False)
        frm = ttk.Frame(ask, padding=14)
        frm.pack()
        ttk.Label(
            frm,
            text="将更新源码检出：",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(frm, text=inst["path"], wraplength=560).grid(row=1, column=0, sticky="w")
        cur = inst["version"] or "—"
        ref = (self.official["github"]["version"] if self.official else None) or "—"
        ttk.Label(frm, text=f"当前版本：{cur}    官方最新：{ref}").grid(row=2, column=0, sticky="w", pady=4)
        # 目标版本稳定性/适配性提示
        gh = (self.official or {}).get("github", {}) or {}
        gh_assess = gh.get("assess") or {}
        if gh_assess.get("grade"):
            notes = []
            gl = gh_assess.get("grade_label", "")
            if gh_assess.get("grade") == "stable":
                notes.append(f"官方最新 {ref} 为【{gl}】。")
            elif gh_assess.get("grade") == "candidate":
                notes.append(f"官方最新 {ref} 为【{gl}】，发布候选版。")
            elif gh_assess.get("grade") == "prerelease":
                notes.append(f"⚠ 官方最新 {ref} 为【{gl}】（预发布），可能存在兼容性变化，请按需更新。")
            else:
                notes.append(f"🛑 官方最新 {ref} 官网信息不足，判定为【{gl}】，请谨慎更新。")
            if gh_assess.get("node_reason"):
                notes.append(f"适配性：{gh_assess['node_reason']}")
            if notes:
                ttk.Label(
                    frm, text="\n".join(notes), wraplength=560, foreground="#b3261e",
                ).grid(row=3, column=0, sticky="w", pady=(0, 6))
        ttk.Label(
            frm,
            text="流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n"
                 "（node_modules / .git 会自动移回新目录，以加快依赖安装）\n"
                 "更新期间请勿关闭本程序；若 DSH Web (3080) 正在运行将中止更新。",
            foreground="#a00", wraplength=560,
        ).grid(row=4, column=0, sticky="w", pady=6)
        self.var_pnpm = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frm, text="替换后自动运行 pnpm install（推荐，用于同步依赖）",
            variable=self.var_pnpm,
        ).grid(row=5, column=0, sticky="w", pady=4)
        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="开始更新", command=lambda: self._run_source_update(inst, ask)).pack(side="left", padx=4)
        ttk.Button(btns, text="取消", command=ask.destroy).pack(side="left")

    def _run_source_update(self, inst, ask):
        ask.destroy()
        if self.busy:
            return
        self._set_busy(True)
        self._set_status("正在下载并替换源码…")
        self._prog_reset("准备下载官方源码…")
        worker = Worker(self._log, self._on_source_update_done, on_progress=self._on_update_progress)
        self._worker = worker
        run_pnpm = self.var_pnpm.get()
        worker.start(
            lambda: core.update_source_from_zip(
                Path(inst["path"]),
                run_pnpm,
                log=worker.emit_log,
                progress_cb=worker.emit_progress,
            )
        )
        self._poll(worker)

    def _on_update_progress(self, value: float):
        """主窗口进度横幅：value 0.0~1.0（下载/解压阶段）。"""
        try:
            self._prog_set(value, text=f"更新进度：{value * 100:.1f}%")
        except tk.TclError:
            pass

    def _on_source_update_done(self, result, err):
        self._set_busy(False)
        if err is not None:
            messagebox.showerror(APP_TITLE, f"更新失败：\n{err}")
            self._set_status("更新失败")
            self._prog_reset("更新失败")
            return
        msg = result.get("message", "更新完成")
        if result.get("backup"):
            msg += f"\n\n原目录备份于：\n{result['backup']}"
        messagebox.showinfo(APP_TITLE, msg)
        self._set_status("更新完成")
        self._prog_done("更新完成")
        self.refresh_all()

    # ---------------- 插件 / 技能窗口 ----------------
    def open_plugins(self):
        self._open_inventory_window(
            name="插件",
            title="🧩 DeepSeek Harness 插件检测",
            reopen=self.open_plugins,
            columns=(("name", "名称"), ("version", "版本"), ("size", "大小"),
                     ("enabled", "启用"), ("source", "来源")),
            widths=(330, 110, 96, 58, 150),
            scan_fn=core.scan_plugins,
            scan_kwargs={},
            row_of=lambda it: (it["name"], it["version"] or "—", it["size_text"],
                               "✔ 启用" if it["enabled"] else "内置", it["source"]),
            detail_of=lambda it: it["path"],
        )

    def open_skills(self):
        self._open_inventory_window(
            name="技能",
            title="📚 DeepSeek Harness 技能检测",
            reopen=self.open_skills,
            columns=(("name", "名称"), ("version", "版本"), ("size", "大小")),
            widths=(330, 120, 120),
            scan_fn=core.scan_skills,
            scan_kwargs={},
            row_of=lambda it: (it["name"], it["version"] or "—", it["size_text"]),
            detail_of=lambda it: it["path"],
        )

    def _open_inventory_window(self, name, title, reopen, columns, widths,
                               scan_fn, scan_kwargs, row_of, detail_of):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("940x620")
        self._apply_icon(win)
        win.transient(self.root)
        win.configure(bg=CLR["bg"])

        # ── 顶部：标题 + 进度条 + 效率标签 ──
        head = ttk.Frame(win)
        head.pack(fill="x", padx=10, pady=(10, 0))
        toprow = ttk.Frame(head)
        toprow.pack(fill="x")
        lbl = ttk.Label(toprow, text="正在扫描…", foreground=CLR["accent"],
                        font=("Microsoft YaHei UI", 10, "bold"))
        lbl.pack(side="left")
        btn_rescan = ttk.Button(toprow, text="↻ 重新扫描", command=lambda: self._rescan(win, reopen))
        btn_rescan.pack(side="right")
        bar = ttk.Progressbar(head, mode="determinate", maximum=1000)
        bar.pack(fill="x", pady=(6, 2))
        lbl_prog = ttk.Label(head, text="", foreground=CLR["text_dim"])
        lbl_prog.pack(anchor="w")

        # ── 结果 / 错误横幅 ──
        banner = tk.Label(win, text="", anchor="w", justify="left", wraplength=900,
                          font=("Microsoft YaHei UI", 9), padx=12, pady=8)
        banner.pack(fill="x", padx=10, pady=(6, 0))

        frm = ttk.Frame(win)
        frm.pack(fill="both", expand=True, padx=10, pady=6)
        cols = [c[0] for c in columns]
        tree = ttk.Treeview(frm, columns=cols, show="headings", height=16)
        for (c, h), w in zip(columns, widths):
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="w")
        vsb = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)
        tree._item_map: dict = {}  # type: ignore[attr-defined]
        tree.bind("<Double-1>", lambda e: self._open_row(tree, detail_of))

        status = ttk.Label(win, text="", relief="flat", anchor="w",
                           background="#e4ebf5", padding=(10, 5))
        status.pack(fill="x", side="bottom")

        state = {"last_log_pct": -1}

        def show_banner(text: str, kind: str = "ok"):
            color = {"ok": CLR["ok"], "warn": CLR["warn"], "err": CLR["err"]}[kind]
            banner.configure(text=text, fg=color,
                             bg={"ok": "#eef7f0", "warn": "#fff4e6",
                                 "err": "#fdeeec"}[kind])
            if not text:
                banner.configure(text="", bg=CLR["bg"])

        def on_progress(rep: dict):
            """rep: {phase,done,total,current,elapsed} —— 每处理完一项回调。"""
            try:
                done = rep.get("done", 0)
                total = rep.get("total", 0) or 1
                elapsed = rep.get("elapsed", 0.0)
                current = rep.get("current", "") or ""
                finished = rep.get("finished", False)
                pct = done / total
                try:
                    bar.configure(value=int(pct * 1000))
                except tk.TclError:
                    pass
                speed = (done / elapsed) if elapsed > 0.05 else float("nan")
                if speed == speed:  # 非 NaN
                    remain = (total - done) / speed if speed > 0 else 0.0
                    speed_txt = f"{speed:.0f} 项/秒"
                    eta_txt = core._fmt_eta(remain) if remain > 0 else "即将完成"
                else:
                    speed_txt, eta_txt = "计算中…", "计算中…"
                try:
                    lbl_prog.configure(
                        text=f"已检测 {done}/{total} 项（{pct * 100:.1f}%）｜当前：{current or '—'}"
                             f"｜{speed_txt}｜已用 {elapsed:.1f} 秒｜预计还需 {eta_txt}"
                    )
                except tk.TclError:
                    pass
                # 主窗口日志按 10% 一档汇报（避免刷屏）
                mark = int(pct * 100 / 10)
                if not finished and mark > state["last_log_pct"]:
                    state["last_log_pct"] = mark
                    try:
                        self._log(f"📊 [{name}检测] 进度 {pct * 100:.0f}%"
                                  f"（{done}/{total}）｜{speed_txt}｜已用 {elapsed:.1f}s")
                    except Exception:  # noqa: BLE001
                        pass
            except Exception as e:  # noqa: BLE001 —— 兜底：不允许进度回调打断窗口
                try:
                    banner.configure(text=f"进度刷新异常（扫描继续）：{e}",
                                     fg=CLR["err"], bg="#fdeeec")
                except tk.TclError:
                    pass

        def fill(result, err=None):
            if err is not None:
                # 扫描线程异常：让窗口脱离“正在扫描”并显示原因
                try:
                    bar.configure(value=1000)
                    lbl.configure(text="扫描出错")
                    lbl_prog.configure(text="✖ 扫描异常")
                    show_banner(f"扫描失败：{err}\n请点击「↻ 重新扫描」重试，"
                                f"或检查 DSH 数据目录（DSH_HOME={core.DSH_HOME}）。",
                                kind="err")
                    status.configure(text="扫描异常 — 未获得结果")
                except tk.TclError:
                    return
                try:
                    self._log(f"✖ [{name}检测] 扫描失败：{err}")
                except Exception:  # noqa: BLE001
                    pass
                return
            try:
                bar.configure(value=1000)
                # 保留进度条显示 100%，仅更新标签
                elapsed = result.get("elapsed", 0.0)
                speed = result.get("speed", 0.0)
                if elapsed:
                    lbl_prog.configure(
                        text=f"✔ 完成（用时 {elapsed:.2f} 秒，平均 {speed:.1f} 项/秒）"
                    )
                else:
                    lbl_prog.configure(text="✔ 完成")
            except tk.TclError:
                return  # 窗口已被关闭
            items = result.get("items", [])
            try:
                for it in items:
                    iid = tree.insert("", "end", values=row_of(it))
                    tree._item_map[iid] = it  # type: ignore[attr-defined]
            except Exception as e:  # noqa: BLE001 —— 兜底：不让填表异常卡死窗口
                try:
                    lbl.configure(text="填表时遇到异常，已显示部分结果")
                    banner.configure(text=f"⚠ 列表渲染异常：{e}",
                                     fg=CLR["err"], bg="#fdeeec")
                except tk.TclError:
                    return
            root = result.get("root")
            errs = result.get("errors") or []
            if root:
                lbl.configure(text=f"扫描目录：{root}")
            else:
                lbl.configure(text="扫描完成")
            total_size = sum(it.get("size", 0) for it in items)
            eff = f"共 {len(items)} 项    合计 {core.human_size(total_size)}"
            if elapsed:
                eff += f"    用时 {elapsed:.2f} 秒"
            if speed:
                eff += f"    平均 {speed:.1f} 项/秒"
            eff += "    双击行可打开所在路径"
            status.configure(text=eff)

            # 空态 / 错误诊断横幅
            if errs:
                show_banner("⚠ " + "；".join(str(e) for e in errs[:3])
                            + ("…" if len(errs) > 3 else ""), kind="err")
            elif not items:
                show_banner(f"未检测到任何{name}。\n"
                            f"扫描目录：{root or '（未指定）'}\n"
                            f"请确认 DSH 数据目录（DSH_HOME={core.DSH_HOME}）正确，"
                            f"或点击「↻ 重新扫描」重试。", kind="warn")
            else:
                show_banner(f"✅ 检测成功：共 {len(items)} 项，合计 {core.human_size(total_size)}，"
                            f"用时 {elapsed:.2f} 秒（平均 {speed:.1f} 项/秒）")
            self._log(f"✅ [{name}检测] 完成：{len(items)} 项，合计 {core.human_size(total_size)}，"
                      f"用时 {elapsed:.2f}s（{speed:.1f} 项/秒）")

        worker = Worker(on_log=lambda m: None, on_finish=fill, on_progress=on_progress)

        def scan():
            try:
                return scan_fn(**scan_kwargs,
                               on_progress=lambda rep: worker.q.put(("progress", rep)))
            except Exception as e:  # noqa: BLE001
                return {"items": [], "errors": [str(e)],
                        "elapsed": 0.0, "speed": 0.0}

        worker.start(scan)
        win.after(120, lambda: self._poll_window(worker, win))

    def _rescan(self, win: tk.Toplevel, reopen):
        try:
            win.destroy()
        except tk.TclError:
            pass
        reopen()

    def _poll_window(self, worker: Worker, win: tk.Toplevel):
        try:
            if worker.pump():
                return
        except tk.TclError:
            return  # 窗口已关闭
        except Exception as e:  # noqa: BLE001 —— 兜底：显示错误且继续轮询，杜绝“卡在正在扫描”
            try:
                self._log(f"⚠ 扫描轮询异常（继续等待）：{e}")
            except Exception:  # noqa: BLE001
                pass
        try:
            win.after(120, lambda: self._poll_window(worker, win))
        except tk.TclError:
            pass

    def _open_row(self, tree, detail_of):
        sel = tree.selection()
        if not sel:
            return
        it = getattr(tree, "_item_map", {}).get(sel[0])
        if it is None:
            return
        self._try_open(detail_of(it))

    def _try_open(self, path_str: str):
        if not path_str:
            return
        import subprocess
        p = Path(path_str)
        if p.is_dir():
            subprocess.Popen(["explorer", str(p)])
        else:
            subprocess.Popen(["explorer", "/select,", str(p)])

    # ---------------- CSV 导出 ----------------
    def export_csv(self):
        # 重扫一次并导出两份 CSV 到程序所在目录
        import csv
        base = app_dir()
        try:
            plugins = core.scan_plugins(include_core=True)
            skills = core.scan_skills()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"扫描失败：{e}")
            return
        wrote = []
        with open(base / "dsh_plugins.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["名称", "版本", "大小(字节)", "大小", "启用", "来源", "路径"])
            for it in plugins["items"]:
                w.writerow([it["name"], it["version"], it["size"], it["size_text"],
                            "是" if it["enabled"] else "", it["source"], it["path"]])
        wrote.append("dsh_plugins.csv")
        with open(base / "dsh_skills.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["名称", "版本", "大小(字节)", "大小", "路径"])
            for it in skills["items"]:
                w.writerow([it["name"], it["version"], it["size"], it["size_text"], it["path"]])
        wrote.append("dsh_skills.csv")
        messagebox.showinfo(APP_TITLE, f"已导出：\n" + "\n".join(str(base / n) for n in wrote))

    # ---------------- 设置 ----------------
    def show_settings(self):
        env = core.DSH_HOME
        skills_root = core.scan_skills().get("root", "")
        messagebox.showinfo(
            APP_TITLE,
            f"DSH 数据目录（DSH_HOME）：\n{env}\n\n"
            f"技能目录：\n{skills_root}\n\n"
            "提示：可通过环境变量 DSH_HOME / DSH_SKILLS 更改检测位置。",
        )

    # ---------------- 行双击 ----------------
    def _on_row_double(self, _evt):
        inst = self._selected_install()
        if inst:
            self._try_open(inst["path"])

    # ---------------- 类型/状态列 hover 浮窗 ----------------
    def _row_at(self, x, y):
        """返回 (install_dict, column_id) 或 (None, None)。"""
        iid = self.tree.identify_row(y)
        if not iid:
            return None, None
        col = self.tree.identify_column(x)
        for r in self.install_rows:
            if r["iid"] == iid:
                return r["data"], col
        return None, None

    def _on_tree_motion(self, event):
        try:
            inst, col = self._row_at(event.x, event.y)
            if inst is None:
                self._hide_tip()
                return
            if col == "#1":  # 类型列
                text = self._kind_tip_text(inst)
                self._show_tip(event, text, width=480)
            elif col == "#4":  # 版本性质列
                text = self._nature_tip_text(inst)
                self._show_tip(event, text, width=360)
            elif col == "#6":  # 状态列
                text = self._status_tip_text(inst)
                self._show_tip(event, text, width=340)
            else:
                self._hide_tip()
        except tk.TclError:
            self._hide_tip()

    def _stability_line(self, inst: dict, with_title: bool = True) -> str:
        """返回稳定性/适配性的展示文本。"""
        assess = inst.get("assess") or {}
        grade = assess.get("grade", inst.get("grade", ""))
        label = assess.get("grade_label", inst.get("grade_label", ""))
        reason = assess.get("reason", "")
        color_note = {"stable": "✅", "candidate": "🟠", "prerelease": "🟣", "unstable": "🛑"}.get(grade, "")
        head = f"◉ 版本性质：{label} {color_note}" if with_title else f"{label} {color_note}"
        if grade == "unstable":
            head += "\n   ⚠ 未能在官网核实该版本 —— 视为【不稳定版】，请谨慎使用"
        if reason:
            head += f"\n   依据：{reason}"
        return head

    def _kind_tip_text(self, inst: dict) -> str:
        kind = inst["kind"]
        info = KIND_INFO.get(kind)
        if not info:
            return "未知类型。"
        gh = (self.official or {}).get("github", {})
        npm = (self.official or {}).get("npm", {})
        local = inst.get("version") or "—"
        if kind == core.INSTALL_KIND_SOURCE:
            ref = gh.get("version") or "获取失败"
            need = inst.get("status") == "可更新"
        else:
            ref = npm.get("version") or "获取失败"
            need = inst.get("status") in ("可更新", "可更新(npm)")
        recent = gh.get("recent") or []
        lines = [
            f"【{info['title']}】",
            "",
            f"◉ 这是什么：{info['what']}",
            "",
            f"◉ 在 DSH 中作用：{info['role']}",
            "",
            f"◉ 版本：本地 {local}   ∥   官方({info['ref']}) {ref}",
            f"◉ 是否需要立即更新：{'是，有可用更新' if need else '否，已是最新'}",
            "",
            self._stability_line(inst),
            "",
            f"◉ 更新方式：{info['how']}",
        ]
        if need and recent:
            lines.append("")
            lines.append("◉ 官方近期更新内容（最近若干提交，可作更新预期参考）：")
            for c in recent[:4]:
                lines.append(f"   · {c.get('date', '')}  {c.get('msg', '')}")
        lines.append("")
        lines.append("（提示：更新前请先退出正在运行的 DeepSeek Harness）")
        return "\n".join(lines)

    def _nature_tip_text(self, inst: dict) -> str:
        ver = inst.get("version") or "—"
        return f"当前版本 {ver}\n\n{self._stability_line(inst)}"

    def _status_tip_text(self, inst: dict) -> str:
        status = inst.get("status", "—")
        ver = inst.get("version") or "—"
        base = ""
        if status == "可更新":
            base = (f"当前版本 {ver} 落后于官方，可点击\n"
                    f"「⬇ 更新所选安装」一键升级（自动备份后替换）。")
        elif status == "已是最新":
            base = f"当前版本 {ver} 与官方一致，无需更新。"
        else:
            base = f"状态：{status}\n（版本信息：{ver}）"
        # 若该版本不稳定，追加醒目提示
        grade = inst.get("grade", "")
        if grade == "unstable":
            base += "\n\n🛑 注意：该版本【不稳定版】，官网无法核实，升级请谨慎。"
        elif grade == "prerelease":
            base += "\n\n🟣 提示：该版本为官方预发布（alpha/beta），可能存在兼容性变化。"
        return base

    def _show_tip(self, event, text: str, width: int = 460):
        if self._tip_win is not None:
            try:
                self._tip_win.destroy()
            except tk.TclError:
                pass
            self._tip_win = None
        if not text:
            return
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg="#2b3441")
        lab = tk.Label(
            win, text=text, justify="left", anchor="nw", wraplength=width,
            bg="#ffffff", fg="#22303f", font=("Microsoft YaHei UI", 9),
            padx=12, pady=10, bd=0,
        )
        lab.pack()
        # 位置：尽量贴合鼠标，避免超出屏幕
        x = event.x_root + 16
        y = event.y_root + 14
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if x + width > sw - 8:
            x = event.x_root - width - 10
        if y + 320 > sh - 8:
            y = event.y_root - 320
        win.geometry(f"+{int(x)}+{int(y)}")
        self._tip_win = win

    def _hide_tip(self):
        if self._tip_win is not None:
            try:
                self._tip_win.destroy()
            except tk.TclError:
                pass
            self._tip_win = None


# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    app = UpdaterApp(root)

    if "--smoke" in sys.argv:
        # 冒烟：短暂打开主窗口 + 插件/技能子窗口后自动关闭
        def _open_subwindows():
            try:
                app.open_plugins()
                app.open_skills()
            except Exception as e:  # noqa: BLE001
                print("subwindow error:", e)

        root.after(900, _open_subwindows)
        root.after(4200, root.destroy)
    else:
        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
    return app


if __name__ == "__main__":
    main()
