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


EXTRA["ja"] = {
    "\n\n🛑 注意：该版本【不稳定版】，官网无法核实，升级请谨慎。":
        "\n\n🛑 注意：これは【不安定版】で公式情報と照合できません。アップグレードは慎重に。",
    "\n\n🟣 提示：该版本为官方预发布（alpha/beta），可能存在兼容性变化。":
        "\n\n🟣 ヒント：これは公式のプレリリース（alpha/beta）です。互換性が変わる可能性があります。",
    "\n   ⚠ 未能在官网核实该版本 —— 视为【不稳定版】，请谨慎使用":
        "\n   ⚠ このバージョンは公式情報と照合できません —— 【不安定版】として扱います。注意して使用してください",
    "\n[4] 插件扫描（启用 + 运行时内置，含效率统计）":
        "\n[4] プラグインスキャン（有効 + ランタイム組み込み、所要時間付き）",
    "\n[5b] 进度回调演示（skills 前 5 项）":
        "\n[5b] 進捗コールバックのデモ（skills 先頭 5 件）",
    "\n[7] 端口占用检测（DSH Web 3080）":
        "\n[7] ポート使用状況の確認（DSH Web 3080）",
    "  {ZIP_URL}\n  HTTP {p1}  大小约 {p2}":
        "  {ZIP_URL}\n  HTTP {p1}  サイズ約 {p2}",
    "  （未自动发现任何安装——源码检出可用 --add 手动指定）":
        "  （インストールを自動検出できませんでした——ソースチェックアウトは --add で手動指定できます）",
    "DSH 数据目录（DSH_HOME）：\n{p1}\n\n技能目录：\n{p2}\n\n本更新器设置文件：\n{p3}\n\n提示：可通过环境变量 DSH_HOME / DSH_SKILLS 更改检测位置。":
        "DSH データフォルダ（DSH_HOME）：\n{p1}\n\nスキルフォルダ：\n{p2}\n\nアップデーター設定ファイル：\n{p3}\n\nヒント：環境変数 DSH_HOME / DSH_SKILLS で検出位置を変更できます。",
    "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理":
        "DSH_HOME（既定 ~/.dsh/profiles/<name>）配下の実行インスタンス。pnpm workspace として管理されます",
    "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。":
        "DeepSeek Harness の完全なオープンソースプロジェクト（package.json: @deepseek-ai/dsh-root）。",
    "npm install -g 失败（退出码 {code}）":
        "npm install -g が失敗しました（終了コード {code}）",
    "npm 全局安装 · @deepseek-ai/dsh": "npm グローバルインストール・@deepseek-ai/dsh",
    "pnpm install 失败（退出码 {code}）。源码已替换，请手动排查依赖。":
        "pnpm install が失敗しました（終了コード {code}）。ソースは置き換え済みです。依存関係を手動で確認してください。",
    "◉ 官方近期更新内容（最近若干提交，可作更新预期参考）：":
        "◉ 公式の最近のコミット（更新内容の見込みとして参考にできます）：",
    "◉ 版本性质：{label} {color_note}": "◉ バージョン性質：{label} {color_note}",
    "◉ 版本：本地 {local}   ∥   官方({p1}) {ref}":
        "◉ バージョン：ローカル {local}   ∥   公式({p1}) {ref}",
    "⚠ 官方最新 {ref} 为【{gl}】（预发布），可能存在兼容性变化，请按需更新。":
        "⚠ 公式最新 {ref} は【{gl}】（プレリリース）です。互換性が変わる可能性があります。必要に応じて更新してください。",
    "✅ git 同步完成：成功 {okn}，失败 {p1}，跳过 {skip}（无 git 来源）":
        "✅ git 同期完了：成功 {okn}、失敗 {p1}、スキップ {skip}（git 由来なし）",
    "✅ 最新版检测完成：共 {total} 项，其中 {upd} 项有可用更新":
        "✅ 最新版の確認完了：全 {total} 件、うち {upd} 件に更新があります",
    "✔ 完成（用时 {elapsed:.2f} 秒，平均 {speed:.1f} 项/秒）":
        "✔ 完了（所要 {elapsed:.2f} 秒、平均 {speed:.1f} 件/秒）",
    "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n":
        "「ランタイム profile」は個別更新の必要がありません：ソース／CLI インストールが提供します。\n",
    "下载完成：{dest}（{p1}，用时 {p2:.1f} 秒）":
        "ダウンロード完了：{dest}（{p1}、所要 {p2:.1f} 秒）",
    "下载的压缩包中未找到 DeepSeek Harness 源码根目录":
        "ダウンロードしたアーカイブに DeepSeek Harness のソースルートが見つかりません",
    "偏好已保存：GPU 加速 = {state}（仅本地记录，DSH 暂无对应选项）":
        "設定を保存しました：GPU アクセラレーション = {state}（ローカル記録のみ。DSH に対応オプションはまだありません）",
    "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”":
        "各起動でどのプラグインを読み込むかを決めます（Web / ACP / SDK などの profile テンプレート）。プラグインの「ランタイム」",
    "官方最新 {ref} 为【{gl}】，发布候选版。":
        "公式最新 {ref} は【{gl}】、リリース候補版です。",
    "官方源码版本：{new_version}（当前：{p1}）":
        "公式ソースのバージョン：{new_version}（現在：{p1}）",
    "官方要求 Node {engines}，无法精确判定当前环境":
        "公式要件は Node {engines} です。現在の環境を正確に判定できません",
    "官网信息获取失败（GitHub 与 npm 均不可用），无法核实":
        "公式情報の取得に失敗しました（GitHub と npm の両方が利用不可）。照合できません",
    "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换":
        "GitHub master と比較。更新方法：公式ソース zip をダウンロード → 元のディレクトリを自動バックアップ → ディレクトリごと置き換え",
    "对比 npm registry 的 latest 发布版；更新方式：npm install -g @deepseek-ai/dsh@latest。":
        "npm registry の latest リリースと比較。更新方法：npm install -g @deepseek-ai/dsh@latest。",
    "当前 v{APP_VERSION}  →  最新 {tag}": "現在 v{APP_VERSION}  →  最新 {tag}",
    "当前版本 v{APP_VERSION} · 检查更新": "現在 v{APP_VERSION}・更新を確認",
    "执行 pnpm install（新目录中安装依赖）…":
        "pnpm install を実行中（新しいディレクトリに依存関係をインストール）…",
    "执行：npm install -g @deepseek-ai/dsh@latest":
        "実行：npm install -g @deepseek-ai/dsh@latest",
    "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、":
        "dsh コマンド（CLI エントリ）を提供：profile の初期化／管理、`dsh web` で Web UI を起動、",
    "插件本身随 DeepSeek Harness 发布版更新。\n":
        "プラグイン自体は DeepSeek Harness のリリースに伴って更新されます。\n",
    "无法解析已启用插件 {name}（未在 node_modules 找到）":
        "有効なプラグイン {name} を解決できません（node_modules に見つかりません）",
    "无法访问 GitHub Releases 接口：{p1}: {e}":
        "GitHub Releases API にアクセスできません：{p1}: {e}",
    "无法访问 GitHub Tags 接口：{p1}: {e}":
        "GitHub Tags API にアクセスできません：{p1}: {e}",
    "更新完成：{p1} → {new_version}": "更新完了：{p1} → {new_version}",
    "替换后自动运行 pnpm install（推荐，用于同步依赖）":
        "置き換え後に pnpm install を自動実行（推奨。依存関係を同期します）",
    "未找到 pnpm。已替换源码，但未安装依赖；请手动运行 pnpm install":
        "pnpm が見つかりません。ソースは置き換え済みですが依存関係は未インストールです。pnpm install を手動で実行してください",
    "未找到任何插件：请检查 DSH 数据目录是否存在，或本机是否安装了运行时插件包。\n当前搜索位置：{p1}":
        "プラグインが見つかりません：DSH データフォルダが存在するか、ランタイムプラグインパッケージがインストールされているか確認してください。\n現在の検索場所：{p1}",
    "本机 Node {cur_node} 不满足官方要求 {engines}（不适配）":
        "ローカル Node {cur_node} は公式要件 {engines} を満たしません（非対応）",
    "本机 Node {cur_node} 满足官方要求 {engines}":
        "ローカル Node {cur_node} は公式要件 {engines} を満たします",
    "本身不单独更新：升级其来源（npm 全局 dsh 或源码检出）后，重启 DSH 即用新版。":
        "単体では更新されません：取得元（npm グローバル dsh またはソースチェックアウト）を更新し、DSH を再起動すると新版が使われます。",
    "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n":
        "DeepSeek Harness が実行中のようです（http://127.0.0.1:3080 が使用中）。\n",
    "检测完成（最新版）：{total} 项 / 可更新 {upd} 项":
        "確認完了（最新版）：{total} 件 / 更新可能 {upd} 件",
    "没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），":
        "git 同期できるスキルがありません：ローカルのスキルはすべてコピー（.git 由来なし）です。",
    "流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n":
        "手順：公式ソース zip をダウンロード → 元のディレクトリをバックアップ（同一ドライブで改名）→ ディレクトリごと置き換え\n",
    "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），":
        "プログラム本体。このディレクトリから直接 DSH を起動できます（例：tsx で apps/cli/src/bin.ts の Web UI を実行）、",
    "统计内置包 @deepseek-ai/{p1} 大小…":
        "組み込みパッケージ @deepseek-ai/{p1} のサイズを集計…",
    "解压完成：{done_files} 个文件，用时 {p1:.1f} 秒":
        "展開完了：{done_files} ファイル、所要 {p1:.1f} 秒",
    "该版本未出现在官方发布记录（GitHub tags / npm 版本表）中，无法核实其稳定性":
        "このバージョンは公式リリース記録（GitHub tags / npm バージョン一覧）に存在せず、安定性を確認できません",
    "该版本未声明 Node.js 运行要求（官方 engines 缺失）":
        "このバージョンは Node.js の要件を宣言していません（公式 engines がありません）",
    "该目录不是 DeepSeek Harness 源码检出（package.json name 非 @deepseek-ai/dsh-root）":
        "このディレクトリは DeepSeek Harness のソースチェックアウトではありません（package.json name が @deepseek-ai/dsh-root ではない）",
    "远端最近发布的是 {p1}，低于当前版本 {p2}；通常表示当前版本尚未发布到 GitHub。":
        "リモートの最新リリースは {p1} で、現在の {p2} より低いです。通常は現在のバージョンがまだ GitHub に公開されていないことを意味します。",
    "通过 npm 全局安装的 dsh 命令行工具包（node_modules/@deepseek-ai/dsh）。":
        "npm でグローバルインストールされた dsh CLI パッケージ（node_modules/@deepseek-ai/dsh）。",
    "（提示：更新前请先退出正在运行的 DeepSeek Harness）":
        "（ヒント：更新前に実行中の DeepSeek Harness を終了してください）",
    "🌐 官方 GitHub master：{gh_txt}": "🌐 公式 GitHub master：{gh_txt}",
    "🛑 官方最新 {ref} 官网信息不足，判定为【{gl}】，请谨慎更新。":
        "🛑 公式最新 {ref} は公式情報が不足しており【{gl}】と判定されました。慎重に更新してください。",
    "🛡 自检：发现并合并 {p1} 处重复安装（同一真实路径）":
        "🛡 自己診断：同一の実パスを指す重複インストール {p1} 件を統合しました",
}


