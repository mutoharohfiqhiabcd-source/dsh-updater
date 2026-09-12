# -*- coding: utf-8 -*-
"""多语言（i18n）支持。

设计要点
--------
1. **以简体中文原文作为翻译键**。这样把现有代码改成多语言的代价最小：
   只需 `"就绪"` → `t("就绪")`，不必另建一套 key 表；缺翻译时自动回退原文，
   因此界面永远不会出现空白或报错，翻译可以分批补齐。
2. **翻译表内嵌在 Python 里**，不用外部 JSON 文件——PyInstaller onefile
   打包时外部数据文件需要额外配置，内嵌则随代码一起进归档，不会漏。
3. 语言解析优先级：显式设置 > 系统语言 > 简体中文。
   settings.json 中 `language = "auto"` 表示跟随系统。

带变量的句子用 `{name}` 占位符，调用方传关键字参数：

    t("检测到 {n} 处安装", n=5)
"""
from __future__ import annotations

import locale
import os

SOURCE_LANG = "zh-CN"

# (语言码, 该语言的自称, 英文名) —— 下拉框里显示"自称"，用户一眼能找到自己的语言
LANGUAGES: tuple[tuple[str, str, str], ...] = (
    ("zh-CN", "简体中文", "Simplified Chinese"),
    ("zh-TW", "繁體中文", "Traditional Chinese"),
    ("en", "English", "English"),
    ("ja", "日本語", "Japanese"),
    ("ko", "한국어", "Korean"),
)

LANGUAGE_CODES: tuple[str, ...] = tuple(code for code, _, _ in LANGUAGES)
AUTO = "auto"

# 各种系统写法 → 我们的语言码。注意顺序：先匹配长的（zh-hant 要先于 zh）。
_ALIASES: tuple[tuple[str, str], ...] = (
    ("zh-hant", "zh-TW"), ("zh-tw", "zh-TW"), ("zh-hk", "zh-TW"),
    ("zh-mo", "zh-TW"), ("zh-hans", "zh-CN"), ("zh-cn", "zh-CN"),
    ("zh-sg", "zh-CN"), ("zh", "zh-CN"),
    ("en", "en"),
    ("ja", "ja"), ("jp", "ja"),
    ("ko", "ko"), ("kr", "ko"),
)

_current = SOURCE_LANG
_setting = AUTO


# ---------------------------------------------------------------------------
# 翻译表：{语言码: {简体中文原文: 译文}}
# ---------------------------------------------------------------------------
TABLES: dict[str, dict[str, str]] = {"zh-TW": {}, "en": {}, "ja": {}, "ko": {}}

TABLES["en"] = {
    # ---- 应用与窗口 ----
    "DeepSeek Harness 自动检测与更新器": "DeepSeek Harness Auto Detector & Updater",
    "DeepSeek Harness 更新器": "DeepSeek Harness Updater",
    "检查更新器自身更新": "Check for Updater Updates",
    "自动检测本机安装 · 对比官方版本 · 插件/技能扫描 · 一键更新":
        "Detect local installs · Compare with official · Plugin/Skill scan · One-click update",
    # ---- 顶部官方版本条 ----
    "🌐 官方 GitHub master：检测中…": "🌐 Official GitHub master: checking…",
    "📦 npm 发布版：检测中…": "📦 npm release: checking…",
    # ---- 安装列表 ----
    "本机检测到的 DeepSeek Harness 安装（悬停“类型/状态/性质”列查看说明）":
        "DeepSeek Harness installs found on this PC (hover 类型/Status/Nature columns for details)"
        .replace("类型", "Type"),
    "类型": "Type", "位置": "Location", "当前版本": "Current version",
    "版本性质": "Version nature", "官方参考版本": "Official version", "状态": "Status",
    # ---- 操作按钮 ----
    "⬇ 更新所选安装": "⬇ Update selected",
    "🧩 插件检测": "🧩 Plugin scan",
    "📚 技能检测": "📚 Skill scan",
    "🔄 重新检测": "🔄 Rescan",
    "⚙ 数据目录": "⚙ Data folder",
    "💾 导出 CSV": "💾 Export CSV",
    "🌙 深色模式": "🌙 Dark mode",
    "☀️ 浅色模式": "☀️ Light mode",
    # ---- 偏好设置 ----
    "⚙ 偏好设置": "⚙ Preferences",
    "使用 GPU 加速": "Use GPU acceleration",
    "DSH 暂无 GPU 加速选项，仅记录偏好，暂不影响行为。":
        "DSH has no GPU acceleration option yet; this only records a preference.",
    "📂 打开设置文件": "📂 Open settings file",
    "语言": "Language",
    "跟随系统": "Follow system",
    "切换语言后界面立即重建": "The UI rebuilds immediately after switching",
    "偏好已保存：GPU 加速 {state}": "Preference saved: GPU acceleration {state}",
    "开启": "on", "关闭": "off",
    "偏好保存失败，详见日志": "Failed to save preference; see log",
    # ---- 进度与状态 ----
    "当前任务": "Current task",
    "等待任务…": "Idle…",
    "准备中…": "Preparing…",
    "日志 / 进度": "Log / Progress",
    "就绪": "Ready",
    "完成": "Done",
    "开始更新": "Start update",
    "取消": "Cancel",
    "关闭窗口": "Close",
    "当前版本 v{ver} · 检查更新": "v{ver} · Check for updates",
}


