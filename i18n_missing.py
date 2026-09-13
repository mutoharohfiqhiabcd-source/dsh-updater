# -*- coding: utf-8 -*-
"""补充翻译表：折行拼接后整体取值、以及遗漏的少数长文案。

为什么单独一个文件：这些键是**拼接后的完整字符串**（源码里写成相邻的多段
字面量），按 token 提取会得到各段而不是整体，导致整条查不到译文而回退中文。
"""
from __future__ import annotations

_MISSING: dict[str, dict[str, str]] = {

    "en": {
        "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。一般来自 git clone 或 GitHub 源码 zip 解压，包含 apps/cli 等全部源码。":
            "The complete open-source DeepSeek Harness project (package.json: @deepseek-ai/dsh-root). Usually obtained by git clone or by extracting the GitHub source zip; contains all sources including apps/cli.",
        "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），内置 dsh-* 插件包大多源自这里的 packages 工程。":
            "The main program. DSH can be started directly from this directory (e.g. running the Web UI via tsx on apps/cli/src/bin.ts); most built-in dsh-* plugin packages originate from the packages workspace here.",
        "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换（node_modules/.git 会保留并移回，可勾选随后 pnpm install）。":
            "Compares against GitHub master; update: download the official source zip → auto-backup the original directory → replace the whole directory (node_modules/.git are kept and moved back; optionally run pnpm install afterwards).",
        "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、加载当前安装的运行时插件。":
            "Provides the dsh command (CLI entry): init/manage profiles, run `dsh web` to start the Web UI, and load the currently installed runtime plugins.",
        "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理该 profile 启用的插件清单（package.json 的 dsh.profile.bundles）与本地配置。":
            "A runtime instance under DSH_HOME (default ~/.dsh/profiles/<name>), managed as a pnpm workspace; holds the enabled plugin list (package.json dsh.profile.bundles) and local configuration for that profile.",
        "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”层面的宿主目录，随 dsh CLI / 源码安装自动生成。":
            "Determines which plugins a given launch loads (Web / ACP / SDK profile templates); it is the plugin host directory at the \"runtime\" level and is created automatically by the dsh CLI / source install.",
        "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n请更新其对应的源码检出或 npm 全局安装。":
            "Runtime profiles do not need separate updates: they are provided by the source/CLI install.\nPlease update the corresponding source checkout or npm global install.",
        "已按新语言重建界面（沿用上次检测结果，未重新扫描）":
            "Rebuilt the UI for the new language (reusing the previous scan result; no rescan)",
        "插件本身随 DeepSeek Harness 发布版更新。\n是否打开主窗口执行「npm 全局 / 源码检出」更新？\n（第三方插件请在对应 profile 中用 dsh plugin 更新）":
            "Plugins themselves are updated with DeepSeek Harness releases.\nOpen the main window to update the npm global / source checkout?\n(For third-party plugins, use `dsh plugin` in the corresponding profile.)",
        "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n请先关闭正在运行的 DeepSeek Harness，再执行更新。":
            "DeepSeek Harness appears to be running (http://127.0.0.1:3080 is in use).\nClose the running DeepSeek Harness before updating.",
        "没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），请在官网手动下载覆盖。":
            "No skills can be git-synced: all local skills are copies (no .git origin). Download and overwrite them manually from the official site.",
        "流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n（node_modules / .git 会自动移回新目录，以加快依赖安装）\n更新期间请勿关闭本程序；若 DSH Web (3080) 正在运行将中止更新。":
            "Steps: download the official source zip → back up the original directory (rename on the same drive) → replace the whole directory\n(node_modules / .git are moved back automatically to speed up dependency install)\nDo not close this program during the update; if DSH Web (3080) is running the update will be aborted.",
    },

    "zh-TW": {
        "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。一般来自 git clone 或 GitHub 源码 zip 解压，包含 apps/cli 等全部源码。":
            "DeepSeek Harness 的完整開源原始碼專案（package.json: @deepseek-ai/dsh-root）。一般來自 git clone 或 GitHub 原始碼 zip 解壓縮，包含 apps/cli 等全部原始碼。",
        "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），内置 dsh-* 插件包大多源自这里的 packages 工程。":
            "程式主體。可從此目錄直接啟動 DSH（例如以 tsx 執行 apps/cli/src/bin.ts 的 Web UI），內建 dsh-* 外掛套件大多源自這裡的 packages 專案。",
        "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换（node_modules/.git 会保留并移回，可勾选随后 pnpm install）。":
            "比對 GitHub master 原始碼；更新方式：下載官方原始碼 zip → 自動備份原目錄 → 整目錄取代（node_modules/.git 會保留並移回，可勾選隨後執行 pnpm install）。",
        "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、加载当前安装的运行时插件。":
            "提供 dsh 命令（CLI 入口）：初始化／管理 profile、執行 `dsh web` 啟動 Web UI、載入目前安裝的執行階段外掛。",
        "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理该 profile 启用的插件清单（package.json 的 dsh.profile.bundles）与本地配置。":
            "DSH_HOME（預設 ~/.dsh/profiles/<name>）下的執行實例，以 pnpm workspace 形態管理該 profile 啟用的外掛清單（package.json 的 dsh.profile.bundles）與本機設定。",
        "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”层面的宿主目录，随 dsh CLI / 源码安装自动生成。":
            "決定某次啟動載入哪些外掛（Web / ACP / SDK 等 profile 範本），是外掛在「執行階段」層面的宿主目錄，隨 dsh CLI／原始碼安裝自動產生。",
        "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n请更新其对应的源码检出或 npm 全局安装。":
            "「執行階段 profile」無需單獨更新：它由原始碼／CLI 安裝提供。\n請更新其對應的原始碼檢查或 npm 全域安裝。",
        "已按新语言重建界面（沿用上次检测结果，未重新扫描）":
            "已依新語言重建介面（沿用上次偵測結果，未重新掃描）",
        "插件本身随 DeepSeek Harness 发布版更新。\n是否打开主窗口执行「npm 全局 / 源码检出」更新？\n（第三方插件请在对应 profile 中用 dsh plugin 更新）":
            "外掛本身隨 DeepSeek Harness 發行版更新。\n是否開啟主視窗執行「npm 全域／原始碼檢查」更新？\n（第三方外掛請在對應 profile 中使用 dsh plugin 更新）",
        "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n请先关闭正在运行的 DeepSeek Harness，再执行更新。":
            "偵測到 DeepSeek Harness 正在執行（http://127.0.0.1:3080 被佔用）。\n請先關閉正在執行的 DeepSeek Harness，再執行更新。",
        "没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），请在官网手动下载覆盖。":
            "沒有可 git 同步的技能：本機技能均為複製安裝（無 .git 來源），請在官網手動下載覆蓋。",
        "流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n（node_modules / .git 会自动移回新目录，以加快依赖安装）\n更新期间请勿关闭本程序；若 DSH Web (3080) 正在运行将中止更新。":
            "流程：下載官方原始碼 zip → 備份原目錄（同磁碟改名）→ 整目錄取代\n（node_modules / .git 會自動移回新目錄，以加快相依套件安裝）\n更新期間請勿關閉本程式；若 DSH Web (3080) 正在執行將中止更新。",
    },

    "ja": {
        "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。一般来自 git clone 或 GitHub 源码 zip 解压，包含 apps/cli 等全部源码。":
            "DeepSeek Harness の完全なオープンソースプロジェクト（package.json: @deepseek-ai/dsh-root）。通常は git clone か GitHub のソース zip を展開して入手し、apps/cli を含む全ソースを保持します。",
        "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），内置 dsh-* 插件包大多源自这里的 packages 工程。":
            "プログラム本体。このディレクトリから直接 DSH を起動できます（例：tsx で apps/cli/src/bin.ts の Web UI を実行）。組み込みの dsh-* プラグインパッケージの多くは、ここの packages ワークスペース由来です。",
        "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换（node_modules/.git 会保留并移回，可勾选随后 pnpm install）。":
            "GitHub master と比較。更新方法：公式ソース zip をダウンロード → 元のディレクトリを自動バックアップ → ディレクトリごと置き換え（node_modules/.git は保持され元に戻されます。任意で pnpm install を実行）。",
        "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、加载当前安装的运行时插件。":
            "dsh コマンド（CLI エントリ）を提供：profile の初期化／管理、`dsh web` で Web UI を起動、現在インストールされているランタイムプラグインを読み込み。",
        "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理该 profile 启用的插件清单（package.json 的 dsh.profile.bundles）与本地配置。":
            "DSH_HOME（既定 ~/.dsh/profiles/<name>）配下の実行インスタンス。pnpm workspace として管理され、その profile で有効なプラグイン一覧（package.json の dsh.profile.bundles）とローカル設定を保持します。",
        "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”层面的宿主目录，随 dsh CLI / 源码安装自动生成。":
            "各起動でどのプラグインを読み込むかを決めます（Web / ACP / SDK などの profile テンプレート）。プラグインの「ランタイム」層におけるホストディレクトリで、dsh CLI／ソースインストール時に自動生成されます。",
        "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n请更新其对应的源码检出或 npm 全局安装。":
            "「ランタイム profile」は個別更新の必要がありません：ソース／CLI インストールが提供します。\n対応するソースチェックアウトまたは npm グローバルインストールを更新してください。",
        "已按新语言重建界面（沿用上次检测结果，未重新扫描）":
            "新しい言語で画面を再構築しました（前回の検出結果を流用し、再スキャンはしていません）",
        "插件本身随 DeepSeek Harness 发布版更新。\n是否打开主窗口执行「npm 全局 / 源码检出」更新？\n（第三方插件请在对应 profile 中用 dsh plugin 更新）":
            "プラグイン自体は DeepSeek Harness のリリースに伴って更新されます。\nメインウィンドウを開いて「npm グローバル／ソースチェックアウト」を更新しますか？\n（サードパーティ製プラグインは、該当 profile で dsh plugin を使って更新してください）",
        "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n请先关闭正在运行的 DeepSeek Harness，再执行更新。":
            "DeepSeek Harness が実行中のようです（http://127.0.0.1:3080 が使用中）。\n実行中の DeepSeek Harness を終了してから更新してください。",
        "没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），请在官网手动下载覆盖。":
            "git 同期できるスキルがありません：ローカルのスキルはすべてコピー（.git 由来なし）です。公式サイトから手動でダウンロードして上書きしてください。",
        "流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n（node_modules / .git 会自动移回新目录，以加快依赖安装）\n更新期间请勿关闭本程序；若 DSH Web (3080) 正在运行将中止更新。":
            "手順：公式ソース zip をダウンロード → 元のディレクトリをバックアップ（同一ドライブで改名）→ ディレクトリごと置き換え\n（node_modules / .git は自動的に新しいディレクトリへ戻され、依存インストールが速くなります）\n更新中はこのプログラムを閉じないでください。DSH Web (3080) が実行中の場合は更新を中止します。",
    },

    "ko": {
        "DeepSeek Harness 的完整开源源码工程（package.json: @deepseek-ai/dsh-root）。一般来自 git clone 或 GitHub 源码 zip 解压，包含 apps/cli 等全部源码。":
            "DeepSeek Harness의 전체 오픈소스 프로젝트(package.json: @deepseek-ai/dsh-root). 보통 git clone 또는 GitHub 소스 zip 압축 해제로 얻으며 apps/cli를 포함한 모든 소스를 담고 있습니다.",
        "程序主体。可从该目录直接启动 DSH（如 tsx 运行 apps/cli/src/bin.ts 的 Web UI），内置 dsh-* 插件包大多源自这里的 packages 工程。":
            "프로그램 본체. 이 폴더에서 DSH를 직접 시작할 수 있습니다(예: tsx로 apps/cli/src/bin.ts의 Web UI 실행). 내장 dsh-* 플러그인 패키지 대부분이 여기 packages 워크스페이스에서 나옵니다.",
        "对比 GitHub master 源码；更新方式：下载官方源码 zip → 自动备份原目录 → 整目录替换（node_modules/.git 会保留并移回，可勾选随后 pnpm install）。":
            "GitHub master와 비교. 업데이트 방법: 공식 소스 zip 다운로드 → 원래 폴더 자동 백업 → 폴더 전체 교체(node_modules/.git는 유지되어 되돌려집니다. 이후 pnpm install 선택 가능).",
        "提供 dsh 命令（CLI 入口）：初始化/管理 profile、运行 `dsh web` 启动 Web UI、加载当前安装的运行时插件。":
            "dsh 명령(CLI 진입점)을 제공: profile 초기화/관리, `dsh web`으로 Web UI 실행, 현재 설치된 런타임 플러그인 로드.",
        "DSH_HOME（默认 ~/.dsh/profiles/<name>）下的运行实例，以 pnpm workspace 形态管理该 profile 启用的插件清单（package.json 的 dsh.profile.bundles）与本地配置。":
            "DSH_HOME(기본 ~/.dsh/profiles/<name>) 아래의 실행 인스턴스로, pnpm workspace 형태로 관리됩니다. 해당 profile에서 사용하는 플러그인 목록(package.json dsh.profile.bundles)과 로컬 설정을 담고 있습니다.",
        "决定某次启动加载哪些插件（Web / ACP / SDK 等 profile 模板），是插件在“运行时”层面的宿主目录，随 dsh CLI / 源码安装自动生成。":
            "각 실행에서 어떤 플러그인을 불러올지 결정합니다(Web / ACP / SDK 등 profile 템플릿). 플러그인의 \"런타임\" 계층 호스트 폴더이며 dsh CLI/소스 설치 시 자동 생성됩니다.",
        "「运行时 profile」无需单独更新：它由源码/CLI 安装提供。\n请更新其对应的源码检出或 npm 全局安装。":
            "「런타임 profile」은 별도로 업데이트할 필요가 없습니다: 소스/CLI 설치가 제공합니다.\n해당 소스 체크아웃 또는 npm 전역 설치를 업데이트하세요.",
        "已按新语言重建界面（沿用上次检测结果，未重新扫描）":
            "새 언어로 화면을 다시 만들었습니다(이전 검사 결과를 그대로 사용, 다시 검사하지 않음)",
        "插件本身随 DeepSeek Harness 发布版更新。\n是否打开主窗口执行「npm 全局 / 源码检出」更新？\n（第三方插件请在对应 profile 中用 dsh plugin 更新）":
            "플러그인 자체는 DeepSeek Harness 릴리스와 함께 업데이트됩니다.\n메인 창을 열어 \"npm 전역 / 소스 체크아웃\"을 업데이트할까요?\n(서드파티 플러그인은 해당 profile에서 dsh plugin으로 업데이트하세요)",
        "检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\n请先关闭正在运行的 DeepSeek Harness，再执行更新。":
            "DeepSeek Harness가 실행 중인 것으로 보입니다(http://127.0.0.1:3080 사용 중).\n실행 중인 DeepSeek Harness를 종료한 뒤 업데이트하세요.",
        "没有可 git 同步的技能：本机技能均为拷贝安装（无 .git 来源），请在官网手动下载覆盖。":
            "git 동기화할 수 있는 스킬이 없습니다: 로컬 스킬은 모두 복사 설치입니다(.git 출처 없음). 공식 사이트에서 직접 내려받아 덮어쓰세요.",
        "流程：下载官方源码 zip → 备份原目录（同盘改名）→ 整目录替换\n（node_modules / .git 会自动移回新目录，以加快依赖安装）\n更新期间请勿关闭本程序；若 DSH Web (3080) 正在运行将中止更新。":
            "절차: 공식 소스 zip 다운로드 → 원래 폴더 백업(같은 드라이브에서 이름 변경) → 폴더 전체 교체\n(node_modules / .git는 자동으로 새 폴더로 되돌려져 의존성 설치가 빨라집니다)\n업데이트 중에는 이 프로그램을 닫지 마세요. DSH Web (3080)이 실행 중이면 업데이트를 중단합니다.",
    },
}

