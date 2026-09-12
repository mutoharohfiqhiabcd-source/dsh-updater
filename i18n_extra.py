# -*- coding: utf-8 -*-
"""补充翻译表：日志正文、类型说明与自测输出等长文案。

键为简体中文原文；`\n` 与 `{占位符}` 必须原样保留。
"""
from __future__ import annotations

EXTRA: dict[str, dict[str, str]] = {

    # =======================================================================
    "en": {
        "\n\n🛑 注意：该版本【不稳定版】，官网无法核实，升级请谨慎。":
            "\n\n🛑 Note: this is an [unstable] version that cannot be verified against official sources; upgrade with care.",
        "\n\n🟣 提示：该版本为官方预发布（alpha/beta），可能存在兼容性变化。":
            "\n\n🟣 Note: this is an official pre-release (alpha/beta); compatibility may change.",
        "\n   ⚠ 未能在官网核实该版本 —— 视为【不稳定版】，请谨慎使用":
            "\n   ⚠ Could not verify this version against official sources — treated as [unstable]; use with care",
        "\n[4] 插件扫描（启用 + 运行时内置，含效率统计）":
            "\n[4] Plugin scan (enabled + runtime built-ins, with timing)",
        "\n[5b] 进度回调演示（skills 前 5 项）":
            "\n[5b] Progress callback demo (first 5 skills)",
        "\n[7] 端口占用检测（DSH Web 3080）":
            "\n[7] Port check (DSH Web 3080)",
        "  {ZIP_URL}\n  HTTP {p1}  大小约 {p2}":
            "  {ZIP_URL}\n  HTTP {p1}  size approx. {p2}",
        "  （未自动发现任何安装——源码检出可用 --add 手动指定）":
            "  (No install auto-detected — source checkouts can be added manually with --add)",
        "DSH 数据目录（DSH_HOME）：\n{p1}\n\n技能目录：\n{p2}\n\n本更新器设置文件：\n{p3}\n\n提示：可通过环境变量 DSH_HOME / DSH_SKILLS 更改检测位置。":
            "DSH data folder (DSH_HOME):\n{p1}\n\nSkill folder:\n{p2}\n\nUpdater settings file:\n{p3}\n\nTip: use DSH_HOME / DSH_SKILLS to change the search locations.",
        "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理":
            "A runtime instance under DSH_HOME (default ~/.dsh/profiles/<name>), managed as a pnpm workspace",
        "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。":
            "The full open-source DeepSeek Harness project (package.json: @deepseek-ai/dsh-root).",
        "npm install -g 失败（退出码 {code}）":
            "npm install -g failed (exit code {code})",
        "npm 全局安装 · @deepseek-ai/dsh": "npm global install · @deepseek-ai/dsh",
        "pnpm install 失败（退出码 {code}）。源码已替换，请手动排查依赖。":
            "pnpm install failed (exit code {code}). Source was replaced; please resolve dependencies manually.",
        "◉ 官方近期更新内容（最近若干提交，可作更新预期参考）：":
            "◉ Recent official commits (useful for anticipating an update):",
        "◉ 版本性质：{label} {color_note}": "◉ Version nature: {label} {color_note}",
        "◉ 版本：本地 {local}   ∥   官方({p1}) {ref}":
            "◉ Version: local {local}   ∥   official({p1}) {ref}",
        "⚠ 官方最新 {ref} 为【{gl}】（预发布），可能存在兼容性变化，请按需更新。":
            "⚠ Official latest {ref} is [{gl}] (pre-release); compatibility may change — update as needed.",
        "✅ git 同步完成：成功 {okn}，失败 {p1}，跳过 {skip}（无 git 来源）":
            "✅ git sync complete: {okn} succeeded, {p1} failed, {skip} skipped (no git origin)",
        "✅ 最新版检测完成：共 {total} 项，其中 {upd} 项有可用更新":
            "✅ Latest-version check complete: {total} item(s), {upd} with updates",
        "✔ 完成（用时 {elapsed:.2f} 秒，平均 {speed:.1f} 项/秒）":
            "✔ Done (took {elapsed:.2f}s, avg {speed:.1f}/s)",
        "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n":
            "Runtime profiles do not need separate updates: they are provided by the source/CLI install.\n",
        "下载完成：{dest}（{p1}，用时 {p2:.1f} 秒）":
            "Download complete: {dest} ({p1}, took {p2:.1f}s)",
        "下载的压缩包中未找到 DeepSeek Harness 源码根目录":
            "The downloaded archive does not contain a DeepSeek Harness source root",
        "偏好已保存：GPU 加速 = {state}（仅本地记录，DSH 暂无对应选项）":
            "Preference saved: GPU acceleration = {state} (local only; DSH has no such option yet)",
        "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”":
            "Determines which plugins a given launch loads (Web / ACP / SDK profile templates); it is where plugins live at \"runtime\"",
        "官方最新 {ref} 为【{gl}】，发布候选版。":
            "Official latest {ref} is [{gl}], a release candidate.",
        "官方源码版本：{new_version}（当前：{p1}）":
            "Official source version: {new_version} (current: {p1})",
        "官方要求 Node {engines}，无法精确判定当前环境":
            "Official requirement is Node {engines}; cannot determine the current environment precisely",
        "官网信息获取失败（GitHub 与 npm 均不可用），无法核实":
            "Could not fetch official info (both GitHub and npm unavailable); cannot verify",
        "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换":
            "Compares against GitHub master; update: download official source zip → auto-backup → replace whole directory",
        "对比 npm registry 的 latest 发布版；更新方式：npm install -g @deepseek-ai/dsh@latest。":
            "Compares against the npm registry latest release; update: npm install -g @deepseek-ai/dsh@latest.",
        "当前 v{APP_VERSION}  →  最新 {tag}": "current v{APP_VERSION}  →  latest {tag}",
        "当前版本 v{APP_VERSION} · 检查更新": "v{APP_VERSION} · Check for updates",
        "执行 pnpm install（新目录中安装依赖）…":
            "Running pnpm install (installing dependencies in the new directory)…",
        "执行：npm install -g @deepseek-ai/dsh@latest":
            "Running: npm install -g @deepseek-ai/dsh@latest",
        "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、":
            "Provides the dsh command (CLI entry): init/manage profiles, run `dsh web` to start the Web UI,",
        "插件本身随 DeepSeek Harness 发布版更新。\n":
            "Plugins themselves are updated with DeepSeek Harness releases.\n",
        "无法解析已启用插件 {name}（未在 node_modules 找到）":
            "Cannot resolve enabled plugin {name} (not found in node_modules)",
        "无法访问 GitHub Releases 接口：{p1}: {e}":
            "Cannot reach the GitHub Releases API: {p1}: {e}",
        "无法访问 GitHub Tags 接口：{p1}: {e}":
            "Cannot reach the GitHub Tags API: {p1}: {e}",
        "更新完成：{p1} → {new_version}": "Update complete: {p1} → {new_version}",
        "替换后自动运行 pnpm install（推荐，用于同步依赖）":
            "Run pnpm install after replacing (recommended, keeps dependencies in sync)",
        "未找到 pnpm。已替换源码，但未安装依赖；请手动运行 pnpm install":
            "pnpm not found. Source was replaced but dependencies were not installed; run pnpm install manually",
        "未找到任何插件：请检查 DSH 数据目录是否存在，或本机是否安装了运行时插件包。\n当前搜索位置：{p1}":
            "No plugins found: check that the DSH data folder exists, or that runtime plugin packages are installed.\nSearched in: {p1}",
        "本机 Node {cur_node} 不满足官方要求 {engines}（不适配）":
            "Local Node {cur_node} does not satisfy the official requirement {engines} (incompatible)",
        "本机 Node {cur_node} 满足官方要求 {engines}":
            "Local Node {cur_node} satisfies the official requirement {engines}",
        "本身不单独更新：升级其来源（npm 全局 dsh 或源码检出）后，重启 DSH 即用新版。":
            "It is not updated on its own: update its source (npm global dsh or source checkout), then restart DSH.",
        "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n":
            "DeepSeek Harness appears to be running (http://127.0.0.1:3080 is in use).\n",
        "检测完成（最新版）：{total} 项 / 可更新 {upd} 项":
            "Latest-version check complete: {total} item(s) / {upd} updatable",
        "没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），":
            "No skills can be git-synced: all local skills are copies (no .git origin).",
        "流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n":
            "Steps: download official source zip → back up original directory (rename on same drive) → replace whole directory\n",
        "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），":
            "The main program. DSH can be started directly from this directory (e.g. running the Web UI via tsx on apps/cli/src/bin.ts),",
        "统计内置包 @deepseek-ai/{p1} 大小…":
            "Measuring size of built-in package @deepseek-ai/{p1}…",
        "解压完成：{done_files} 个文件，用时 {p1:.1f} 秒":
            "Extraction complete: {done_files} file(s), took {p1:.1f}s",
        "该版本未出现在官方发布记录（GitHub tags / npm 版本表）中，无法核实其稳定性":
            "This version does not appear in official release records (GitHub tags / npm versions); stability cannot be verified",
        "该版本未声明 Node.js 运行要求（官方 engines 缺失）":
            "This version declares no Node.js requirement (official engines missing)",
        "该目录不是 DeepSeek Harness 源码检出（package.json name 非 @deepseek-ai/dsh-root）":
            "This directory is not a DeepSeek Harness source checkout (package.json name is not @deepseek-ai/dsh-root)",
        "远端最近发布的是 {p1}，低于当前版本 {p2}；通常表示当前版本尚未发布到 GitHub。":
            "The latest upstream release is {p1}, lower than the current {p2}; this usually means the current version has not been published to GitHub yet.",
        "通过 npm 全局安装的 dsh 命令行工具包（node_modules/@deepseek-ai/dsh）。":
            "The dsh CLI package installed globally via npm (node_modules/@deepseek-ai/dsh).",
        "（提示：更新前请先退出正在运行的 DeepSeek Harness）":
            "(Tip: exit the running DeepSeek Harness before updating)",
        "🌐 官方 GitHub master：{gh_txt}": "🌐 Official GitHub master: {gh_txt}",
        "🛑 官方最新 {ref} 官网信息不足，判定为【{gl}】，请谨慎更新。":
            "🛑 Not enough official information for {ref}; judged [{gl}] — update with care.",
        "🛡 自检：发现并合并 {p1} 处重复安装（同一真实路径）":
            "🛡 Self-check: merged {p1} duplicate install(s) (same real path)",
    },

    # =======================================================================
    "zh-TW": {
        "\n\n🛑 注意：该版本【不稳定版】，官网无法核实，升级请谨慎。":
            "\n\n🛑 注意：此版本為【不穩定版】，官網無法核實，升級請謹慎。",
        "\n\n🟣 提示：该版本为官方预发布（alpha/beta），可能存在兼容性变化。":
            "\n\n🟣 提示：此版本為官方預發佈（alpha/beta），可能存在相容性變化。",
        "\n   ⚠ 未能在官网核实该版本 —— 视为【不稳定版】，请谨慎使用":
            "\n   ⚠ 未能在官網核實此版本 —— 視為【不穩定版】，請謹慎使用",
        "\n[4] 插件扫描（启用 + 运行时内置，含效率统计）":
            "\n[4] 外掛掃描（啟用 + 執行階段內建，含效率統計）",
        "\n[5b] 进度回调演示（skills 前 5 项）":
            "\n[5b] 進度回呼示範（skills 前 5 項）",
        "\n[7] 端口占用检测（DSH Web 3080）":
            "\n[7] 連接埠佔用偵測（DSH Web 3080）",
        "  {ZIP_URL}\n  HTTP {p1}  大小约 {p2}":
            "  {ZIP_URL}\n  HTTP {p1}  大小約 {p2}",
        "  （未自动发现任何安装——源码检出可用 --add 手动指定）":
            "  （未自動發現任何安裝——原始碼檢查可用 --add 手動指定）",
        "DSH 数据目录（DSH_HOME）：\n{p1}\n\n技能目录：\n{p2}\n\n本更新器设置文件：\n{p3}\n\n提示：可通过环境变量 DSH_HOME / DSH_SKILLS 更改检测位置。":
            "DSH 資料目錄（DSH_HOME）：\n{p1}\n\n技能目錄：\n{p2}\n\n本更新器設定檔：\n{p3}\n\n提示：可透過環境變數 DSH_HOME / DSH_SKILLS 變更偵測位置。",
        "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理":
            "DSH_HOME（預設 ~/.dsh/profiles/<name>）下的執行實例，以 pnpm workspace 形態管理",
        "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。":
            "DeepSeek Harness 的完整開源原始碼專案（package.json: @deepseek-ai/dsh-root）。",
        "npm install -g 失败（退出码 {code}）":
            "npm install -g 失敗（退出碼 {code}）",
        "npm 全局安装 · @deepseek-ai/dsh": "npm 全域安裝・@deepseek-ai/dsh",
        "pnpm install 失败（退出码 {code}）。源码已替换，请手动排查依赖。":
            "pnpm install 失敗（退出碼 {code}）。原始碼已取代，請手動排查相依套件。",
        "◉ 官方近期更新内容（最近若干提交，可作更新预期参考）：":
            "◉ 官方近期更新內容（最近若干提交，可作更新預期參考）：",
        "◉ 版本性质：{label} {color_note}": "◉ 版本性質：{label} {color_note}",
        "◉ 版本：本地 {local}   ∥   官方({p1}) {ref}":
            "◉ 版本：本機 {local}   ∥   官方({p1}) {ref}",
        "⚠ 官方最新 {ref} 为【{gl}】（预发布），可能存在兼容性变化，请按需更新。":
            "⚠ 官方最新 {ref} 為【{gl}】（預發佈），可能存在相容性變化，請視需求更新。",
        "✅ git 同步完成：成功 {okn}，失败 {p1}，跳过 {skip}（无 git 来源）":
            "✅ git 同步完成：成功 {okn}，失敗 {p1}，略過 {skip}（無 git 來源）",
        "✅ 最新版检测完成：共 {total} 项，其中 {upd} 项有可用更新":
            "✅ 最新版偵測完成：共 {total} 項，其中 {upd} 項有可用更新",
        "✔ 完成（用时 {elapsed:.2f} 秒，平均 {speed:.1f} 项/秒）":
            "✔ 完成（耗時 {elapsed:.2f} 秒，平均 {speed:.1f} 項/秒）",
        "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n":
            "「執行階段 profile」無需單獨更新：它由原始碼／CLI 安裝提供。\n",
        "下载完成：{dest}（{p1}，用时 {p2:.1f} 秒）":
            "下載完成：{dest}（{p1}，耗時 {p2:.1f} 秒）",
        "下载的压缩包中未找到 DeepSeek Harness 源码根目录":
            "下載的壓縮檔中找不到 DeepSeek Harness 原始碼根目錄",
        "偏好已保存：GPU 加速 = {state}（仅本地记录，DSH 暂无对应选项）":
            "偏好已儲存：GPU 加速 = {state}（僅本機記錄，DSH 尚無對應選項）",
        "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”":
            "決定某次啟動載入哪些外掛（Web / ACP / SDK 等 profile 範本），是外掛在「執行階段」",
        "官方最新 {ref} 为【{gl}】，发布候选版。":
            "官方最新 {ref} 為【{gl}】，發佈候選版。",
        "官方源码版本：{new_version}（当前：{p1}）":
            "官方原始碼版本：{new_version}（目前：{p1}）",
        "官方要求 Node {engines}，无法精确判定当前环境":
            "官方要求 Node {engines}，無法精確判定目前環境",
        "官网信息获取失败（GitHub 与 npm 均不可用），无法核实":
            "官網資訊取得失敗（GitHub 與 npm 均無法使用），無法核實",
        "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换":
            "比對 GitHub master 原始碼；更新方式：下載官方原始碼 zip → 自動備份原目錄 → 整目錄取代",
        "对比 npm registry 的 latest 发布版；更新方式：npm install -g @deepseek-ai/dsh@latest。":
            "比對 npm registry 的 latest 發行版；更新方式：npm install -g @deepseek-ai/dsh@latest。",
        "当前 v{APP_VERSION}  →  最新 {tag}": "目前 v{APP_VERSION}  →  最新 {tag}",
        "当前版本 v{APP_VERSION} · 检查更新": "目前版本 v{APP_VERSION}・檢查更新",
        "执行 pnpm install（新目录中安装依赖）…":
            "執行 pnpm install（在新目錄中安裝相依套件）…",
        "执行：npm install -g @deepseek-ai/dsh@latest":
            "執行：npm install -g @deepseek-ai/dsh@latest",
        "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、":
            "提供 dsh 命令（CLI 入口）：初始化／管理 profile、執行 `dsh web` 啟動 Web UI、",
        "插件本身随 DeepSeek Harness 发布版更新。\n":
            "外掛本身隨 DeepSeek Harness 發行版更新。\n",
        "无法解析已启用插件 {name}（未在 node_modules 找到）":
            "無法解析已啟用外掛 {name}（未在 node_modules 找到）",
        "无法访问 GitHub Releases 接口：{p1}: {e}":
            "無法存取 GitHub Releases 介面：{p1}: {e}",
        "无法访问 GitHub Tags 接口：{p1}: {e}":
            "無法存取 GitHub Tags 介面：{p1}: {e}",
        "更新完成：{p1} → {new_version}": "更新完成：{p1} → {new_version}",
        "替换后自动运行 pnpm install（推荐，用于同步依赖）":
            "取代後自動執行 pnpm install（建議，用於同步相依套件）",
        "未找到 pnpm。已替换源码，但未安装依赖；请手动运行 pnpm install":
            "找不到 pnpm。原始碼已取代，但未安裝相依套件；請手動執行 pnpm install",
        "未找到任何插件：请检查 DSH 数据目录是否存在，或本机是否安装了运行时插件包。\n当前搜索位置：{p1}":
            "找不到任何外掛：請檢查 DSH 資料目錄是否存在，或本機是否安裝了執行階段外掛套件。\n目前搜尋位置：{p1}",
        "本机 Node {cur_node} 不满足官方要求 {engines}（不适配）":
            "本機 Node {cur_node} 不符合官方要求 {engines}（不相容）",
        "本机 Node {cur_node} 满足官方要求 {engines}":
            "本機 Node {cur_node} 符合官方要求 {engines}",
        "本身不单独更新：升级其来源（npm 全局 dsh 或源码检出）后，重启 DSH 即用新版。":
            "本身不單獨更新：升級其來源（npm 全域 dsh 或原始碼檢查）後，重新啟動 DSH 即使用新版。",
        "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n":
            "偵測到 DeepSeek Harness 正在執行（http://127.0.0.1:3080 被佔用）。\n",
        "检测完成（最新版）：{total} 项 / 可更新 {upd} 项":
            "偵測完成（最新版）：{total} 項／可更新 {upd} 項",
        "没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），":
            "沒有可 git 同步的技能：本機技能均為複製安裝（無 .git 來源），",
        "流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n":
            "流程：下載官方原始碼 zip → 備份原目錄（同磁碟改名）→ 整目錄取代\n",
        "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），":
            "程式主體。可從此目錄直接啟動 DSH（例如以 tsx 執行 apps/cli/src/bin.ts 的 Web UI），",
        "统计内置包 @deepseek-ai/{p1} 大小…":
            "統計內建套件 @deepseek-ai/{p1} 大小…",
        "解压完成：{done_files} 个文件，用时 {p1:.1f} 秒":
            "解壓縮完成：{done_files} 個檔案，耗時 {p1:.1f} 秒",
        "该版本未出现在官方发布记录（GitHub tags / npm 版本表）中，无法核实其稳定性":
            "此版本未出現在官方發佈記錄（GitHub tags / npm 版本表）中，無法核實其穩定性",
        "该版本未声明 Node.js 运行要求（官方 engines 缺失）":
            "此版本未宣告 Node.js 執行需求（缺少官方 engines）",
        "该目录不是 DeepSeek Harness 源码检出（package.json name 非 @deepseek-ai/dsh-root）":
            "此目錄不是 DeepSeek Harness 原始碼檢查（package.json name 非 @deepseek-ai/dsh-root）",
        "远端最近发布的是 {p1}，低于当前版本 {p2}；通常表示当前版本尚未发布到 GitHub。":
            "遠端最近發佈的是 {p1}，低於目前版本 {p2}；通常表示目前版本尚未發佈到 GitHub。",
        "通过 npm 全局安装的 dsh 命令行工具包（node_modules/@deepseek-ai/dsh）。":
            "透過 npm 全域安裝的 dsh 命令列工具套件（node_modules/@deepseek-ai/dsh）。",
        "（提示：更新前请先退出正在运行的 DeepSeek Harness）":
            "（提示：更新前請先結束正在執行的 DeepSeek Harness）",
        "🌐 官方 GitHub master：{gh_txt}": "🌐 官方 GitHub master：{gh_txt}",
        "🛑 官方最新 {ref} 官网信息不足，判定为【{gl}】，请谨慎更新。":
            "🛑 官方最新 {ref} 官網資訊不足，判定為【{gl}】，請謹慎更新。",
        "🛡 自检：发现并合并 {p1} 处重复安装（同一真实路径）":
            "🛡 自檢：發現並合併 {p1} 處重複安裝（同一真實路徑）",
    },
}