TABLES["zh-TW"] = {
    "DeepSeek Harness 自动检测与更新器": "DeepSeek Harness 自動偵測與更新器",
    "DeepSeek Harness 更新器": "DeepSeek Harness 更新器",
    "检查更新器自身更新": "檢查更新器自身更新",
    "自动检测本机安装 · 对比官方版本 · 插件/技能扫描 · 一键更新":
        "自動偵測本機安裝 · 比對官方版本 · 外掛/技能掃描 · 一鍵更新",
    "🌐 官方 GitHub master：检测中…": "🌐 官方 GitHub master：偵測中…",
    "📦 npm 发布版：检测中…": "📦 npm 發行版：偵測中…",
    "本机检测到的 DeepSeek Harness 安装（悬停“类型/状态/性质”列查看说明）":
        "本機偵測到的 DeepSeek Harness 安裝（將游標移到「類型/狀態/性質」欄可看說明）",
    "类型": "類型", "位置": "位置", "当前版本": "目前版本",
    "版本性质": "版本性質", "官方参考版本": "官方參考版本", "状态": "狀態",
    "⬇ 更新所选安装": "⬇ 更新所選安裝",
    "🧩 插件检测": "🧩 外掛偵測",
    "📚 技能检测": "📚 技能偵測",
    "🔄 重新检测": "🔄 重新偵測",
    "⚙ 数据目录": "⚙ 資料目錄",
    "💾 导出 CSV": "💾 匯出 CSV",
    "🌙 深色模式": "🌙 深色模式",
    "☀️ 浅色模式": "☀️ 淺色模式",
    "⚙ 偏好设置": "⚙ 偏好設定",
    "使用 GPU 加速": "使用 GPU 加速",
    "DSH 暂无 GPU 加速选项，仅记录偏好，暂不影响行为。":
        "DSH 目前沒有 GPU 加速選項，這裡只記錄偏好，暫不影響行為。",
    "📂 打开设置文件": "📂 開啟設定檔",
    "语言": "語言",
    "跟随系统": "跟隨系統",
    "切换语言后界面立即重建": "切換語言後介面會立即重建",
    "偏好已保存：GPU 加速 {state}": "偏好已儲存：GPU 加速 {state}",
    "开启": "開啟", "关闭": "關閉",
    "偏好保存失败，详见日志": "偏好儲存失敗，詳見日誌",
    "当前任务": "目前任務",
    "等待任务…": "等待任務…",
    "准备中…": "準備中…",
    "日志 / 进度": "日誌 / 進度",
    "就绪": "就緒",
    "完成": "完成",
    "开始更新": "開始更新",
    "取消": "取消",
    "关闭窗口": "關閉視窗",
    "当前版本 v{ver} · 检查更新": "目前版本 v{ver} · 檢查更新",
}