EXTRA["ko"] = {
    "\n\n🛑 注意：该版本【不稳定版】，官网无法核实，升级请谨慎。":
        "\n\n🛑 주의: 이 버전은 [불안정판]이며 공식 정보로 확인할 수 없습니다. 업그레이드에 주의하세요.",
    "\n\n🟣 提示：该版本为官方预发布（alpha/beta），可能存在兼容性变化。":
        "\n\n🟣 안내: 이 버전은 공식 사전 릴리스(alpha/beta)입니다. 호환성이 바뀔 수 있습니다.",
    "\n   ⚠ 未能在官网核实该版本 —— 视为【不稳定版】，请谨慎使用":
        "\n   ⚠ 이 버전은 공식 정보로 확인할 수 없습니다 — [불안정판]으로 간주합니다. 주의해서 사용하세요",
    "\n[4] 插件扫描（启用 + 运行时内置，含效率统计）":
        "\n[4] 플러그인 검사(사용 중 + 런타임 내장, 소요 시간 포함)",
    "\n[5b] 进度回调演示（skills 前 5 项）":
        "\n[5b] 진행률 콜백 데모(skills 처음 5개)",
    "\n[7] 端口占用检测（DSH Web 3080）":
        "\n[7] 포트 사용 확인(DSH Web 3080)",
    "  {ZIP_URL}\n  HTTP {p1}  大小约 {p2}":
        "  {ZIP_URL}\n  HTTP {p1}  크기 약 {p2}",
    "  （未自动发现任何安装——源码检出可用 --add 手动指定）":
        "  (설치를 자동으로 찾지 못했습니다 — 소스 체크아웃은 --add로 직접 지정할 수 있습니다)",
    "DSH 数据目录（DSH_HOME）：\n{p1}\n\n技能目录：\n{p2}\n\n本更新器设置文件：\n{p3}\n\n提示：可通过环境变量 DSH_HOME / DSH_SKILLS 更改检测位置。":
        "DSH 데이터 폴더(DSH_HOME):\n{p1}\n\n스킬 폴더:\n{p2}\n\n업데이터 설정 파일:\n{p3}\n\n팁: 환경 변수 DSH_HOME / DSH_SKILLS로 검색 위치를 바꿀 수 있습니다.",
    "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理":
        "DSH_HOME(기본 ~/.dsh/profiles/<name>) 아래의 실행 인스턴스로, pnpm workspace 형태로 관리됩니다",
    "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。":
        "DeepSeek Harness의 전체 오픈소스 프로젝트(package.json: @deepseek-ai/dsh-root).",
    "npm install -g 失败（退出码 {code}）":
        "npm install -g 실패(종료 코드 {code})",
    "npm 全局安装 · @deepseek-ai/dsh": "npm 전역 설치 · @deepseek-ai/dsh",
    "pnpm install 失败（退出码 {code}）。源码已替换，请手动排查依赖。":
        "pnpm install 실패(종료 코드 {code}). 소스는 교체되었습니다. 의존성을 직접 확인하세요.",
    "◉ 官方近期更新内容（最近若干提交，可作更新预期参考）：":
        "◉ 공식 최근 커밋(업데이트 내용을 예상하는 참고 자료):",
    "◉ 版本性质：{label} {color_note}": "◉ 버전 성질: {label} {color_note}",
    "◉ 版本：本地 {local}   ∥   官方({p1}) {ref}":
        "◉ 버전: 로컬 {local}   ∥   공식({p1}) {ref}",
    "⚠ 官方最新 {ref} 为【{gl}】（预发布），可能存在兼容性变化，请按需更新。":
        "⚠ 공식 최신 {ref}은(는) [{gl}](사전 릴리스)입니다. 호환성이 바뀔 수 있으니 필요할 때 업데이트하세요.",
    "✅ git 同步完成：成功 {okn}，失败 {p1}，跳过 {skip}（无 git 来源）":
        "✅ git 동기화 완료: 성공 {okn}, 실패 {p1}, 건너뜀 {skip}(git 출처 없음)",
    "✅ 最新版检测完成：共 {total} 项，其中 {upd} 项有可用更新":
        "✅ 최신 버전 확인 완료: 총 {total}개, 그중 {upd}개 업데이트 가능",
    "✔ 完成（用时 {elapsed:.2f} 秒，平均 {speed:.1f} 项/秒）":
        "✔ 완료(소요 {elapsed:.2f}초, 평균 {speed:.1f}개/초)",
    "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n":
        "「런타임 profile」은 별도로 업데이트할 필요가 없습니다: 소스/CLI 설치가 제공합니다.\n",
    "下载完成：{dest}（{p1}，用时 {p2:.1f} 秒）":
        "다운로드 완료: {dest}({p1}, 소요 {p2:.1f}초)",
    "下载的压缩包中未找到 DeepSeek Harness 源码根目录":
        "내려받은 압축 파일에서 DeepSeek Harness 소스 루트를 찾지 못했습니다",
    "偏好已保存：GPU 加速 = {state}（仅本地记录，DSH 暂无对应选项）":
        "설정 저장됨: GPU 가속 = {state}(로컬 기록만. DSH에는 아직 해당 옵션이 없습니다)",
    "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”":
        "각 실행에서 어떤 플러그인을 불러올지 결정합니다(Web / ACP / SDK 등 profile 템플릿). 플러그인의 \"런타임\"",
    "官方最新 {ref} 为【{gl}】，发布候选版。":
        "공식 최신 {ref}은(는) [{gl}], 릴리스 후보 버전입니다.",
    "官方源码版本：{new_version}（当前：{p1}）":
        "공식 소스 버전: {new_version}(현재: {p1})",
    "官方要求 Node {engines}，无法精确判定当前环境":
        "공식 요구 사항은 Node {engines}입니다. 현재 환경을 정확히 판정할 수 없습니다",
    "官网信息获取失败（GitHub 与 npm 均不可用），无法核实":
        "공식 정보를 가져오지 못했습니다(GitHub와 npm 모두 사용 불가). 확인할 수 없습니다",
    "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换":
        "GitHub master와 비교. 업데이트 방법: 공식 소스 zip 다운로드 → 원래 폴더 자동 백업 → 폴더 전체 교체",
    "对比 npm registry 的 latest 发布版；更新方式：npm install -g @deepseek-ai/dsh@latest。":
        "npm registry의 latest 릴리스와 비교. 업데이트 방법: npm install -g @deepseek-ai/dsh@latest.",
    "当前 v{APP_VERSION}  →  最新 {tag}": "현재 v{APP_VERSION}  →  최신 {tag}",
    "当前版本 v{APP_VERSION} · 检查更新": "현재 v{APP_VERSION} · 업데이트 확인",
    "执行 pnpm install（新目录中安装依赖）…":
        "pnpm install 실행 중(새 폴더에 의존성 설치)…",
    "执行：npm install -g @deepseek-ai/dsh@latest":
        "실행: npm install -g @deepseek-ai/dsh@latest",
    "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、":
        "dsh 명령(CLI 진입점)을 제공: profile 초기화/관리, `dsh web`으로 Web UI 실행,",
    "插件本身随 DeepSeek Harness 发布版更新。\n":
        "플러그인 자체는 DeepSeek Harness 릴리스와 함께 업데이트됩니다.\n",
    "无法解析已启用插件 {name}（未在 node_modules 找到）":
        "사용 중인 플러그인 {name}을(를) 확인할 수 없습니다(node_modules에서 찾지 못함)",
    "无法访问 GitHub Releases 接口：{p1}: {e}":
        "GitHub Releases API에 접근할 수 없습니다: {p1}: {e}",
    "无法访问 GitHub Tags 接口：{p1}: {e}":
        "GitHub Tags API에 접근할 수 없습니다: {p1}: {e}",
    "更新完成：{p1} → {new_version}": "업데이트 완료: {p1} → {new_version}",
    "替换后自动运行 pnpm install（推荐，用于同步依赖）":
        "교체 후 pnpm install 자동 실행(권장. 의존성을 동기화합니다)",
    "未找到 pnpm。已替换源码，但未安装依赖；请手动运行 pnpm install":
        "pnpm을 찾지 못했습니다. 소스는 교체되었지만 의존성은 설치되지 않았습니다. pnpm install을 직접 실행하세요",
    "未找到任何插件：请检查 DSH 数据目录是否存在，或本机是否安装了运行时插件包。\n当前搜索位置：{p1}":
        "플러그인을 찾지 못했습니다: DSH 데이터 폴더가 있는지, 런타임 플러그인 패키지가 설치되어 있는지 확인하세요.\n현재 검색 위치: {p1}",
    "本机 Node {cur_node} 不满足官方要求 {engines}（不适配）":
        "로컬 Node {cur_node}은(는) 공식 요구 사항 {engines}을(를) 충족하지 않습니다(호환되지 않음)",
    "本机 Node {cur_node} 满足官方要求 {engines}":
        "로컬 Node {cur_node}은(는) 공식 요구 사항 {engines}을(를) 충족합니다",
    "本身不单独更新：升级其来源（npm 全局 dsh 或源码检出）后，重启 DSH 即用新版。":
        "자체적으로는 업데이트되지 않습니다: 출처(npm 전역 dsh 또는 소스 체크아웃)를 업그레이드한 뒤 DSH를 다시 시작하면 새 버전이 사용됩니다.",
    "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n":
        "DeepSeek Harness가 실행 중인 것으로 보입니다(http://127.0.0.1:3080 사용 중).\n",
    "检测完成（最新版）：{total} 项 / 可更新 {upd} 项":
        "확인 완료(최신 버전): {total}개 / 업데이트 가능 {upd}개",
    "没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），":
        "git 동기화할 수 있는 스킬이 없습니다: 로컬 스킬은 모두 복사 설치입니다(.git 출처 없음).",
    "流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n":
        "절차: 공식 소스 zip 다운로드 → 원래 폴더 백업(같은 드라이브에서 이름 변경) → 폴더 전체 교체\n",
    "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），":
        "프로그램 본체. 이 폴더에서 DSH를 직접 시작할 수 있습니다(예: tsx로 apps/cli/src/bin.ts의 Web UI 실행),",
    "统计内置包 @deepseek-ai/{p1} 大小…":
        "내장 패키지 @deepseek-ai/{p1} 크기 집계 중…",
    "解压完成：{done_files} 个文件，用时 {p1:.1f} 秒":
        "압축 해제 완료: {done_files}개 파일, 소요 {p1:.1f}초",
    "该版本未出现在官方发布记录（GitHub tags / npm 版本表）中，无法核实其稳定性":
        "이 버전은 공식 릴리스 기록(GitHub tags / npm 버전 목록)에 없어 안정성을 확인할 수 없습니다",
    "该版本未声明 Node.js 运行要求（官方 engines 缺失）":
        "이 버전은 Node.js 요구 사항을 선언하지 않았습니다(공식 engines 없음)",
    "该目录不是 DeepSeek Harness 源码检出（package.json name 非 @deepseek-ai/dsh-root）":
        "이 폴더는 DeepSeek Harness 소스 체크아웃이 아닙니다(package.json name이 @deepseek-ai/dsh-root가 아님)",
    "远端最近发布的是 {p1}，低于当前版本 {p2}；通常表示当前版本尚未发布到 GitHub。":
        "원격 최근 릴리스는 {p1}이며 현재 {p2}보다 낮습니다. 보통 현재 버전이 아직 GitHub에 공개되지 않았다는 뜻입니다.",
    "通过 npm 全局安装的 dsh 命令行工具包（node_modules/@deepseek-ai/dsh）。":
        "npm으로 전역 설치된 dsh CLI 패키지(node_modules/@deepseek-ai/dsh).",
    "（提示：更新前请先退出正在运行的 DeepSeek Harness）":
        "(팁: 업데이트 전에 실행 중인 DeepSeek Harness를 종료하세요)",
    "🌐 官方 GitHub master：{gh_txt}": "🌐 공식 GitHub master: {gh_txt}",
    "🛑 官方最新 {ref} 官网信息不足，判定为【{gl}】，请谨慎更新。":
        "🛑 공식 최신 {ref}은(는) 공식 정보가 부족하여 [{gl}](으)로 판정되었습니다. 신중하게 업데이트하세요.",
    "🛡 自检：发现并合并 {p1} 处重复安装（同一真实路径）":
        "🛡 자가 점검: 동일한 실제 경로를 가리키는 중복 설치 {p1}개를 병합했습니다",
}