TABLES_EXTRA = _MISSING


# npm 全局更新前的进程检查提示（v0.7.1）
for _lang, _pair in {
    'en': ('DeepSeek Harness appears to be running (http://127.0.0.1:3080 is in use).\\nUpdating the npm global install replaces native modules that are currently in use; it may fail or even corrupt the install.\\nClose DeepSeek Harness first, then run the update.', 'Note: {p1} node process(es) detected. If they are using dsh, npm may fail because files are locked; closing them all is recommended.'),
    'zh-TW': ('偵測到 DeepSeek Harness 正在執行（http://127.0.0.1:3080 被佔用）。\\n更新 npm 全域安裝會取代正在使用的原生模組，可能失敗甚至損壞安裝。\\n請先關閉 DeepSeek Harness，再執行更新。', '提示：偵測到 {p1} 個 node 行程。若它們正在使用 dsh，npm 可能因檔案佔用而失敗；建議先全部關閉。'),
    'ja': ('DeepSeek Harness が実行中のようです（http://127.0.0.1:3080 が使用中）。\\nnpm グローバルインストールの更新は使用中のネイティブモジュールを置き換えるため、失敗したりインストールを破損させる可能性があります。\\n先に DeepSeek Harness を終了してから更新してください。', 'ヒント：{p1} 個の node プロセスを検出しました。それらが dsh を使用中だとファイルがロックされ npm が失敗することがあります。すべて終了することを推奨します。'),
    'ko': ('DeepSeek Harness가 실행 중인 것으로 보입니다(http://127.0.0.1:3080 사용 중).\\nnpm 전역 설치를 업데이트하면 사용 중인 네이티브 모듈을 교체하므로 실패하거나 설치가 손상될 수 있습니다.\\n먼저 DeepSeek Harness를 종료한 뒤 업데이트하세요.', '안내: node 프로세스 {p1}개가 감지되었습니다. 이들이 dsh를 사용 중이면 파일이 잠겨 npm이 실패할 수 있으니 모두 종료하는 것을 권장합니다.'),
}.items():
    TABLES_EXTRA.setdefault(_lang, {}).update({
        '检测到 DeepSeek Harness 正在运行（http://127.0.0.1:3080 被占用）。\\n更新 npm 全局安装会替换正在使用的原生模块，可能失败甚至损坏安装。\\n请先关闭 DeepSeek Harness，再执行更新。': _pair[0],
        '提示：检测到 {p1} 个 node 进程。若它们正在使用 dsh，npm 可能因文件占用而失败；建议先全部关闭。': _pair[1],
    })