TABLES["ja"] = {
    "DeepSeek Harness 自动检测与更新器": "DeepSeek Harness 自動検出・更新ツール",
    "DeepSeek Harness 更新器": "DeepSeek Harness アップデーター",
    "检查更新器自身更新": "アップデーター自体の更新を確認",
    "自动检测本机安装 · 对比官方版本 · 插件/技能扫描 · 一键更新":
        "本機のインストールを自動検出 · 公式版と比較 · プラグイン/スキル走査 · ワンクリック更新",
    "🌐 官方 GitHub master：检测中…": "🌐 公式 GitHub master：確認中…",
    "📦 npm 发布版：检测中…": "📦 npm リリース版：確認中…",
    "本机检测到的 DeepSeek Harness 安装（悬停“类型/状态/性质”列查看说明）":
        "本機で検出した DeepSeek Harness（「種類/状態/性質」列にカーソルで説明を表示）",
    "类型": "種類", "位置": "場所", "当前版本": "現在のバージョン",
    "版本性质": "バージョン性質", "官方参考版本": "公式リファレンス", "状态": "状態",
    "⬇ 更新所选安装": "⬇ 選択項目を更新",
    "🧩 插件检测": "🧩 プラグイン走査",
    "📚 技能检测": "📚 スキル走査",
    "🔄 重新检测": "🔄 再検出",
    "⚙ 数据目录": "⚙ データフォルダ",
    "💾 导出 CSV": "💾 CSV 出力",
    "🌙 深色模式": "🌙 ダークモード",
    "☀️ 浅色模式": "☀️ ライトモード",
    "⚙ 偏好设置": "⚙ 環境設定",
    "使用 GPU 加速": "GPU アクセラレーションを使う",
    "DSH 暂无 GPU 加速选项，仅记录偏好，暂不影响行为。":
        "DSH にはまだ GPU アクセラレーション設定がありません。ここでは設定を記録するだけです。",
    "📂 打开设置文件": "📂 設定ファイルを開く",
    "语言": "言語",
    "跟随系统": "システムに従う",
    "切换语言后界面立即重建": "言語を切り替えると画面がすぐ再構築されます",
    "偏好已保存：GPU 加速 {state}": "設定を保存しました：GPU アクセラレーション {state}",
    "开启": "オン", "关闭": "オフ",
    "偏好保存失败，详见日志": "設定の保存に失敗しました。ログを確認してください",
    "当前任务": "現在のタスク",
    "等待任务…": "待機中…",
    "准备中…": "準備中…",
    "日志 / 进度": "ログ / 進捗",
    "就绪": "準備完了",
    "完成": "完了",
    "开始更新": "更新を開始",
    "取消": "キャンセル",
    "关闭窗口": "閉じる",
    "当前版本 v{ver} · 检查更新": "現在 v{ver} · 更新を確認",
}


TABLES["ko"] = {
    "DeepSeek Harness 自动检测与更新器": "DeepSeek Harness 자동 감지 및 업데이터",
    "DeepSeek Harness 更新器": "DeepSeek Harness 업데이터",
    "检查更新器自身更新": "업데이터 자체 업데이트 확인",
    "自动检测本机安装 · 对比官方版本 · 插件/技能扫描 · 一键更新":
        "로컬 설치 자동 감지 · 공식 버전 비교 · 플러그인/스킬 검사 · 원클릭 업데이트",
    "🌐 官方 GitHub master：检测中…": "🌐 공식 GitHub master: 확인 중…",
    "📦 npm 发布版：检测中…": "📦 npm 배포판: 확인 중…",
    "本机检测到的 DeepSeek Harness 安装（悬停“类型/状态/性质”列查看说明）":
        "이 PC에서 감지된 DeepSeek Harness 설치 (유형/상태/성질 열에 마우스를 올리면 설명 표시)",
    "类型": "유형", "位置": "위치", "当前版本": "현재 버전",
    "版本性质": "버전 성질", "官方参考版本": "공식 버전", "状态": "상태",
    "⬇ 更新所选安装": "⬇ 선택 항목 업데이트",
    "🧩 插件检测": "🧩 플러그인 검사",
    "📚 技能检测": "📚 스킬 검사",
    "🔄 重新检测": "🔄 다시 검사",
    "⚙ 数据目录": "⚙ 데이터 폴더",
    "💾 导出 CSV": "💾 CSV 내보내기",
    "🌙 深色模式": "🌙 다크 모드",
    "☀️ 浅色模式": "☀️ 라이트 모드",
    "⚙ 偏好设置": "⚙ 환경 설정",
    "使用 GPU 加速": "GPU 가속 사용",
    "DSH 暂无 GPU 加速选项，仅记录偏好，暂不影响行为。":
        "DSH에는 아직 GPU 가속 옵션이 없습니다. 여기서는 설정만 기록합니다.",
    "📂 打开设置文件": "📂 설정 파일 열기",
    "语言": "언어",
    "跟随系统": "시스템 설정 따르기",
    "切换语言后界面立即重建": "언어를 바꾸면 화면이 즉시 다시 만들어집니다",
    "偏好已保存：GPU 加速 {state}": "설정 저장됨: GPU 가속 {state}",
    "开启": "켜기", "关闭": "끄기",
    "偏好保存失败，详见日志": "설정 저장 실패, 로그를 확인하세요",
    "当前任务": "현재 작업",
    "等待任务…": "대기 중…",
    "准备中…": "준비 중…",
    "日志 / 进度": "로그 / 진행률",
    "就绪": "준비됨",
    "完成": "완료",
    "开始更新": "업데이트 시작",
    "取消": "취소",
    "关闭窗口": "닫기",
    "当前版本 v{ver} · 检查更新": "현재 v{ver} · 업데이트 확인",
}


