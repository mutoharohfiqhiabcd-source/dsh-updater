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
import i18n
from i18n import t

APP_TITLE = t("DeepSeek Harness 自动检测与更新器")
APP_VERSION = "0.6.8"


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
# 主题色板（美工）—— 浅色 / 深色两套
# ---------------------------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#f2f5f9", "panel": "#ffffff", "panel_line": "#d7dee8",
        "accent": "#0b57d0", "accent_hover": "#0842a0", "accent_fg": "#ffffff",
        "text": "#1c2733", "text_dim": "#5a6a7a",
        "ok": "#1a7f37", "warn": "#b35900", "err": "#c5221f",
        "heading_bg": "#dfe8f6", "heading_fg": "#12315f",
        "log_bg": "#0f1722", "log_fg": "#d7e1ee",
        "status_bg": "#e4ebf5",
        "row_bg": {
            "update": "#fff3e0", "ok": "#e8f5e9", "err": "#fdecea",
            "dim": "#f4f6f9", "candidate": "#fff8e1", "prerelease": "#f3e5f5",
            "unstable": "#fce4ec",
        },
        "tree_bg": "#ffffff", "tree_sel": "#cfe0f7",
    },
    "dark": {
        "bg": "#12161c", "panel": "#1b2129", "panel_line": "#2d3742",
        "accent": "#4f8cff", "accent_hover": "#3a74e0", "accent_fg": "#ffffff",
        "text": "#dfe6ee", "text_dim": "#93a1af",
        "ok": "#4caf7d", "warn": "#e0a54f", "err": "#ef6b62",
        "heading_bg": "#232c37", "heading_fg": "#b7c9e4",
        "log_bg": "#0a0d12", "log_fg": "#c3d0de",
        "status_bg": "#232c37",
        "row_bg": {
            "update": "#3a2f16", "ok": "#17301f", "err": "#3a1c1c",
            "dim": "#232a33", "candidate": "#3a3118", "prerelease": "#2e2140",
            "unstable": "#451726",
        },
        "tree_bg": "#171d25", "tree_sel": "#27466e",
    },
}

CLR = dict(THEMES["light"])

# 插件窗口（暗绿）与技能窗口（暗紫）独立强调色
ACCENT_PLUGIN = {"light": "#1e7d3c", "dark": "#5bc078"}
ACCENT_SKILL = {"light": "#6a1b9a", "dark": "#bb86fc"}