# 检测缓存相关文案（v0.7.0 新增）
for _lang, _pair in {
    "en": ("Last scan: {p1}",
           "Loaded the previous scan result ({p1}); rescanning in the background…"),
    "zh-TW": ("上次偵測：{p1}",
              "已載入上次偵測結果（{p1}），正在背景重新偵測…"),
    "ja": ("前回の検出：{p1}",
           "前回の検出結果を読み込みました（{p1}）。バックグラウンドで再検出中…"),
    "ko": ("마지막 검사: {p1}",
           "이전 검사 결과를 불러왔습니다({p1}). 백그라운드에서 다시 검사하는 중…"),
}.items():
    EXTRA[_lang].update({
        "上次检测：{p1}": _pair[0],
        "已载入上次检测结果（{p1}），正在后台重新检测…": _pair[1],
    })


# 下载来源按钮相关文案（v0.7.0 新增）
for _lang, _triple in {
    "en": ("🔗 Open download source",
           "No recognizable download source: skills need a .git origin; plugins must be npm packages.",
           "Remembered source: {p1} → {p2}"),
    "zh-TW": ("🔗 開啟下載來源",
              "這條沒有可辨識的下載來源：技能需要帶 .git 來源，外掛需要是 npm 套件。",
              "已記住來源：{p1} → {p2}"),
    "ja": ("🔗 ダウンロード元を開く",
           "認識できるダウンロード元がありません：スキルは .git 由来、プラグインは npm パッケージである必要があります。",
           "取得元を記憶しました：{p1} → {p2}"),
    "ko": ("🔗 다운로드 출처 열기",
           "인식할 수 있는 다운로드 출처가 없습니다: 스킬은 .git 출처, 플러그인은 npm 패키지여야 합니다.",
           "출처를 기억했습니다: {p1} → {p2}"),
}.items():
    EXTRA[_lang].update({
        "🔗 打开下载来源": _triple[0],
        "这条没有可识别的下载来源：技能需要带 .git 来源，插件需要是 npm 包。": _triple[1],
        "已记住来源：{p1} → {p2}": _triple[2],
    })