# ---------------------------------------------------------------------------
# 语言解析
# ---------------------------------------------------------------------------
# 批量翻译数据放在 i18n_data.py（按语言分批 update，便于增量补齐）。
# 这里的 TABLES 作为基础，i18n_data 里的条目优先。
from i18n_data import TABLES as _DATA_TABLES

for _lang, _tbl in _DATA_TABLES.items():
    TABLES.setdefault(_lang, {}).update(_tbl)


def normalize_language(raw: str | None) -> str | None:
    """把各种系统写法归一成我们的语言码；识别不了返回 None。"""
    if not raw:
        return None
    key = str(raw).strip().lower().replace("_", "-")
    if key in LANGUAGE_CODES:
        return key
    if key in (AUTO, ""):
        return None
    for alias, code in _ALIASES:
        if key == alias or key.startswith(alias + "-"):
            return code
    # 只剩主语言标签时（例如 "zh-Hans-CN"）再退一步用前缀匹配
    head = key.split("-")[0]
    for alias, code in _ALIASES:
        if head == alias.split("-")[0]:
            return code
    return None


def _langid_to_code(langid: int) -> str | None:
    """Windows LANGID → 语言码（纯函数，便于测试）。

    LANGID 低 10 位是主语言，高 6 位是 sublanguage。中文必须再分简繁，
    否则会误判。SUBLANG 取值：1=台湾繁体、2=大陆简体、3=香港、4=新加坡、5=澳门。
    （注意：1 才是繁体，别记成 3。）
    """
    primary = langid & 0x03FF
    sub = (langid >> 10) & 0x3F
    if primary == 0x04:                      # Chinese
        return "zh-TW" if sub in (1, 3, 5) else "zh-CN"
    return {0x09: "en", 0x11: "ja", 0x12: "ko"}.get(primary)


def detect_system_language() -> str:
    """探测系统语言，识别不了则回退简体中文。

    优先用 Windows 的 UI 语言 API（比 locale 更贴近用户实际看到的界面语言），
    失败再退到 locale / 环境变量，最后回退简体中文。
    """
    # 1) Windows：GetUserDefaultUILanguage 返回 LANGID
    try:
        import ctypes
        langid = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
        code = _langid_to_code(langid)
        if code:
            return code
    except Exception:  # noqa: BLE001
        pass
    # 2) locale
    for getter in (lambda: locale.getlocale()[0], lambda: locale.getdefaultlocale()[0]):
        try:
            code = normalize_language(getter())
            if code:
                return code
        except Exception:  # noqa: BLE001
            pass
    # 3) 环境变量
    for env in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        code = normalize_language(os.environ.get(env))
        if code:
            return code
    return SOURCE_LANG


def resolve_language(setting: str | None = None) -> str:
    """把设置值解析成实际语言码。setting 为 None 时用当前设置值。"""
    raw = _setting if setting is None else setting
    if raw and raw != AUTO:
        code = normalize_language(raw)
        if code:
            return code
    return detect_system_language()


def set_language(setting: str) -> str:
    """设置语言（可传 "auto"），返回解析后的实际语言码。"""
    global _current, _setting
    _setting = setting or AUTO
    _current = resolve_language(_setting)
    return _current


def get_language() -> str:
    """当前实际生效的语言码。"""
    return _current


def get_language_setting() -> str:
    """当前设置值（可能是 "auto"）。"""
    return _setting


def t(text: str, **kwargs) -> str:
    """翻译一段简体中文原文。

    * 简体中文环境下原样返回，零开销；
    * 缺翻译时回退原文，界面不会空白；
    * 传了关键字参数则做 `{name}` 占位符替换；
    * 译文里的占位符写错会抛异常，因此替换失败时回退到原文而不是崩溃。
    """
    out = text
    if _current != SOURCE_LANG:
        table = TABLES.get(_current)
        if table:
            out = table.get(text, text)
    if kwargs:
        try:
            out = out.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            out = text
    return out


def language_display_name(code: str) -> str:
    """语言码 → 该语言的自称（用于下拉框）。"""
    for c, native, _ in LANGUAGES:
        if c == code:
            return native
    return code


def coverage(code: str) -> int:
    """该语言已录入的翻译条数（用于统计/自检）。"""
    return len(TABLES.get(code, {}))


# 模块导入时先按系统语言初始化一次，GUI 稍后会用设置值覆盖
_current = detect_system_language()