# 各安装类型在此程序浮窗中的说明
KIND_INFO = {
    core.INSTALL_KIND_SOURCE: {
        "badge": t("源码检出"),
        "title": t("源码检出 · Source Checkout"),
        "what": t("DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。"
                "一般来自 git clone 或 GitHub 源码 zip 解压，包含 apps/cli 等全部源码。"),
        "role": t("程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），"
                "内置 dsh-* 插件包大多源自这里的 packages 工程。"),
        "how": t("对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换"
               "（node_modules/.git 会保留并移回，可勾选随后 pnpm install）。"),
        "ref": "GitHub master",
    },
    core.INSTALL_KIND_NPM: {
        "badge": t("npm 全局"),
        "title": t("npm 全局安装 · @deepseek-ai/dsh"),
        "what": t("通过 npm 全局安装的 dsh 命令行工具包（node_modules/@deepseek-ai/dsh）。"),
        "role": t("提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、"
                "加载当前安装的运行时插件。"),
        "how": t("对比 npm registry 的 latest 发布版；更新方式：npm install -g @deepseek-ai/dsh@latest。"),
        "ref": "npm latest",
    },
    core.INSTALL_KIND_PROFILE: {
        "badge": t("运行时 profile"),
        "title": t("运行时 Profile · 插件装载实例"),
        "what": t("DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理"
                "该 profile 启用的插件清单（package.json 的 dsh.profile.bundles）与本地配置。"),
        "role": t("决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”"
                "层面的宿主目录，随 dsh CLI / 源码安装自动生成。"),
        "how": t("本身不单独更新：升级其来源（npm 全局 dsh 或源码检出）后，重启 DSH 即用新版。"),
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
        root.title(f"{APP_TITLE} v{APP_VERSION}")
        # 高度按实际内容取：底部状态栏（含版本号）与日志区都要放得下，
        # 否则 pack 会把排在后面的部件完全挤掉（见 _build_ui 里的说明）。
        root.geometry("1020x700")
        root.minsize(860, 660)

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
        self._dark = False                 # 当前主题（False=浅色）
        self._tree_tags_applied = False
        self.style = ttk.Style(root)
        try:
            self.style.theme_use("clam")
        except Exception:  # noqa: BLE001
            pass

        # 应用图标（开发时与脚本同目录；PyInstaller 打包后内置在 exe 资源中）
        self._icon_path = str(resource_path("dsh_updater.ico"))
        if Path(self._icon_path).is_file():
            try:
                root.iconbitmap(self._icon_path)
            except Exception:  # noqa: BLE001
                pass

        self.settings = core.load_settings()
        i18n.set_language(str(self.settings.get("language") or i18n.AUTO))
        self._setup_style()
        self._build_ui()
        self._log(f"{APP_TITLE} 已启动。\nDSH 数据目录：{core.DSH_HOME}\n"
                  f"设置文件：{core.settings_file()}")
        self._log(t("正在自动检测本机安装与官方版本…"))
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
        """统一美工：配色 / 字体 / 组件样式（读当前 CLR，可重复调用以切换主题）。"""
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
        btn_active = CLR["accent_hover"] if not self._dark else "#2b3d5e"
        s.configure("TButton", background=CLR["panel"], foreground=CLR["text"],
                    bordercolor=CLR["panel_line"], focusthickness=0, padding=(14, 6))
        s.map("TButton", background=[("active", btn_active), ("pressed", "#c8d2e0")],
              foreground=[("active", CLR["text"])])
        s.configure("Accent.TButton", background=CLR["accent"], foreground=CLR["accent_fg"],
                    bordercolor=CLR["accent"], padding=(16, 7))
        s.map("Accent.TButton",
              background=[("active", CLR["accent_hover"]), ("pressed", CLR["accent_hover"]),
                          ("disabled", "#5a6f92")],
              foreground=[("disabled", "#c7d2e0")])
        s.configure("Warn.TButton", background="#e8710a", foreground="#ffffff",
                    bordercolor="#e8710a", padding=(16, 7))
        s.map("Warn.TButton", background=[("active", "#cf6407"), ("disabled", "#f0b98a")],
              foreground=[("disabled", "#ffffff")])

        # 进度条
        s.configure("TProgressbar", background=CLR["accent"], troughcolor=CLR["panel_line"],
                    bordercolor=CLR["bg"], lightcolor=CLR["accent"], darkcolor=CLR["accent"])

        # Treeview
        s.configure("Treeview", background=CLR["tree_bg"], fieldbackground=CLR["tree_bg"],
                    foreground=CLR["text"], rowheight=30, bordercolor=CLR["panel_line"])
        s.map("Treeview", background=[("selected", CLR["tree_sel"])],
              foreground=[("selected", CLR["text"])])
        s.configure("Treeview.Heading", background=CLR["heading_bg"],
                    foreground=CLR["heading_fg"], padding=(8, 6),
                    font=("Microsoft YaHei UI", 10, "bold"))
        s.map("Treeview.Heading", background=[("active", CLR["heading_bg"])])

        # 滚动条
        s.configure("Vertical.TScrollbar", background=CLR["panel_line"], troughcolor=CLR["bg"],
                    bordercolor=CLR["bg"], arrowcolor=CLR["text_dim"])
        s.configure("Horizontal.TScrollbar", background=CLR["panel_line"], troughcolor=CLR["bg"],
                    bordercolor=CLR["bg"], arrowcolor=CLR["text_dim"])
        s.configure("TCheckbutton", background=CLR["panel"], foreground=CLR["text"])

        # 状态/性质 tag（行前景 + 行背景）
        row_bg = CLR["row_bg"]
        if hasattr(self, "tree"):
            for tag, col in STATUS_TAG.items():
                self.tree.tag_configure(tag, foreground=col,
                                        background=row_bg.get(tag, CLR["tree_bg"]))
        self._tree_tags_applied = True

    def toggle_theme(self):
        """深色 / 浅色主题切换。"""
        self._dark = not self._dark
        CLR.clear()
        CLR.update(THEMES["dark" if self._dark else "light"])
        # ttk 主题刷新
        self._setup_style()
        # 原生控件颜色刷新
        try:
            self.root.configure(bg=CLR["bg"])
            self.txt.configure(bg=CLR["log_bg"], fg=CLR["log_fg"])
            self.status.configure(bg=CLR["status_bg"], fg=CLR["text_dim"])
            self._status_bar.configure(bg=CLR["status_bg"])
            self.lbl_version.configure(bg=CLR["status_bg"], fg=CLR["accent"])
            self.lbl_pref_title.configure(bg=CLR["panel"], fg=CLR["text"])
            self.lbl_pref_file.configure(bg=CLR["panel"], fg=CLR["text_dim"])
            self.lbl_github.configure(background=CLR["panel"],
                                      foreground=CLR["accent"])
            self.lbl_npm.configure(background=CLR["panel"])
        except Exception:  # noqa: BLE001
            pass
        self.btn_theme.configure(
            text=t("🌙 深色模式") if not self._dark else t("☀️ 浅色模式"))
        self._log(t("已切换到{p1}主题。", p1=t('深色') if self._dark else t('浅色')))

    def _build_ui(self):
        self.root.configure(bg=CLR["bg"])

        # ── 底部状态栏：必须先 pack，才能在内容超长时保住自己的位置 ──
        # 注意：pack 是按调用顺序分配空间的，内容总高度超出窗口时「最后 pack 的
        # 部件」会被完全挤掉。状态栏排最后会导致版本号直接不显示，所以放在最前。
        self._status_bar = tk.Frame(self.root, background=CLR["status_bg"])
        self._status_bar.pack(fill="x", side="bottom")
        self.status = tk.Label(self._status_bar, text=t("就绪"), relief="flat", anchor="w",
                               background=CLR["status_bg"], foreground=CLR["text_dim"],
                               font=("Microsoft YaHei UI", 9), padx=10, pady=5)
        self.status.pack(side="left", fill="x", expand=True)
        self.lbl_version = tk.Label(
            self._status_bar, text=t("当前版本 v{APP_VERSION} · 检查更新", APP_VERSION=APP_VERSION), anchor="e",
            background=CLR["status_bg"], foreground=CLR["accent"],
            font=("Microsoft YaHei UI", 9, "underline"), cursor="hand2",
            padx=10, pady=5)
        self.lbl_version.pack(side="right")
        self.lbl_version.bind("<Button-1>", self._on_version_click)
        self.lbl_version.bind(
            "<Enter>", lambda e: self.lbl_version.configure(foreground=CLR["accent_hover"]))
        self.lbl_version.bind(
            "<Leave>", lambda e: self.lbl_version.configure(foreground=CLR["accent"]))
        self._upd_win = None

        # ── 顶部横幅：标题与官方版本条 ──
        top = ttk.Frame(self.root, style="Panel.TFrame")
        top.pack(fill="x", padx=10, pady=(10, 4))
        # 左侧标题区
        titlebox = ttk.Frame(top, style="Panel.TFrame")
        titlebox.pack(side="left", padx=12, pady=8)
        ttk.Label(titlebox, text=t("DeepSeek Harness 更新器"),
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(titlebox, text=t("自动检测本机安装 · 对比官方版本 · 插件/技能扫描 · 一键更新"),
                  style="Dim.TLabel").pack(anchor="w", pady=(2, 0))
        # 右侧版本条（白底卡片）
        verbox = ttk.Frame(top, style="Panel.TFrame")
        verbox.pack(side="right", padx=12, pady=8)
        self.lbl_github = ttk.Label(verbox, text=t("🌐 官方 GitHub master：检测中…"),
                                    foreground=CLR["accent"], background=CLR["panel"])
        self.lbl_github.pack(anchor="e")
        self.lbl_npm = ttk.Label(verbox, text=t("📦 npm 发布版：检测中…"),
                                 foreground="#7a4a0b", background=CLR["panel"])
        self.lbl_npm.pack(anchor="e", pady=(2, 0))

        # ── 中部：安装列表 ──
        mid = ttk.LabelFrame(self.root, text=t("本机检测到的 DeepSeek Harness 安装（悬停“类型/状态/性质”列查看说明）"))
        mid.pack(fill="both", expand=False, padx=10, pady=6)
        cols = ("kind", "path", "version", "nature", "ref", "status")
        heads = {"kind": t("类型"), "path": t("位置"), "version": t("当前版本"),
                 "nature": t("版本性质"), "ref": t("官方参考版本"), "status": t("状态")}
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=5)
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
        self.btn_update = ttk.Button(btns, text=t("⬇ 更新所选安装"), style="Accent.TButton",
                                     command=self.update_selected)
        self.btn_update.pack(side="left", padx=(0, 8))
        self.btn_plugins = ttk.Button(btns, text=t("🧩 插件检测"), command=self.open_plugins)
        self.btn_plugins.pack(side="left", padx=(0, 8))
        self.btn_skills = ttk.Button(btns, text=t("📚 技能检测"), command=self.open_skills)
        self.btn_skills.pack(side="left", padx=(0, 8))
        self.btn_refresh = ttk.Button(btns, text=t("🔄 重新检测"), command=self.refresh_all)
        self.btn_refresh.pack(side="left")
        self.btn_settings = ttk.Button(btns, text=t("⚙ 数据目录"), command=self.show_settings)
        self.btn_settings.pack(side="right", padx=(8, 0))
        self.btn_export = ttk.Button(btns, text=t("💾 导出 CSV"), command=self.export_csv)
        self.btn_export.pack(side="right")
        self.btn_theme = ttk.Button(btns, text=t("🌙 深色模式"), command=self.toggle_theme)
        self.btn_theme.pack(side="right", padx=(0, 8))

        # ── 偏好设置行 ──
        # 用 Panel 白底卡片：TCheckbutton / Dim.TLabel 两个样式都是以 panel 为底色的。
        prefs = ttk.Frame(self.root, style="Panel.TFrame")
        prefs.pack(fill="x", padx=10, pady=(6, 0))
        prow = ttk.Frame(prefs, style="Panel.TFrame")
        prow.pack(fill="x", padx=12, pady=8)
        self.lbl_pref_title = tk.Label(prow, text=t("⚙ 偏好设置"), background=CLR["panel"],
                                       foreground=CLR["text"],
                                       font=("Microsoft YaHei UI", 9, "bold"))
        self.lbl_pref_title.pack(side="left", padx=(0, 14))

        # 语言选择：显示各语言的自称，用户一眼能找到自己的语言
        self.lbl_lang = tk.Label(prow, text=t("语言"), background=CLR["panel"],
                                 foreground=CLR["text"],
                                 font=("Microsoft YaHei UI", 9))
        self.lbl_lang.pack(side="left", padx=(0, 6))
        self._lang_options = [(i18n.AUTO, t("跟随系统"))] + \
                             [(code, native) for code, native, _ in i18n.LANGUAGES]
        self.cmb_lang = ttk.Combobox(prow, values=[label for _, label in self._lang_options],
                                     state="readonly", width=10)
        cur_setting = str(self.settings.get("language") or i18n.AUTO)
        self.cmb_lang.current(next((i for i, (code, _) in enumerate(self._lang_options)
                                    if code == cur_setting), 0))
        self.cmb_lang.pack(side="left", padx=(0, 14))
        self.cmb_lang.bind("<<ComboboxSelected>>", self._on_language_change)

        self.var_gpu = tk.BooleanVar(value=bool(self.settings.get("gpu_acceleration")))
        self.chk_gpu = ttk.Checkbutton(prow, text=t("使用 GPU 加速"), variable=self.var_gpu,
                                       command=self._on_gpu_toggle)
        self.chk_gpu.pack(side="left")
        ttk.Label(prow, text=t("DSH 暂无 GPU 加速选项，仅记录偏好，暂不影响行为。"),
                  style="Dim.TLabel").pack(side="left", padx=(14, 0))
        self.lbl_pref_file = tk.Label(prow, text=t("📂 打开设置文件"), background=CLR["panel"],
                                      foreground=CLR["text_dim"], cursor="hand2",
                                      font=("Microsoft YaHei UI", 8, "underline"))
        self.lbl_pref_file.pack(side="right", padx=(10, 0))
        self.lbl_pref_file.bind("<Button-1>", lambda e: self._open_settings_file())

        # ── 当前操作进度横幅（扫描/下载/更新通用） ──
        progframe = ttk.LabelFrame(self.root, text=t("当前任务"))
        progframe.pack(fill="x", padx=10, pady=4)
        inner = ttk.Frame(progframe)
        inner.pack(fill="x", padx=6, pady=6)
        self.prog = ttk.Progressbar(inner, mode="determinate", maximum=1000)
        self.prog.pack(side="left", fill="x", expand=True)
        self.lbl_progress = ttk.Label(inner, text=t("等待任务…"), width=60, anchor="e")
        self.lbl_progress.pack(side="right", padx=(10, 0))

        # ── 日志区 ──
        logframe = ttk.LabelFrame(self.root, text=t("日志 / 进度"))
        logframe.pack(fill="both", expand=True, padx=10, pady=6)
        self.txt = tk.Text(logframe, height=4, wrap="word", state="disabled",
                           font=("Consolas", 9), background=CLR["log_bg"],
                           foreground=CLR["log_fg"], borderwidth=0, padx=8, pady=6)
        logvsb = ttk.Scrollbar(logframe, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=logvsb.set)
        self.txt.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        logvsb.pack(side="right", fill="y", padx=(0, 6), pady=6)

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
        self.lbl_progress.configure(text=text or t("准备中…"))

    def _prog_set(self, value: float, text: str | None = None):
        """value 0.0~1.0；text 留空则自动显示百分比。"""
        self.prog.configure(value=int(max(0.0, min(value, 1.0)) * 1000))
        if text is None:
            text = t("进度：{p1:.1f}%", p1=value * 100)
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
        self._set_status(t("正在检测本机安装与官方版本…"))
        self._log(t("\n── 开始检测 ──"))
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
            messagebox.showerror(APP_TITLE, t("检测失败：\n{err}", err=err))
            self._set_status(t("检测失败"))
            return
        self.official = result["official"]
        gh = result["official"]["github"]
        npm = result["official"]["npm"]
        gh_txt = gh.get("version") or t("获取失败")
        npm_txt = npm.get("version") or t("获取失败")
        if gh.get("version"):
            gh_txt += t("（{p1}）", p1=gh.get('date', '')[:10])
        gh_assess = gh.get("assess") or {}
        npm_assess = npm.get("assess") or {}
        if gh_assess.get("grade") in ("prerelease", "unstable"):
            gh_txt += t("〔{p1}〕", p1=gh_assess.get('grade_label', ''))
        if npm_assess.get("grade") in ("prerelease", "unstable", "candidate"):
            npm_txt += t("〔{p1}〕", p1=npm_assess.get('grade_label', ''))
        self.lbl_github.configure(text=t("🌐 官方 GitHub master：{gh_txt}", gh_txt=gh_txt))
        self.lbl_npm.configure(text=t("📦 npm 发布版：{npm_txt}", npm_txt=npm_txt))

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
                self._log(t("    └ 稳定性判定：{p1}", p1=assess['reason']))
        # —— 自检结果 ——
        sc = result.get("selfcheck") or {}
        if sc.get("duplicates"):
            self._log(t("🛡 自检：发现并合并 {p1} 处重复安装（同一真实路径）", p1=sc['duplicates']))
            for n in sc.get("notes", []):
                self._log(f"    └ {n}")
        self._set_status(t("检测完成：发现 {p1} 处安装", p1=len(result['installs']))
                         + (t("（自检合并重复 {p1} 处）", p1=sc.get('duplicates', 0)) if sc.get("duplicates") else ""))
        if not result["installs"]:
            self._log(t("未自动发现安装，可使用界面按钮或自行检查路径。"))

    @staticmethod
    def _row_tag(inst: dict) -> str:
        """行 tag 优先级：不稳定/预发布最醒目，其次可更新状态。"""
        grade = inst.get("grade", "")
        if grade == "unstable":
            return "unstable"
        if grade == "prerelease":
            return "prerelease"
        status = inst.get("status", "")
        if t("可更新") in status:
            return "update"
        if grade == "candidate":
            return "candidate"
        if status == t("已是最新"):
            return "ok"
        if status and t("失败") in status:
            return "err"
        return "dim"

    @staticmethod
    def _status_tag(status: str) -> str:
        if t("可更新") in status:
            return "update"
        if status == t("已是最新"):
            return "ok"
        if status and t("失败") in status:
            return "err"
        return "dim"

    # ---------------- 更新 ----------------
    def _selected_install(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, t("请先在列表中选中一行安装。"))
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
                t("「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n"
                "请更新其对应的源码检出或 npm 全局安装。"),
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
        self._set_status(t("正在通过 npm 更新全局安装…"))
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
            messagebox.showerror(APP_TITLE, t("npm 更新失败：\n{err}", err=err))
            self._set_status(t("npm 更新失败"))
            self._prog_reset(t("npm 更新失败"))
            return
        messagebox.showinfo(APP_TITLE, result.get("message", t("npm 更新完成")))
        self._set_status(t("npm 更新完成"))
        self._prog_done(t("npm 更新完成"))
        self.refresh_all()

    def _confirm_source_update(self, inst):
        # 询问是否运行 pnpm install
        ask = tk.Toplevel(self.root)
        ask.title(t("更新源码检出"))
        self._apply_icon(ask)
        ask.transient(self.root)
        ask.grab_set()
        ask.resizable(False, False)
        frm = ttk.Frame(ask, padding=14)
        frm.pack()
        ttk.Label(
            frm,
            text=t("将更新源码检出："),
            font=("Microsoft YaHei UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(frm, text=inst["path"], wraplength=560).grid(row=1, column=0, sticky="w")
        cur = inst["version"] or "—"
        ref = (self.official["github"]["version"] if self.official else None) or "—"
        ttk.Label(frm, text=t("当前版本：{cur}    官方最新：{ref}", cur=cur, ref=ref)).grid(row=2, column=0, sticky="w", pady=4)
        # 目标版本稳定性/适配性提示
        gh = (self.official or {}).get("github", {}) or {}
        gh_assess = gh.get("assess") or {}
        if gh_assess.get("grade"):
            notes = []
            gl = gh_assess.get("grade_label", "")
            if gh_assess.get("grade") == "stable":
                notes.append(t("官方最新 {ref} 为【{gl}】。", ref=ref, gl=gl))
            elif gh_assess.get("grade") == "candidate":
                notes.append(t("官方最新 {ref} 为【{gl}】，发布候选版。", ref=ref, gl=gl))
            elif gh_assess.get("grade") == "prerelease":
                notes.append(t("⚠ 官方最新 {ref} 为【{gl}】（预发布），可能存在兼容性变化，请按需更新。", ref=ref, gl=gl))
            else:
                notes.append(t("🛑 官方最新 {ref} 官网信息不足，判定为【{gl}】，请谨慎更新。", ref=ref, gl=gl))
            if gh_assess.get("node_reason"):
                notes.append(t("适配性：{p1}", p1=gh_assess['node_reason']))
            if notes:
                ttk.Label(
                    frm, text="\n".join(notes), wraplength=560, foreground="#b3261e",
                ).grid(row=3, column=0, sticky="w", pady=(0, 6))
        ttk.Label(
            frm,
            text=t("流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n"
                 "（node_modules / .git 会自动移回新目录，以加快依赖安装）\n"
                 "更新期间请勿关闭本程序；若 DSH Web (3080) 正在运行将中止更新。"),
            foreground="#a00", wraplength=560,
        ).grid(row=4, column=0, sticky="w", pady=6)
        self.var_pnpm = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frm, text=t("替换后自动运行 pnpm install（推荐，用于同步依赖）"),
            variable=self.var_pnpm,
        ).grid(row=5, column=0, sticky="w", pady=4)
        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, sticky="e", pady=(10, 0))
        ttk.Button(btns, text=t("开始更新"), command=lambda: self._run_source_update(inst, ask)).pack(side="left", padx=4)
        ttk.Button(btns, text=t("取消"), command=ask.destroy).pack(side="left")

    def _run_source_update(self, inst, ask):
        ask.destroy()
        if self.busy:
            return
        self._set_busy(True)
        self._set_status(t("正在下载并替换源码…"))
        self._prog_reset(t("准备下载官方源码…"))
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
            self._prog_set(value, text=t("更新进度：{p1:.1f}%", p1=value * 100))
        except tk.TclError:
            pass

    def _on_source_update_done(self, result, err):
        self._set_busy(False)
        if err is not None:
            messagebox.showerror(APP_TITLE, t("更新失败：\n{err}", err=err))
            self._set_status(t("更新失败"))
            self._prog_reset(t("更新失败"))
            return
        msg = result.get("message", t("更新完成"))
        if result.get("backup"):
            msg += t("\n\n原目录备份于：\n{p1}", p1=result['backup'])
        messagebox.showinfo(APP_TITLE, msg)
        self._set_status(t("更新完成"))
        self._prog_done(t("更新完成"))
        self.refresh_all()

    # ---------------- 插件 / 技能窗口 ----------------
    def open_plugins(self):
        """插件窗口 —— 暗绿主题：检测最新版走 npm，同步更新支持 git/npm 源插件。"""
        accent = ACCENT_PLUGIN["dark" if self._dark else "light"]
        self._open_inventory_window(
            name=t("插件"),
            title=t("🧩 DeepSeek Harness 插件检测"),
            reopen=self.open_plugins,
            accent=accent,
            accent_label=t("暗绿主题"),
            columns=(("name", t("名称")), ("version", t("版本")), ("size", t("大小")),
                     ("installed", t("安装时间")), ("latest", t("最新版")), ("enabled", t("启用")),
                     ("source", t("来源"))),
            widths=(300, 88, 84, 120, 84, 58, 120),
            scan_fn=core.scan_plugins,
            scan_kwargs={},
            row_of=lambda it: (it["name"], it["version"] or "—", it["size_text"],
                               it.get("installed") or "—", "—",
                               t("✔ 启用") if it["enabled"] else t("内置"), it["source"]),
            detail_of=lambda it: it["path"],
            latest_fn=core.check_plugin_latest,
            update_fn=None,  # 插件更新=更新对应 dsh/运行时，见 update_selected
            update_label=t("⬇ 同步更新"),
        )

    def open_skills(self):
        """技能窗口 —— 暗紫主题：检测最新版走 git 来源，可同步 git pull。"""
        accent = ACCENT_SKILL["dark" if self._dark else "light"]
        self._open_inventory_window(
            name=t("技能"),
            title=t("📚 DeepSeek Harness 技能检测"),
            reopen=self.open_skills,
            accent=accent,
            accent_label=t("暗紫主题"),
            columns=(("name", t("名称")), ("version", t("版本")), ("size", t("大小")),
                     ("installed", t("安装时间")), ("latest", t("最新版"))),
            widths=(300, 100, 96, 122, 100),
            scan_fn=core.scan_skills,
            scan_kwargs={},
            row_of=lambda it: (it["name"], it["version"] or "—", it["size_text"],
                               it.get("installed") or "—", "—"),
            detail_of=lambda it: it["path"],
            latest_fn=core.check_skill_latest,
            update_fn=core.update_skills_git,
            update_label=t("⬇ git 同步更新"),
        )

    def _open_inventory_window(self, name, title, reopen, accent, accent_label,
                               columns, widths, scan_fn, scan_kwargs, row_of,
                               detail_of, latest_fn=None, update_fn=None,
                               update_label=None):
        win = tk.Toplevel(self.root)
        win.title(f"{title} · {APP_VERSION} · {accent_label}")
        win.geometry("1080x640")
        self._apply_icon(win)
        win.transient(self.root)
        win.configure(bg=CLR["bg"])

        # 自定义强调样式（插件=暗绿 / 技能=暗紫）
        accent_style = f"{name}.Accent.TButton"
        s = ttk.Style(win)
        s.configure(accent_style, background=accent, foreground="#ffffff",
                    bordercolor=accent, padding=(12, 6))
        s.map(accent_style, background=[("active", accent), ("disabled", "#8a9aa8")],
              foreground=[("disabled", "#ffffff")])

        # ── 顶部：标题 + 动作按钮 + 进度条 ──
        head = ttk.Frame(win)
        head.pack(fill="x", padx=10, pady=(10, 0))
        toprow = ttk.Frame(head)
        toprow.pack(fill="x")
        lbl = ttk.Label(toprow, text=t("正在扫描…"), foreground=accent,
                        font=("Microsoft YaHei UI", 10, "bold"))
        lbl.pack(side="left")
        # 操作按钮组（右）
        right = ttk.Frame(toprow)
        right.pack(side="right")
        if latest_fn is not None:
            btn_latest = ttk.Button(right, text=t("🔍 检测最新版"),
                                    style=accent_style,
                                    command=lambda: _check_latest())
            btn_latest.pack(side="left", padx=(0, 6))
        if update_label is not None:
            btn_update = ttk.Button(right, text=update_label, command=lambda: _sync_update())
            btn_update.pack(side="left", padx=(0, 6))
        btn_rescan = ttk.Button(right, text=t("↻ 重新扫描"),
                                command=lambda: self._rescan(win, reopen))
        btn_rescan.pack(side="left")
        bar = ttk.Progressbar(head, mode="determinate", maximum=1000)
        bar.pack(fill="x", pady=(6, 2))
        lbl_prog = ttk.Label(head, text="", foreground=CLR["text_dim"])
        lbl_prog.pack(anchor="w")

        # ── 结果 / 错误横幅 ──
        banner = tk.Label(win, text="", anchor="w", justify="left", wraplength=1030,
                          font=("Microsoft YaHei UI", 9), padx=12, pady=8,
                          bg=CLR["panel"], fg=CLR["text"])
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
                           background=CLR["status_bg"], padding=(10, 5))
        status.pack(fill="x", side="bottom")

        state = {"last_log_pct": -1}

        # 可更新行高亮（深绿边框提示）——按当前主题选色
        try:
            tree.tag_configure("newver",
                               background=CLR["row_bg"]["update"],
                               foreground=CLR["warn"])
        except Exception:  # noqa: BLE001
            pass

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
                    speed_txt = t("{speed:.0f} 项/秒", speed=speed)
                    eta_txt = core._fmt_eta(remain) if remain > 0 else t("即将完成")
                else:
                    speed_txt, eta_txt = t("计算中…"), t("计算中…")
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
                    banner.configure(text=t("进度刷新异常（扫描继续）：{e}", e=e),
                                     fg=CLR["err"], bg="#fdeeec")
                except tk.TclError:
                    pass

        def fill(result, err=None):
            if err is not None:
                # 扫描线程异常：让窗口脱离“正在扫描”并显示原因
                try:
                    bar.configure(value=1000)
                    lbl.configure(text=t("扫描出错"))
                    lbl_prog.configure(text=t("✖ 扫描异常"))
                    show_banner(f"扫描失败：{err}\n请点击「↻ 重新扫描」重试，"
                                f"或检查 DSH 数据目录（DSH_HOME={core.DSH_HOME}）。",
                                kind="err")
                    status.configure(text=t("扫描异常 — 未获得结果"))
                except tk.TclError:
                    return
                try:
                    self._log(t("✖ [{name}检测] 扫描失败：{err}", name=name, err=err))
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
                        text=t("✔ 完成（用时 {elapsed:.2f} 秒，平均 {speed:.1f} 项/秒）", elapsed=elapsed, speed=speed)
                    )
                else:
                    lbl_prog.configure(text=t("✔ 完成"))
            except tk.TclError:
                return  # 窗口已被关闭
            items = result.get("items", [])
            try:
                for it in items:
                    iid = tree.insert("", "end", values=row_of(it))
                    tree._item_map[iid] = it  # type: ignore[attr-defined]
            except Exception as e:  # noqa: BLE001 —— 兜底：不让填表异常卡死窗口
                try:
                    lbl.configure(text=t("填表时遇到异常，已显示部分结果"))
                    banner.configure(text=t("⚠ 列表渲染异常：{e}", e=e),
                                     fg=CLR["err"], bg="#fdeeec")
                except tk.TclError:
                    return
            root = result.get("root")
            errs = result.get("errors") or []
            if root:
                lbl.configure(text=t("扫描目录：{root}", root=root))
            else:
                lbl.configure(text=t("扫描完成"))
            total_size = sum(it.get("size", 0) for it in items)
            eff = t("共 {p1} 项    合计 {p2}", p1=len(items), p2=core.human_size(total_size))
            if elapsed:
                eff += t("    用时 {elapsed:.2f} 秒", elapsed=elapsed)
            if speed:
                eff += t("    平均 {speed:.1f} 项/秒", speed=speed)
            eff += t("    双击行可打开所在路径")
            status.configure(text=eff)

            # 空态 / 错误诊断横幅
            if errs:
                show_banner("⚠ " + t("；").join(str(e) for e in errs[:3])
                            + ("…" if len(errs) > 3 else ""), kind="err")
            elif not items:
                show_banner(f"未检测到任何{name}。\n"
                            f"扫描目录：{root or t('（未指定）')}\n"
                            f"请确认 DSH 数据目录（DSH_HOME={core.DSH_HOME}）正确，"
                            f"或点击「↻ 重新扫描」重试。", kind="warn")
            else:
                show_banner(f"✅ 检测成功：共 {len(items)} 项，合计 {core.human_size(total_size)}，"
                            f"用时 {elapsed:.2f} 秒（平均 {speed:.1f} 项/秒）")
            self._log(f"✅ [{name}检测] 完成：{len(items)} 项，合计 {core.human_size(total_size)}，"
                      f"用时 {elapsed:.2f}s（{speed:.1f} 项/秒）")

        # ---- 状态：供“检测最新版/同步更新”使用 ----
        state["items"] = []

        def _fill_done_hook(worker_, items_):
            state["items"] = items_
            # 让“检测最新版”按钮可用
            try:
                if latest_fn is not None:
                    btn_latest.configure(state="normal")
            except Exception:  # noqa: BLE001
                pass

        # 包装 fill：插入行后记录 items
        _orig_fill = fill

        def fill(result, err=None):
            _orig_fill(result, err)
            if err is None:
                try:
                    _fill_done_hook(worker, result.get("items", []) if result else [])
                except Exception:  # noqa: BLE001
                    pass

        def _apply_latest_result(latest_map: dict):
            """把检测到的最新版写回表格 latest 列，并标记可更新行。"""
            upd = 0
            for it in state["items"]:
                info = latest_map.get(it.get("name", "")) or {}
                latest = info.get("latest")
                err = info.get("error")
                col_name = "latest"
                for iid, item in getattr(tree, "_item_map", {}).items():
                    if item is it:
                        if latest:
                            tree.set(iid, col_name, latest)
                            try:
                                cur = item.get("version") or ""
                                if cur and compare_hook(cur, latest) < 0:
                                    tree.item(iid, tags=("newver",))
                                    upd += 1
                            except Exception:  # noqa: BLE001
                                pass
                        else:
                            tree.set(iid, col_name, "—")
                        break
            return upd

        def compare_hook(a: str, b: str) -> int:
            return core.compare_versions(a, b)

        def _check_latest():
            if latest_fn is None or not state.get("items"):
                return
            try:
                btn_latest.configure(state="disabled")
            except Exception:  # noqa: BLE001
                pass
            show_banner(t("正在检测 {p1} 项的最新版本（联网查询）…", p1=len(state['items'])), kind="ok")
            w = Worker(self._log,
                       lambda res, e: _latest_done(res, e),
                       on_progress=lambda rep: lbl_prog.configure(
                           text=f"检测最新版：{rep.get('done', 0)}/{rep.get('total', 0)}"
                                f"｜当前 {rep.get('current', '') or '—'}"))
            state["_latest_worker"] = w
            items_snapshot = list(state["items"])
            w.start(latest_fn, items_snapshot)
            win.after(120, lambda: self._poll_window(w, win))

        def _latest_done(res, err):
            try:
                btn_latest.configure(state="normal")
            except Exception:  # noqa: BLE001
                pass
            if err is not None:
                show_banner(t("检测最新版失败：{err}", err=err), kind="err")
                return
            upd = _apply_latest_result(res or {})
            total = len(state["items"])
            show_banner(t("✅ 最新版检测完成：共 {total} 项，其中 {upd} 项有可用更新", total=total, upd=upd)
                        + (t("（技能若无 git 来源则无法检测）") if name == t("技能") else "")
                        + t("。可在主窗口对源码检出/npm 全局执行更新。"),
                        kind="ok")
            status.configure(text=t("检测完成（最新版）：{total} 项 / 可更新 {upd} 项", total=total, upd=upd))

        def _sync_update():
            """技能：git pull 同步；插件：更新其 npm 全局 dsh（内置包随其更新）。"""
            if update_fn is None:
                # 插件窗口：引导到主窗口的“更新所选安装”（npm 全局 @deepseek-ai/dsh）
                if not messagebox.askyesno(
                        title, t("插件本身随 DeepSeek Harness 发布版更新。\n"
                               "是否打开主窗口执行「npm 全局 / 源码检出」更新？\n"
                               "（第三方插件请在对应 profile 中用 dsh plugin 更新）")):
                    return
                try:
                    win.destroy()
                except tk.TclError:
                    pass
                self.btn_update.invoke()
                return
            items_git = [it for it in state["items"]
                         if (Path(it.get("path", "")) / ".git").is_dir()]
            if not items_git:
                show_banner(t("没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），"
                            "请在官网手动下载覆盖。"), kind="warn")
                return
            show_banner(t("正在 git 同步 {p1} 个技能…", p1=len(items_git)), kind="ok")
            w = Worker(self._log,
                       lambda res, e: _sync_done(res, e))
            state["_sync_worker"] = w
            w.start(update_fn, items_git)
            win.after(120, lambda: self._poll_window(w, win))

        def _sync_done(res, err):
            if err is not None:
                show_banner(t("同步失败：{err}", err=err), kind="err")
                return
            res = res or {}
            okn = len(res.get("ok", []))
            fail = res.get("failed", [])
            skip = res.get("skipped", 0)
            txt = t("✅ git 同步完成：成功 {okn}，失败 {p1}，跳过 {skip}（无 git 来源）", okn=okn, p1=len(fail), skip=skip)
            if fail:
                txt += "\n" + "\n".join(f"   ✖ {a}: {b}" for a, b in fail[:5])
            show_banner(txt, kind="ok" if not fail else "warn")

        worker = Worker(on_log=lambda m: None, on_finish=fill, on_progress=on_progress)

        def scan():
            try:
                return scan_fn(**scan_kwargs,
                               on_progress=lambda rep: worker.q.put(("progress", rep)))
            except Exception as e:  # noqa: BLE001
                return {"items": [], "errors": [str(e)],
                        "elapsed": 0.0, "speed": 0.0}

        worker.start(scan)
        # “检测最新版”按钮初始禁用，待扫描完成才可用
        try:
            btn_latest.configure(state="disabled")
        except Exception:  # noqa: BLE001
            pass
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
                self._log(t("⚠ 扫描轮询异常（继续等待）：{e}", e=e))
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
            messagebox.showerror(APP_TITLE, t("扫描失败：{e}", e=e))
            return
        wrote = []
        with open(base / "dsh_plugins.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([t("名称"), t("版本"), t("大小(字节)"), t("大小"), t("启用"), t("来源"), t("路径")])
            for it in plugins["items"]:
                w.writerow([it["name"], it["version"], it["size"], it["size_text"],
                            t("是") if it["enabled"] else "", it["source"], it["path"]])
        wrote.append("dsh_plugins.csv")
        with open(base / "dsh_skills.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([t("名称"), t("版本"), t("大小(字节)"), t("大小"), t("路径")])
            for it in skills["items"]:
                w.writerow([it["name"], it["version"], it["size"], it["size_text"], it["path"]])
        wrote.append("dsh_skills.csv")
        messagebox.showinfo(APP_TITLE, t("已导出：\n") + "\n".join(str(base / n) for n in wrote))

    # ---------------- 设置 ----------------
    def show_settings(self):
        env = core.DSH_HOME
        skills_root = core.scan_skills().get("root", "")
        messagebox.showinfo(
            APP_TITLE,
            t("DSH 数据目录（DSH_HOME）：\n{p1}\n\n技能目录：\n{p2}\n\n本更新器设置文件：\n{p3}\n\n提示：可通过环境变量 DSH_HOME / DSH_SKILLS 更改检测位置。",
              p1=env, p2=skills_root, p3=core.settings_file()),
        )

    # ---------------- 偏好设置 ----------------
    def _on_language_change(self, _evt=None):
        """语言下拉框变化：立即保存并重建界面。"""
        idx = self.cmb_lang.current()
        if idx < 0 or idx >= len(self._lang_options):
            return
        code = self._lang_options[idx][0]
        self.settings["language"] = code
        saved = core.save_settings(self.settings)
        i18n.set_language(code)
        if not saved:
            self._log(t("⚠ 语言偏好保存失败，本次运行仍会生效"))
        # 延迟重建：此刻回调正处于即将被销毁的控件的处理链上，直接 destroy 不安全
        self.root.after(30, self._rebuild_ui)

    def _rebuild_ui(self):
        """按当前语言重建整个界面（销毁所有子部件后重新构建）。

        界面文案是在构建时取值的，所以换语言必须重建；重建后会重新检测一次，
        因此不会留下空白列表。
        """
        try:
            for child in self.root.winfo_children():
                child.destroy()
        except tk.TclError:
            return
        self._tip_win = None
        self._upd_win = None
        self._build_ui()
        self._log(f"界面语言：{i18n.language_display_name(i18n.get_language())}"
                  f"（{i18n.get_language()}）")
        self.refresh_all()

    def _open_settings_file(self):
        """打开设置文件；文件还不存在时退而打开它所在的目录。"""
        target = core.settings_file()
        try:
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
            self._try_open(str(target if target.exists() else target.parent))
        except Exception as e:  # noqa: BLE001
            self._log(t("⚠ 无法打开设置文件：{e}", e=e))

    def _on_gpu_toggle(self):
        """GPU 加速偏好变化时立即持久化。

        该偏好目前不影响任何行为（DSH 未提供 GPU 加速选项），
        因此日志与状态栏都明确说明，避免误以为它已经生效。
        """
        value = bool(self.var_gpu.get())
        self.settings["gpu_acceleration"] = value
        ok = core.save_settings(self.settings)
        state = t("开启") if value else t("关闭")
        if ok:
            self._log(t("偏好已保存：GPU 加速 = {state}（仅本地记录，DSH 暂无对应选项）", state=state))
            self._set_status(t("偏好已保存：GPU 加速 {state}", state=state))
        else:
            self._log(f"⚠ 偏好保存失败（{core.settings_file()} 不可写）："
                      f"GPU 加速 = {state}，本次选择仅当前会话有效")
            self._set_status(t("偏好保存失败，详见日志"))

    # ---------------- 检查更新器自身更新（右下角版本号） ----------------
    def _on_version_click(self, _evt=None):
        self.check_updater_update()

    def _close_upd_win(self):
        win, self._upd_win = self._upd_win, None
        if win is not None:
            try:
                win.destroy()
            except tk.TclError:
                pass

    def check_updater_update(self):
        """点击右下角版本号：弹出小窗口，检测本更新器自身是否有新版本。"""
        win = self._upd_win
        if win is not None:
            try:
                win.lift()
                win.focus_force()
                return
            except tk.TclError:
                self._upd_win = None

        win = tk.Toplevel(self.root)
        self._upd_win = win
        self._upd_url = core.SELF_REPO_URL
        win.title(t("检查更新 · 当前 v{APP_VERSION}", APP_VERSION=APP_VERSION))
        win.resizable(False, False)
        win.configure(bg=CLR["bg"])
        self._apply_icon(win)
        win.transient(self.root)
        win.protocol("WM_DELETE_WINDOW", self._close_upd_win)
        win.bind("<Escape>", lambda e: self._close_upd_win())

        frm = ttk.Frame(win, padding=16)
        frm.pack(fill="both", expand=True)
        tk.Label(frm, text=t("检查更新器自身更新"), anchor="w", background=CLR["bg"],
                 foreground=CLR["text"], font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w")
        tk.Label(frm, text=t("当前版本：v{APP_VERSION}", APP_VERSION=APP_VERSION), anchor="w", background=CLR["bg"],
                 foreground=CLR["text_dim"], font=("Microsoft YaHei UI", 9)).pack(
                     anchor="w", pady=(2, 10))

        self._upd_status = tk.Label(frm, text=t("正在检查 GitHub 上的最新发布…"), anchor="w",
                                    justify="left", width=52, background=CLR["bg"],
                                    foreground=CLR["text"])
        self._upd_status.pack(anchor="w")
        self._upd_detail = tk.Label(frm, text="", anchor="w", justify="left", width=52,
                                    background=CLR["bg"], foreground=CLR["text_dim"])
        self._upd_detail.pack(anchor="w", pady=(6, 0))

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(16, 0))
        self._upd_open_btn = ttk.Button(btns, text=t("打开 GitHub 页面"), state="disabled",
                                        command=lambda: self._open_url(self._upd_url))
        self._upd_open_btn.pack(side="left")
        ttk.Button(btns, text=t("关闭"), command=self._close_upd_win).pack(side="right")

        # 居中显示在主窗口上方
        win.update_idletasks()
        try:
            w, h = win.winfo_width(), win.winfo_height()
            x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
            y = self.root.winfo_rooty() + max((self.root.winfo_height() - h) // 3, 0)
            win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except tk.TclError:
            pass
        win.focus_force()

        wk = Worker(on_log=lambda _m: None, on_finish=self._on_upd_check_done)
        wk.start(core.fetch_self_latest, APP_VERSION)
        self._poll_window(wk, win)

    def _open_url(self, url: str):
        if not url:
            return
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:  # noqa: BLE001
            self._log(t("⚠ 无法打开链接：{e}", e=e))

    def _on_upd_check_done(self, result, err):
        if self._upd_win is None:
            return
        try:
            if err is not None:
                self._upd_status.configure(text=t("检查失败"), foreground=CLR["err"])
                self._upd_detail.configure(text=f"{type(err).__name__}: {err}")
                return
            result = result or {}
            if not result.get("ok"):
                self._upd_status.configure(text=t("检查失败"), foreground=CLR["err"])
                self._upd_detail.configure(text=result.get("error") or t("未知原因"))
                return

            tag = result.get("tag") or ""
            date = (result.get("date") or "")[:10]
            self._upd_url = result.get("url") or core.SELF_REPO_URL
            self._upd_open_btn.configure(state="normal")

            if result.get("has_update"):
                self._upd_status.configure(text=t("🎉 发现新版本：{tag}", tag=tag), foreground=CLR["ok"])
                lines = [t("当前 v{APP_VERSION}  →  最新 {tag}", APP_VERSION=APP_VERSION, tag=tag)]
                if date:
                    lines.append(t("发布时间：{date}", date=date))
                lines.append(t("点击左下按钮打开 GitHub 页面。"))
                self._upd_detail.configure(text="\n".join(lines))
            else:
                self._upd_status.configure(text=t("✅ 已是最新版本（v{APP_VERSION}）", APP_VERSION=APP_VERSION),
                                           foreground=CLR["ok"])
                line = t("远端最近发布：{tag}", tag=tag)
                if date:
                    line += t("（{date}）", date=date)
                if result.get("note"):
                    line += "\n\n" + result["note"]
                self._upd_detail.configure(text=line)
        except tk.TclError:
            pass

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
        head = t("◉ 版本性质：{label} {color_note}", label=label, color_note=color_note) if with_title else f"{label} {color_note}"
        if grade == "unstable":
            head += t("\n   ⚠ 未能在官网核实该版本 —— 视为【不稳定版】，请谨慎使用")
        if reason:
            head += t("\n   依据：{reason}", reason=reason)
        return head

    def _kind_tip_text(self, inst: dict) -> str:
        kind = inst["kind"]
        info = KIND_INFO.get(kind)
        if not info:
            return t("未知类型。")
        gh = (self.official or {}).get("github", {})
        npm = (self.official or {}).get("npm", {})
        local = inst.get("version") or "—"
        if kind == core.INSTALL_KIND_SOURCE:
            ref = gh.get("version") or t("获取失败")
            need = inst.get("status") == t("可更新")
        else:
            ref = npm.get("version") or t("获取失败")
            need = inst.get("status") in (t("可更新"), t("可更新(npm)"))
        recent = gh.get("recent") or []
        lines = [
            t("【{p1}】", p1=info['title']),
            "",
            t("◉ 这是什么：{p1}", p1=info['what']),
            "",
            t("◉ 在 DSH 中作用：{p1}", p1=info['role']),
            "",
            t("◉ 版本：本地 {local}   ∥   官方({p1}) {ref}", local=local, p1=info['ref'], ref=ref),
            t("◉ 是否需要立即更新：{p1}", p1=t('是，有可用更新') if need else t('否，已是最新')),
            "",
            self._stability_line(inst),
            "",
            t("◉ 更新方式：{p1}", p1=info['how']),
        ]
        if need and recent:
            lines.append("")
            lines.append(t("◉ 官方近期更新内容（最近若干提交，可作更新预期参考）："))
            for c in recent[:4]:
                lines.append(f"   · {c.get('date', '')}  {c.get('msg', '')}")
        lines.append("")
        lines.append(t("（提示：更新前请先退出正在运行的 DeepSeek Harness）"))
        return "\n".join(lines)

    def _nature_tip_text(self, inst: dict) -> str:
        ver = inst.get("version") or "—"
        return t("当前版本 {ver}\n\n{p1}", ver=ver, p1=self._stability_line(inst))

    def _status_tip_text(self, inst: dict) -> str:
        status = inst.get("status", "—")
        ver = inst.get("version") or "—"
        base = ""
        if status == t("可更新"):
            base = (f"当前版本 {ver} 落后于官方，可点击\n"
                    f"「⬇ 更新所选安装」一键升级（自动备份后替换）。")
        elif status == t("已是最新"):
            base = t("当前版本 {ver} 与官方一致，无需更新。", ver=ver)
        else:
            base = t("状态：{status}\n（版本信息：{ver}）", status=status, ver=ver)
        # 若该版本不稳定，追加醒目提示
        grade = inst.get("grade", "")
        if grade == "unstable":
            base += t("\n\n🛑 注意：该版本【不稳定版】，官网无法核实，升级请谨慎。")
        elif grade == "prerelease":
            base += t("\n\n🟣 提示：该版本为官方预发布（alpha/beta），可能存在兼容性变化。")
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
                app.toggle_theme()  # 冒烟中顺带验证深色主题切换
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
