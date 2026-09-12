# -*- coding: utf-8 -*-
"""多语言翻译数据。

键 = 简体中文原文（见 i18n.py 的说明）。本文件按语言分批 `update()`，
便于增量补齐：缺翻译的键会自动回退中文，不会出现空白。

约定：
  * `{p1}` / `{name}` 等占位符必须原样保留在译文里；
  * 译者可调整占位符顺序，但不能改名；
  * 纯符号键（如 "、"）按其在句子中的连接作用翻译。
"""
from __future__ import annotations

TABLES: dict[str, dict[str, str]] = {"zh-TW": {}, "en": {}, "ja": {}, "ko": {}}


# ---------------------------------------------------------------------------
# English
# ---------------------------------------------------------------------------
TABLES["en"].update({
    # 安装类型与头部
    "源码检出": "Source checkout",
    "源码检出 · Source Checkout": "Source checkout",
    "npm 全局": "npm global",
    "运行时 profile": "Runtime profile",
    "运行时 Profile · 插件装载实例": "Runtime profile (plugin host)",
    "正在自动检测本机安装与官方版本…": "Detecting local installs and official versions…",
    "🌙 深色模式": "🌙 Dark mode",
    "☀️ 浅色模式": "☀️ Light mode",
    "已切换到{p1}主题。": "Switched to {p1} theme.",
    "深色": "dark",
    "浅色": "light",
    "就绪": "Ready",
    "DeepSeek Harness 更新器": "DeepSeek Harness Updater",
    "🌐 官方 GitHub master：检测中…": "🌐 Official GitHub master: checking…",
    "📦 npm 发布版：检测中…": "📦 npm release: checking…",
    # 列表表头
    "类型": "Type",
    "位置": "Location",
    "当前版本": "Current version",
    "版本性质": "Nature",
    "官方参考版本": "Official version",
    "状态": "Status",
    # 主按钮
    "⬇ 更新所选安装": "⬇ Update selected",
    "🧩 插件检测": "🧩 Plugin scan",
    "📚 技能检测": "📚 Skill scan",
    "🔄 重新检测": "🔄 Rescan",
    "⚙ 数据目录": "⚙ Data folder",
    "💾 导出 CSV": "💾 Export CSV",
    # 偏好设置
    "⚙ 偏好设置": "⚙ Preferences",
    "语言": "Language",
    "跟随系统": "Follow system",
    "使用 GPU 加速": "Use GPU acceleration",
    "📂 打开设置文件": "📂 Open settings file",
    # 进度区
    "当前任务": "Current task",
    "等待任务…": "Idle…",
    "日志 / 进度": "Log / Progress",
    "准备中…": "Preparing…",
    "进度：{p1:.1f}%": "Progress: {p1:.1f}%",
    "正在检测本机安装与官方版本…": "Detecting local installs and official versions…",
    "\n── 开始检测 ──": "\n── Detection started ──",
    # 检测与状态
    "检测失败：\n{err}": "Detection failed:\n{err}",
    "检测失败": "Detection failed",
    "获取失败": "Fetch failed",
    "（{p1}）": "（{p1}）",
    "〔{p1}〕": "[{p1}]",
    "📦 npm 发布版：{npm_txt}": "📦 npm release: {npm_txt}",
    "    └ 稳定性判定：{p1}": "    └ Stability: {p1}",
    "检测完成：发现 {p1} 处安装": "Detection complete: {p1} install(s) found",
    "（自检合并重复 {p1} 处）": "({p1} duplicate(s) merged by self-check)",
    "未自动发现安装，可使用界面按钮或自行检查路径。":
        "No install detected automatically. Use the buttons above or check paths manually.",
    "可更新": "Update available",
    "已是最新": "Up to date",
    "失败": "Failed",
    "请先在列表中选中一行安装。": "Select an install row in the list first.",
    # npm 更新
    "正在通过 npm 更新全局安装…": "Updating npm global install…",
    "npm 更新失败：\n{err}": "npm update failed:\n{err}",
    "npm 更新失败": "npm update failed",
    "npm 更新完成": "npm update complete",
    # 源码更新确认
    "更新源码检出": "Update source checkout",
    "将更新源码检出：": "About to update source checkout:",
    "当前版本：{cur}    官方最新：{ref}": "Current: {cur}    Official latest: {ref}",
    "官方最新 {ref} 为【{gl}】。": "Official latest {ref} is [{gl}].",
    "适配性：{p1}": "Compatibility: {p1}",
    "开始更新": "Start update",
    "取消": "Cancel",
    "正在下载并替换源码…": "Downloading and replacing source…",
    "准备下载官方源码…": "Preparing to download official source…",
    "更新进度：{p1:.1f}%": "Update progress: {p1:.1f}%",
    "更新失败：\n{err}": "Update failed:\n{err}",
    "更新失败": "Update failed",
    "更新完成": "Update complete",
    "\n\n原目录备份于：\n{p1}": "\n\nOriginal directory backed up at:\n{p1}",
    # 插件窗口
    "插件": "Plugin",
    "🧩 DeepSeek Harness 插件检测": "🧩 DeepSeek Harness Plugin Scan",
    "暗绿主题": "dark green theme",
    "名称": "Name",
    "版本": "Version",
    "大小": "Size",
    "安装时间": "Installed",
    "最新版": "Latest",
    "启用": "Enabled",
    "来源": "Source",
    "✔ 启用": "✔ Enabled",
    "内置": "Built-in",
    "⬇ 同步更新": "⬇ Sync update",
    # 技能窗口
    "技能": "Skill",
    "📚 DeepSeek Harness 技能检测": "📚 DeepSeek Harness Skill Scan",
    "暗紫主题": "dark purple theme",
    "⬇ git 同步更新": "⬇ git sync update",
    "正在扫描…": "Scanning…",
    "🔍 检测最新版": "🔍 Check latest",
    "↻ 重新扫描": "↻ Rescan",
    # 扫描进度与状态
    "{speed:.0f} 项/秒": "{speed:.0f}/s",
    "即将完成": "Almost done",
    "计算中…": "calculating…",
    "进度刷新异常（扫描继续）：{e}": "Progress refresh error (scan continues): {e}",
    "扫描出错": "Scan error",
    "✖ 扫描异常": "✖ Scan error",
    "扫描异常 — 未获得结果": "Scan error — no result",
    "✖ [{name}检测] 扫描失败：{err}": "✖ [{name} scan] failed: {err}",
    "✔ 完成": "✔ Done",
    "填表时遇到异常，已显示部分结果": "Error while filling table; partial results shown",
    "⚠ 列表渲染异常：{e}": "⚠ List render error: {e}",
    "扫描目录：{root}": "Scanning directory: {root}",
    "扫描完成": "Scan complete",
    "共 {p1} 项    合计 {p2}": "{p1} item(s)    total {p2}",
    "    用时 {elapsed:.2f} 秒": "    took {elapsed:.2f}s",
    "    平均 {speed:.1f} 项/秒": "    avg {speed:.1f}/s",
    "    双击行可打开所在路径": "    Double-click a row to open its folder",
    "；": "; ",
    "（未指定）": "(not specified)",
    "正在检测 {p1} 项的最新版本（联网查询）…": "Checking latest version for {p1} item(s) (online)…",
    "检测最新版失败：{err}": "Latest-version check failed: {err}",
    "（技能若无 git 来源则无法检测）": "(skills without a git origin cannot be checked)",
    "。可在主窗口对源码检出/npm 全局执行更新。":
        ". Use the main window to update the source checkout / npm global.",
    "正在 git 同步 {p1} 个技能…": "git-syncing {p1} skill(s)…",
    "同步失败：{err}": "Sync failed: {err}",
    "⚠ 扫描轮询异常（继续等待）：{e}": "⚠ Scan polling error (still waiting): {e}",
    "扫描失败：{e}": "Scan failed: {e}",
    "大小(字节)": "Size (bytes)",
    "路径": "Path",
    "是": "Yes",
    "已导出：\n": "Exported:\n",
    # 偏好与设置
    "⚠ 语言偏好保存失败，本次运行仍会生效":
        "⚠ Failed to save language preference; it still applies to this run",
    "⚠ 无法打开设置文件：{e}": "⚠ Cannot open settings file: {e}",
    "开启": "on",
    "关闭": "off",
    "偏好已保存：GPU 加速 {state}": "Preference saved: GPU acceleration {state}",
    "偏好保存失败，详见日志": "Failed to save preference; see log",
    # 检查更新器自身
    "检查更新 · 当前 v{APP_VERSION}": "Check for updates · current v{APP_VERSION}",
    "检查更新器自身更新": "Check for updater updates",
    "当前版本：v{APP_VERSION}": "Current version: v{APP_VERSION}",
    "正在检查 GitHub 上的最新发布…": "Checking the latest release on GitHub…",
    "打开 GitHub 页面": "Open GitHub page",
    "⚠ 无法打开链接：{e}": "⚠ Cannot open link: {e}",
    "检查失败": "Check failed",
    "未知原因": "unknown reason",
    "🎉 发现新版本：{tag}": "🎉 New version available: {tag}",
    "发布时间：{date}": "Published: {date}",
    "点击左下按钮打开 GitHub 页面。": "Click the button at bottom-left to open the GitHub page.",
    "✅ 已是最新版本（v{APP_VERSION}）": "✅ Up to date (v{APP_VERSION})",
    "远端最近发布：{tag}": "Latest upstream release: {tag}",
    "（{date}）": "({date})",
    "\n   依据：{reason}": "\n   Reason: {reason}",
    # 类型说明浮窗
    "未知类型。": "Unknown type.",
    "可更新(npm)": "Update available (npm)",
    "【{p1}】": "[{p1}]",
    "◉ 这是什么：{p1}": "◉ What it is: {p1}",
    "◉ 在 DSH 中作用：{p1}": "◉ Role in DSH: {p1}",
    "◉ 是否需要立即更新：{p1}": "◉ Update now? {p1}",
    "是，有可用更新": "Yes, an update is available",
    "否，已是最新": "No, already up to date",
    "◉ 更新方式：{p1}": "◉ How to update: {p1}",
    "当前版本 {ver}\n\n{p1}": "Current version {ver}\n\n{p1}",
    "当前版本 {ver} 与官方一致，无需更新。":
        "Current version {ver} matches the official release; no update needed.",
    # 稳定性分级
    "稳定版": "Stable",
    "候选版 rc": "Release candidate",
    "预发布 alpha": "Pre-release (alpha)",
    "不稳定版": "Unstable",
    "版本号为空，官网无法核实": "Version is empty; cannot verify against official sources",
    "无法评估": "Cannot assess",
    "与官方最新发布版（npm latest）一致": "Matches the official npm latest release",
    "官方发布记录中存在该版本（预发布/候选版本）":
        "This version exists in the official release records (pre-release/candidate)",
    "远端没有可用的 Release 或 Tag。": "No usable Release or Tag upstream.",
    # 其余零散文案
    "运行时 profile ({p1})": "Runtime profile ({p1})",
    "已合并 %d 处指向同一真实路径的重复安装：%s":
        "Merged %d duplicate install(s) pointing to the same real path: %s",
    "、": ", ",
    "无法读取版本": "Cannot read version",
    "官方版本获取失败": "Failed to fetch official version",
    "准备就绪，开始枚举插件目录…": "Ready; enumerating plugin directories…",
    "解析启用插件 {name}": "Resolving enabled plugin {name}",
    "运行时内置": "Built-in (runtime)",
    "技能目录不存在: ": "Skill directory does not exist: ",
    "未发现技能目录…": "No skill directory found…",
    "统计技能 {name} 文件与大小…": "Measuring files and size for skill {name}…",
    "读取技能 {name}": "Reading skill {name}",
    "查询 {name} 最新版…": "Querying latest version of {name}…",
    "npm 无该包": "Package not found on npm",
    "检查技能 {name} 来源…": "Checking origin of skill {name}…",
    "远端无版本 tag": "No version tag upstream",
    "git ls-remote 失败": "git ls-remote failed",
    "本地副本（无 git 来源，无法自动检测）":
        "Local copy (no git origin; cannot auto-check)",
    "更新技能 {p1}…": "Updating skill {p1}…",
    "  ✔ {p1} 已更新": "  ✔ {p1} updated",
    "{seconds:.0f} 秒": "{seconds:.0f} s",
    "{p1} 分 {p2} 秒": "{p1} min {p2} s",
    "开始下载：{url}": "Downloading: {url}",
    "[下载] {p1}": "[download] {p1}",
    "解压跳过异常文件 {p1}: {e}": "Skipped malformed entry {p1}: {e}",
    "解压中：{p1}": "Extracting: {p1}",
    "目标目录不存在：{target_dir}": "Target directory does not exist: {target_dir}",
    "未知": "unknown",
    "备份原目录 → {backup_dir}": "Backing up original directory → {backup_dir}",
    "备份完成（原目录已改名）": "Backup complete (original directory renamed)",
    "写入官方源码 → {target_dir}": "Writing official source → {target_dir}",
    "保留 {k}（移回新目录）…": "Preserving {k} (moving back into new directory)…",
    "新源码就位。": "New source is in place.",
    "替换失败，回滚中：{e}": "Replacement failed, rolling back: {e}",
    "更新失败，已回滚：{e}": "Update failed and was rolled back: {e}",
    "旧版本": "old",
    "未找到 npm，无法执行全局更新": "npm not found; cannot perform global update",
    "npm 全局更新完成，版本：{p1}": "npm global update complete, version: {p1}",
    # 自测输出
    "DeepSeek Harness 更新器核心自测": "DeepSeek Harness Updater core self-test",
    "\n[1] 检测本机安装": "\n[1] Detect local installs",
    "\n[2] 官方版本": "\n[2] Official versions",
    "\n[3] 版本比较": "\n[3] Version comparison",
    "  … 其余 {p1} 项": "  … {p1} more item(s)",
    "\n[5] 技能扫描（含效率统计）": "\n[5] Skill scan (with timing)",
    "  技能目录：{p1}": "  Skill directory: {p1}",
    "\n[6] zip 可达性（仅探测，不下载）": "\n[6] zip reachability (probe only, no download)",
    "  探测失败：{e}": "  Probe failed: {e}",
    "  3080 监听中：{p1}": "  Port 3080 listening: {p1}",
    "\n自测结束。": "\nSelf-test finished.",
})


TABLES["en"].update({
    "状态：{status}\n（版本信息：{ver}）":
        "Status: {status}\n (version: {ver})",
})


# ---------------------------------------------------------------------------
# 各语言拆分到独立文件，便于增量补齐与单独审阅
# ---------------------------------------------------------------------------
from i18n_zh_tw import TABLE as _TABLE_ZH_TW

TABLES["zh-TW"].update(_TABLE_ZH_TW)
from i18n_ja import TABLE as _TABLE_JA

TABLES["ja"].update(_TABLE_JA)
from i18n_ko import TABLE as _TABLE_KO

TABLES["ko"].update(_TABLE_KO)