# 源码更新后提示重新构建（v0.7.1）
for _lang, _val in {
    'en': 'Note: build output (apps/cli/lib) from the original directory was not kept.\\nIf you start DSH from it, run: pnpm install && pnpm run build',
    'zh-TW': '注意：原目錄中的建置產物（apps/cli/lib）未隨原始碼保留。\\n若你用它直接啟動 DSH，請重新執行：pnpm install && pnpm run build',
    'ja': '注意：元のディレクトリのビルド成果物（apps/cli/lib）は引き継がれませんでした。\\nそれを使って DSH を起動している場合は、次を再実行してください：pnpm install && pnpm run build',
    'ko': '주의: 원래 폴더의 빌드 산출물(apps/cli/lib)은 유지되지 않았습니다.\\n이를 사용해 DSH를 시작한다면 다음을 다시 실행하세요: pnpm install && pnpm run build',
}.items():
    TABLES_EXTRA.setdefault(_lang, {}).update({'注意：原目录中的构建产物（apps/cli/lib）未随源码保留。\\n若你用它直接启动 DSH，请重新执行：pnpm install && pnpm run build': _val})


# 源码更新的 pnpm 步骤（v0.7.2）
for _lang, _vals in {
    'en': ('Running {p1} …', 'pnpm not found. Source was replaced but {p1} was not run; please run it manually.', '{p1} failed (exit code {p2}). Source was replaced; please investigate manually.', 'Run pnpm run build after replacing (required to start from a source checkout)'),
    'zh-TW': ('執行 {p1} …', '找不到 pnpm。原始碼已取代，但未執行 {p1}；請手動執行。', '{p1} 失敗（退出碼 {p2}）。原始碼已取代，請手動排查。', '取代後自動執行 pnpm run build（原始碼版啟動必需）'),
    'ja': ('{p1} を実行中 …', 'pnpm が見つかりません。ソースは置き換え済みですが {p1} は未実行です。手動で実行してください。', '{p1} が失敗しました（終了コード {p2}）。ソースは置き換え済みです。手動で確認してください。', '置き換え後に pnpm run build を実行（ソース版の起動に必須）'),
    'ko': ('{p1} 실행 중 …', 'pnpm을 찾지 못했습니다. 소스는 교체되었지만 {p1}은(는) 실행되지 않았습니다. 직접 실행하세요.', '{p1} 실패(종료 코드 {p2}). 소스는 교체되었습니다. 직접 확인하세요.', '교체 후 pnpm run build 실행(소스판 시작에 필수)'),
}.items():
    for _k, _v in zip({
        '执行 {p1} …',
        '未找到 pnpm。已替换源码，但未执行 {p1}；请手动运行。',
        '{p1} 失败（退出码 {p2}）。源码已替换，请手动排查。',
        '替换后自动运行 pnpm run build（源码版启动必需）',
    }, _vals):
        TABLES_EXTRA.setdefault(_lang, {}).update({_k: _v})
