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

        self._build_ui()
        self._log(f"{APP_TITLE} 已启动。\nDSH 数据目录：{core.DSH_HOME}")
        self._log("正在自动检测本机安装与官方版本…")
        self.refresh_all()

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 4}

        # ── 顶部：标题与官方版本条 ──
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=(10, 2))
        ttk.Label(top, text="DeepSeek Harness", font=("Microsoft YaHei UI", 16, "bold")).pack(side="left")
        ttk.Label(top, text="自动检测 · 版本对比 · 插件/技能扫描 · 一键更新",
                  foreground="#555").pack(side="left", padx=12)

        self.lbl_github = ttk.Label(top, text="官方 GitHub：检测中…", foreground="#0a58ca")
        self.lbl_github.pack(side="right", padx=6)
        self.lbl_npm = ttk.Label(top, text="npm：检测中…", foreground="#7a4a0b")
        self.lbl_npm.pack(side="right")

        # ── 中部：安装列表 ──
        mid = ttk.LabelFrame(self.root, text="本机检测到的 DeepSeek Harness 安装")
        mid.pack(fill="both", expand=False, padx=10, pady=6)
        cols = ("kind", "path", "version", "ref", "status")
        heads = {"kind": "类型", "path": "位置", "version": "当前版本",
                 "ref": "官方参考版本", "status": "状态"}
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=7)
        for c in cols:
            self.tree.heading(c, text=heads[c])
        widths = {"kind": 130, "path": 430, "version": 120, "ref": 130, "status": 110}
        for c in cols:
            self.tree.column(c, width=widths[c], anchor="w")
        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        vsb.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self.tree.bind("<Double-1>", self._on_row_double)

        # ── 操作按钮区 ──
        btns = ttk.Frame(self.root)
        btns.pack(fill="x", padx=10, pady=4)
        self.btn_refresh = ttk.Button(btns, text="🔄 重新检测", command=self.refresh_all)
        self.btn_refresh.pack(side="left")
        self.btn_update = ttk.Button(btns, text="⬇ 更新所选安装", command=self.update_selected)
        self.btn_update.pack(side="left", padx=8)
        self.btn_plugins = ttk.Button(btns, text="🧩 插件检测", command=self.open_plugins)
        self.btn_plugins.pack(side="left", padx=(8, 0))
        self.btn_skills = ttk.Button(btns, text="📚 技能检测", command=self.open_skills)
        self.btn_skills.pack(side="left", padx=8)
        self.btn_export = ttk.Button(btns, text="💾 导出插件/技能 CSV", command=self.export_csv)
        self.btn_export.pack(side="right")
        self.btn_settings = ttk.Button(btns, text="⚙ 数据目录", command=self.show_settings)
        self.btn_settings.pack(side="right", padx=8)

        # ── 当前操作进度横幅（扫描/下载/更新通用） ──
        progframe = ttk.Frame(self.root)
        progframe.pack(fill="x", padx=10, pady=(2, 0))
        self.prog = ttk.Progressbar(progframe, mode="determinate", maximum=1000)
        self.prog.pack(side="left", fill="x", expand=True)
        self.lbl_progress = ttk.Label(progframe, text="等待任务…", width=58, anchor="e")
        self.lbl_progress.pack(side="right", padx=(8, 0))

        # ── 日志区 ──
        logframe = ttk.LabelFrame(self.root, text="日志 / 进度")
        logframe.pack(fill="both", expand=True, padx=10, pady=6)
        self.txt = tk.Text(logframe, height=10, wrap="word", state="disabled",
                           font=("Consolas", 9), background="#111318", foreground="#d8dee9")
        logvsb = ttk.Scrollbar(logframe, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=logvsb.set)
        self.txt.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        logvsb.pack(side="right", fill="y", padx=(0, 6), pady=6)

        # 底部状态栏
        self.status = ttk.Label(self.root, text="就绪", relief="sunken", anchor="w")
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
        self.lbl_github.configure(text=f"官方 GitHub master：{gh_txt}")
        self.lbl_npm.configure(text=f"npm 发布版：{npm_txt}")

        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.install_rows = []
        for inst in result["installs"]:
            ref = gh.get("version") or "" if inst["kind"] == core.INSTALL_KIND_SOURCE else (npm.get("version") or "")
            row = (inst["kind_label"], inst["path"], inst["version"] or "—",
                   ref or "—", inst.get("status", "—"))
            iid = self.tree.insert("", "end", values=row)
            self.install_rows.append({"iid": iid, "data": inst})
            self._log(
                f"[{inst['kind_label']}] {inst['path']}\n"
                f"    当前 {inst['version'] or '—'} / 官方 {ref or '—'} / {inst.get('status', '—')}"
            )
        self._set_status(f"检测完成：发现 {len(result['installs'])} 处安装")
        if not result["installs"]:
            self._log("未自动发现安装，可使用界面按钮或自行检查路径。")

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
        ttk.Label(
            frm,
            text="流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n"
                 "（node_modules / .git 会自动移回新目录，以加快依赖安装）\n"
                 "更新期间请勿关闭本程序；若 DSH Web (3080) 正在运行将中止更新。",
            foreground="#a00", wraplength=560,
        ).grid(row=3, column=0, sticky="w", pady=6)
        self.var_pnpm = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frm, text="替换后自动运行 pnpm install（推荐，用于同步依赖）",
            variable=self.var_pnpm,
        ).grid(row=4, column=0, sticky="w", pady=4)
        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, sticky="e", pady=(10, 0))
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
            columns=(("name", "名称"), ("version", "版本"), ("size", "大小"),
                     ("enabled", "启用"), ("source", "来源")),
            widths=(340, 110, 100, 60, 130),
            scan_fn=core.scan_plugins,
            scan_kwargs={},
            row_of=lambda it: (it["name"], it["version"] or "—", it["size_text"],
                               "✔" if it["enabled"] else "—", it["source"]),
            detail_of=lambda it: it["path"],
        )

    def open_skills(self):
        self._open_inventory_window(
            name="技能",
            title="📚 DeepSeek Harness 技能检测",
            columns=(("name", "名称"), ("version", "版本"), ("size", "大小")),
            widths=(330, 110, 110),
            scan_fn=core.scan_skills,
            scan_kwargs={},
            row_of=lambda it: (it["name"], it["version"] or "—", it["size_text"]),
            detail_of=lambda it: it["path"],
        )

    def _open_inventory_window(self, name, title, columns, widths, scan_fn, scan_kwargs,
                               row_of, detail_of):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("920x600")
        win.transient(self.root)

        # ── 顶部：标题 + 进度条 + 效率标签 ──
        head = ttk.Frame(win)
        head.pack(fill="x", padx=10, pady=(8, 0))
        lbl = ttk.Label(head, text="正在扫描…", foreground="#0a58ca")
        lbl.pack(anchor="w")
        bar = ttk.Progressbar(head, mode="determinate", maximum=1000)
        bar.pack(fill="x", pady=(4, 2))
        lbl_prog = ttk.Label(head, text="", foreground="#333")
        lbl_prog.pack(anchor="w")

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

        status = ttk.Label(win, text="", relief="sunken", anchor="w")
        status.pack(fill="x", side="bottom")

        state = {"last_log_pct": -1}

        def on_progress(rep: dict):
            """rep: {phase,done,total,current,elapsed} —— 每处理完一项回调。"""
            try:
                done = rep.get("done", 0)
                total = rep.get("total", 0) or 1
                elapsed = rep.get("elapsed", 0.0)
                current = rep.get("current", "") or ""
                pct = done / total
                bar.configure(value=int(pct * 1000))
                speed = (done / elapsed) if elapsed > 0.05 else float("nan")
                if speed == speed:  # 非 NaN
                    remain = (total - done) / speed if speed > 0 else 0.0
                    speed_txt = f"{speed:.0f} 项/秒"
                    eta_txt = core._fmt_eta(remain) if remain > 0 else "即将完成"
                else:
                    speed_txt, eta_txt = "计算中…", "计算中…"
                lbl_prog.configure(
                    text=f"已检测 {done}/{total} 项（{pct * 100:.1f}%）｜当前：{current or '—'}"
                         f"｜{speed_txt}｜已用 {elapsed:.1f} 秒｜预计还需 {eta_txt}"
                )
                # 主窗口日志按 10% 一档汇报（避免刷屏）
                mark = int(pct * 100 / 10)
                if mark > state["last_log_pct"]:
                    state["last_log_pct"] = mark
                    self._log(f"📊 [{name}检测] 进度 {pct * 100:.0f}%"
                              f"（{done}/{total}）｜{speed_txt}｜已用 {elapsed:.1f}s")
            except tk.TclError:
                pass  # 窗口已关闭

        def fill(result):
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
            for it in items:
                iid = tree.insert("", "end", values=row_of(it))
                tree._item_map[iid] = it  # type: ignore[attr-defined]
            root = result.get("root")
            errs = result.get("errors") or []
            if root:
                lbl.configure(text=f"扫描目录：{root}")
            else:
                lbl.configure(text="扫描完成")
            if errs:
                lbl.configure(text=(lbl.cget("text") + "    ⚠ 部分项解析失败，见列表空白行"))
            total_size = sum(it.get("size", 0) for it in items)
            eff = f"共 {len(items)} 项    合计 {core.human_size(total_size)}"
            if elapsed:
                eff += f"    用时 {elapsed:.2f} 秒"
            if speed:
                eff += f"    平均 {speed:.1f} 项/秒"
            eff += "    双击行可打开所在路径"
            status.configure(text=eff)
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

    def _poll_window(self, worker: Worker, win: tk.Toplevel):
        try:
            if worker.pump():
                return
        except tk.TclError:
            return  # 窗口已关闭
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
        # 重扫一次并导出两份 CSV 到程序目录
        import csv
        base = Path(__file__).resolve().parent
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
