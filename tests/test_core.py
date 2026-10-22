# -*- coding: utf-8 -*-
"""updater_core 冒烟测试。

设计原则：
  * 不联网、不读写真实用户目录（全部用 pytest 的 tmp_path）；
  * 只覆盖纯函数与关键安全逻辑，跑得快（目标 < 1 秒）；
  * 重点保护「源码检出识别」这条安全阀——它决定了更新时会不会误替换目录。

运行：python -m pytest -q
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

import i18n
import updater_core as core

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 辅助：构造一个合法的源码检出目录
# ---------------------------------------------------------------------------
def make_checkout(root: Path, *, name: str = "@deepseek-ai/dsh-root",
                  cli_form: str = "package.json", version: str = "0.1.5") -> Path:
    """在 root 下造一个源码检出。cli_form 可选 package.json / bin.ts / none。"""
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        json.dumps({"name": name, "version": version}), encoding="utf-8")
    if cli_form == "package.json":
        cli = root / "apps" / "cli"
        cli.mkdir(parents=True, exist_ok=True)
        (cli / "package.json").write_text("{}", encoding="utf-8")
    elif cli_form == "bin.ts":
        src = root / "apps" / "cli" / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "bin.ts").write_text("// bin", encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# 版本号解析与比较
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("1.2.3", (1, 2, 3, "")),
    ("v1.2.3", (1, 2, 3, "")),                 # v 前缀需被接受
    ("0.1.0-rc.5", (0, 1, 0, "rc.5")),
    ("1.2.3-alpha.1", (1, 2, 3, "alpha.1")),
    ("", (0, 0, 0, "")),                       # 空串兜底
])
def test_version_key(raw, expected):
    assert core.version_key(raw) == expected


def test_version_key_unparsable_falls_back():
    # 无法解析时不应抛异常，且保持原串小写（保证排序时不崩）
    assert core.version_key("not-a-version") == (0, 0, 0, "not-a-version")
    assert core.version_key("1.2") == (0, 0, 0, "1.2")


@pytest.mark.parametrize("a,b,expected", [
    ("1.2.3", "1.2.2", 1),
    ("1.2.2", "1.2.3", -1),
    ("1.2.3", "1.2.3", 0),
    ("v0.1.5", "0.1.5", 0),                    # v 前缀不影响相等判定
    ("0.1.0-rc.5", "0.1.3-alpha.1", -1),       # 与自检里的示例一致
    ("1.0.0", "0.9.9", 1),
])
def test_compare_versions(a, b, expected):
    assert core.compare_versions(a, b) == expected


def test_compare_versions_is_antisymmetric():
    assert core.compare_versions("1.2.3", "2.0.0") == -core.compare_versions("2.0.0", "1.2.3")


def test_parse_package_version():
    text = '{\n  "name": "@deepseek-ai/dsh",\n  "version": "0.1.5-rc.1"\n}'
    assert core._parse_package_version(text) == "0.1.5-rc.1"
    assert core._parse_package_version("{}") == ""


@pytest.mark.parametrize("version,grade", [
    ("1.2.3", "stable"),
    ("0.1.5-rc.1", "candidate"),
    ("0.1.3-alpha.1", "prerelease"),
    ("1.0.0-beta", "prerelease"),
    ("", "unstable"),
])
def test_grade_by_suffix(version, grade):
    assert core._grade_by_suffix(version) == grade


# ---------------------------------------------------------------------------
# 格式化函数
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n,expected", [
    (0, "0 B"),
    (512, "512 B"),
    (1024, "1.0 KB"),
    (1536, "1.5 KB"),
    (1024 ** 2, "1.00 MB"),
    (1024 ** 3, "1.00 GB"),
])
def test_human_size(n, expected):
    assert core.human_size(n) == expected


@pytest.mark.parametrize("seconds,expected", [
    (float("nan"), "计算中…"),
    (-1, "计算中…"),
    (30, "30 秒"),
    (90, "1 分 30 秒"),
])
def test_fmt_eta(seconds, expected):
    assert core._fmt_eta(seconds) == expected


def test_fmt_dl_progress_reports_percentage_and_speed():
    total = 50 * 1024 * 1024
    text = core._fmt_dl_progress(total // 2, total, 10.0)
    assert "50%" in text
    assert "MB/s" in text


# ---------------------------------------------------------------------------
# 源码检出识别（安全阀：识别错就会误替换目录）
# ---------------------------------------------------------------------------
def test_is_source_checkout_accepts_valid(tmp_path):
    assert core._is_source_checkout(make_checkout(tmp_path / "a")) is True


def test_is_source_checkout_accepts_bin_ts_form(tmp_path):
    assert core._is_source_checkout(make_checkout(tmp_path / "b", cli_form="bin.ts")) is True


def test_is_source_checkout_rejects_wrong_package_name(tmp_path):
    p = make_checkout(tmp_path / "c", name="@deepseek-ai/dsh")
    assert core._is_source_checkout(p) is False


def test_is_source_checkout_rejects_missing_cli_form(tmp_path):
    p = make_checkout(tmp_path / "d", cli_form="none")
    assert core._is_source_checkout(p) is False


def test_is_source_checkout_rejects_missing_package_json(tmp_path):
    (tmp_path / "e").mkdir()
    assert core._is_source_checkout(tmp_path / "e") is False


def test_is_source_checkout_rejects_broken_json(tmp_path):
    p = tmp_path / "f"
    p.mkdir()
    (p / "package.json").write_text("{ not json", encoding="utf-8")
    assert core._is_source_checkout(p) is False


def test_is_source_checkout_rejects_backup_dir(tmp_path):
    """备份目录绝不能被识别为检出，否则会备份套备份、无限膨胀。"""
    p = make_checkout(tmp_path / "dsh.dsh-bak-20260910-140000")
    assert core._is_source_checkout(p) is False


def test_read_dir_version(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "@deepseek-ai/dsh-root", "version": "9.9.9"}), encoding="utf-8")
    assert core._read_dir_version(tmp_path) == "9.9.9"
    # 缺失或损坏时返回空串而不抛异常
    assert core._read_dir_version(tmp_path / "nope") == ""


# ---------------------------------------------------------------------------
# 技能版本解析
# ---------------------------------------------------------------------------
def test_parse_skill_version_top_level(tmp_path):
    d = tmp_path / "skill-a"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: demo\nversion: 1.2.3\n---\n\n正文\n", encoding="utf-8")
    assert core.parse_skill_version(d) == "1.2.3"


def test_parse_skill_version_metadata_section(tmp_path):
    d = tmp_path / "skill-b"
    d.mkdir()
    (d / "SKILL.md").write_text(
        '---\nname: demo\nmetadata:\n  version: "2.0.0"\n---\n\n正文\n', encoding="utf-8")
    assert core.parse_skill_version(d) == "2.0.0"


def test_parse_skill_version_without_frontmatter(tmp_path):
    d = tmp_path / "skill-c"
    d.mkdir()
    (d / "SKILL.md").write_text("没有 frontmatter 的正文\n", encoding="utf-8")
    assert core.parse_skill_version(d) is None
    # 连 SKILL.md 都没有
    assert core.parse_skill_version(tmp_path / "skill-nonexistent") is None


# ---------------------------------------------------------------------------
# 目录体积统计
# ---------------------------------------------------------------------------
def test_dir_size_counts_nested_files(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"x" * 100)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_bytes(b"y" * 200)
    assert core.dir_size(tmp_path) == 300


def test_dir_size_always_skips_git_but_honours_skip_dirs(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"x" * 10)
    git = tmp_path / ".git"
    git.mkdir()
    (git / "pack").write_bytes(b"z" * 500)
    modules = tmp_path / "node_modules"
    modules.mkdir()
    (modules / "m.js").write_bytes(b"w" * 500)

    # .git 无条件跳过；node_modules 默认计入
    assert core.dir_size(tmp_path) == 510
    # 显式跳过 node_modules 后只剩 a.txt
    assert core.dir_size(tmp_path, skip_dirs=("node_modules",)) == 10


# ---------------------------------------------------------------------------
# 去重逻辑
# ---------------------------------------------------------------------------
def test_norm_path_key_is_stable_for_str_and_path(tmp_path):
    p = tmp_path / "sub"
    assert core._norm_path_key(p) == core._norm_path_key(str(p))


def test_dedupe_installs_keeps_first_and_reports_removed(tmp_path):
    target = str(tmp_path / "install")
    first = {"path": target, "kind": "source"}
    second = {"path": target, "kind": "npm"}
    result = core._dedupe_installs([first, second])
    assert len(result["installs"]) == 1
    assert result["installs"][0]["kind"] == "source"   # 保留第一次出现的
    assert len(result["removed"]) == 1


def test_dedupe_scan_items(tmp_path):
    dup = str(tmp_path / "dup")
    other = str(tmp_path / "other")
    result = core._dedupe_scan_items([
        {"path": dup, "name": "a"},
        {"path": dup, "name": "a-again"},
        {"path": other, "name": "b"},
    ])
    assert len(result["items"]) == 2
    assert result["removed"] == 1


# ---------------------------------------------------------------------------
# 常量健全性
# ---------------------------------------------------------------------------
def test_keep_dirs_protects_local_state():
    """更新时必须保留 node_modules 与 .git，否则会丢依赖和 git 历史。"""
    assert "node_modules" in core._KEEP_DIRS
    assert ".git" in core._KEEP_DIRS


def test_github_targets_are_consistent():
    assert core.ZIP_URL.endswith(f"/{core.GITHUB_BRANCH}.zip")
    assert core.GITHUB_REPO in core.RAW_PACKAGE_URL
    assert core.GITHUB_REPO in core.API_COMMIT_URL


# ---------------------------------------------------------------------------
# 检查「更新器自身」是否有新版本
# ---------------------------------------------------------------------------
def test_pick_self_latest_uses_publish_date_not_version_number():
    """本仓库 tag 存在版本号倒挂（v1.0.1 指向的提交比 v0.6.7 更早）。

    因此必须按**发布时间**挑最新发布；若改成按版本号挑，会误报「有新版本」。
    """
    releases = [
        {"tag_name": "v1.0.1", "published_at": "2026-09-05T18:00:00Z", "html_url": "u-old"},
        {"tag_name": "v0.6.7", "published_at": "2026-09-06T04:51:17Z", "html_url": "u-new"},
        {"tag_name": "v1.0.0", "published_at": "2026-09-05T17:00:00Z", "html_url": "u-older"},
    ]
    picked = core._pick_self_latest(releases)
    assert picked["tag"] == "v0.6.7"      # 而不是版本号更大的 v1.0.1
    assert picked["url"] == "u-new"


def test_pick_self_latest_ignores_drafts_and_blank_tags():
    releases = [
        {"tag_name": "v9.9.9", "published_at": "2030-01-01T00:00:00Z", "draft": True},
        {"tag_name": "   ", "published_at": "2030-01-01T00:00:00Z"},
        {"tag_name": "v0.6.7", "published_at": "2026-09-06T04:51:17Z", "html_url": "u"},
    ]
    assert core._pick_self_latest(releases)["tag"] == "v0.6.7"


def test_pick_self_latest_falls_back_to_created_at():
    releases = [
        {"tag_name": "v0.6.5", "published_at": None, "created_at": "2026-09-06T04:09:25Z"},
        {"tag_name": "v0.6.1", "created_at": "2026-09-01T00:00:00Z"},
    ]
    assert core._pick_self_latest(releases)["tag"] == "v0.6.5"


def test_pick_self_latest_handles_empty_and_bad_input():
    assert core._pick_self_latest([]) is None
    assert core._pick_self_latest(None) is None
    assert core._pick_self_latest("not-a-list") is None


def test_self_repo_constants_point_to_this_project():
    assert "dsh-updater" in core.SELF_REPO_URL
    assert core.SELF_REPO_NAME in core.SELF_RELEASES_URL
    assert core.SELF_REPO_NAME in core.SELF_TAGS_URL


def test_fetch_self_latest_reports_newer_release(monkeypatch):
    monkeypatch.setattr(core, "http_get_json", lambda url, timeout=20: [
        {"tag_name": "v0.9.0", "published_at": "2026-10-01T00:00:00Z",
         "html_url": "https://example.com/rel"},
    ])
    r = core.fetch_self_latest("0.6.8")
    assert r["ok"] is True
    assert r["source"] == "release"
    assert r["latest"] == "0.9.0"
    assert r["has_update"] is True
    assert r["url"] == "https://example.com/rel"
    assert r["note"] == ""


def test_fetch_self_latest_reports_up_to_date(monkeypatch):
    monkeypatch.setattr(core, "http_get_json", lambda url, timeout=20: [
        {"tag_name": "v0.6.8", "published_at": "2026-09-11T00:00:00Z",
         "html_url": "https://example.com/v068"},
    ])
    r = core.fetch_self_latest("0.6.8")
    assert r["ok"] is True
    assert r["has_update"] is False
    assert r["note"] == ""


def test_fetch_self_latest_notes_when_remote_is_older(monkeypatch):
    """本地版本尚未发布是正常状态，提示措辞不应说成 tag 倒挂之类异常。"""
    monkeypatch.setattr(core, "http_get_json", lambda url, timeout=20: [
        {"tag_name": "v0.6.7", "published_at": "2026-09-06T04:51:17Z",
         "html_url": "https://example.com/v067"},
    ])
    r = core.fetch_self_latest("0.6.8")
    assert r["ok"] is True
    assert r["has_update"] is False
    assert "尚未发布" in r["note"]
    assert "0.6.7" in r["note"]


def test_fetch_self_latest_falls_back_to_tags(monkeypatch):
    def fake(url, timeout=20):
        if "releases" in url:
            return []                                  # 远端没有 Release
        return [{"name": "v0.6.7"}, {"name": "v0.6.5"}]
    monkeypatch.setattr(core, "http_get_json", fake)
    r = core.fetch_self_latest("0.6.6")
    assert r["ok"] is True
    assert r["source"] == "tag"
    assert r["latest"] == "0.6.7"
    assert r["has_update"] is True


def test_fetch_self_latest_returns_error_instead_of_raising(monkeypatch):
    def boom(url, timeout=20):
        raise OSError("network down")
    monkeypatch.setattr(core, "http_get_json", boom)
    r = core.fetch_self_latest("0.6.8")
    assert r["ok"] is False
    assert r["error"]
    assert r["has_update"] is False


# ---------------------------------------------------------------------------
# 源码版打包脚本（本地与 CI 共用）
# ---------------------------------------------------------------------------
def test_read_app_version_looks_like_a_version():
    import pack_source
    ver = pack_source.read_app_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", ver), ver


def test_build_source_zip_structure(tmp_path):
    import pack_source
    out = pack_source.build_source_zip("9.9.9", tmp_path)
    assert out.is_file()
    assert out.name == "dsh-updater-src-v9.9.9.zip"
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    # 顶层目录必须带版本号，且只含清单内的文件
    payload = pack_source.source_payload()
    assert len(names) == len(payload)
    assert all(n.startswith("dsh-updater-src-v9.9.9/") for n in names)
    assert "dsh-updater-src-v9.9.9/updater_core.py" in names
    assert "dsh-updater-src-v9.9.9/updater_gui.pyw" in names
    # 语言包必须跟着走（v0.7.7 漏过：解压即 ModuleNotFoundError）
    assert "dsh-updater-src-v9.9.9/i18n.py" in names
    assert "dsh-updater-src-v9.9.9/i18n_data.py" in names


def test_build_source_zip_refuses_when_file_missing(tmp_path, monkeypatch):
    import pack_source
    monkeypatch.setattr(pack_source, "SOURCE_FILES",
                        ("updater_core.py", "这个文件不存在.xyz"))
    with pytest.raises(FileNotFoundError):
        pack_source.build_source_zip("9.9.9", tmp_path)


def test_release_notes_mention_current_version():
    """防呆：升了 APP_VERSION 却忘记同步 RELEASE_NOTES.md 时，让 CI 直接失败。

    这正是 v0.6.8 发布时踩过的坑——Release 说明是自动生成的，没有任何功能描述。
    """
    import pack_source
    ver = pack_source.read_app_version()
    notes = (REPO_ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert ver in notes, f"RELEASE_NOTES.md 未提及当前版本 v{ver}，发布前请更新"


# ---------------------------------------------------------------------------
# 本地偏好设置
# ---------------------------------------------------------------------------
def test_settings_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.load_settings()["gpu_acceleration"] is False        # 默认关
    assert core.save_settings({"gpu_acceleration": True}) is True
    assert core.load_settings()["gpu_acceleration"] is True
    assert core.save_settings({"gpu_acceleration": False}) is True
    assert core.load_settings()["gpu_acceleration"] is False


def test_settings_missing_dir_returns_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path / "not-created"))
    assert core.load_settings() == core.SETTINGS_DEFAULTS


def test_settings_corrupted_file_returns_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    core.settings_file().write_text("{ 这不是 json", encoding="utf-8")
    assert core.load_settings()["gpu_acceleration"] is False


def test_settings_non_dict_json_returns_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    core.settings_file().write_text("[1, 2, 3]", encoding="utf-8")
    assert core.load_settings()["gpu_acceleration"] is False


def test_settings_rejects_wrong_type_and_unknown_keys(monkeypatch, tmp_path):
    """外部写坏的设置不应把垃圾数据带进程序。"""
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    core.settings_file().write_text(
        json.dumps({"gpu_acceleration": "yes", "evil_key": True}), encoding="utf-8")
    loaded = core.load_settings()
    assert loaded["gpu_acceleration"] is False      # 类型不符 → 回退默认值
    assert "evil_key" not in loaded                 # 未声明的键被丢弃


def test_settings_save_leaves_no_temp_file(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.save_settings({"gpu_acceleration": True}) is True
    assert list(tmp_path.glob("*.tmp")) == []       # 原子写入，不留临时文件
    assert core.settings_file().name == "settings.json"


def test_settings_save_failure_returns_false(monkeypatch, tmp_path):
    """目标目录无法创建时应返回 False，而不是抛异常打断界面。"""
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")       # 用文件占住路径
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(blocker / "sub"))
    assert core.save_settings({"gpu_acceleration": True}) is False


# ---------------------------------------------------------------------------
# 多语言（i18n）
# ---------------------------------------------------------------------------
def test_langid_to_code_simplified_vs_traditional():
    """简体/繁体必须分清——这里写错过一次，把简体误判成繁体。"""
    assert i18n._langid_to_code(0x0804) == "zh-CN"      # 大陆简体
    assert i18n._langid_to_code(0x1004) == "zh-CN"      # 新加坡简体
    assert i18n._langid_to_code(0x0404) == "zh-TW"      # 台湾繁体
    assert i18n._langid_to_code(0x0C04) == "zh-TW"      # 香港
    assert i18n._langid_to_code(0x1404) == "zh-TW"      # 澳门
    assert i18n._langid_to_code(0x0409) == "en"
    assert i18n._langid_to_code(0x0411) == "ja"
    assert i18n._langid_to_code(0x0412) == "ko"
    assert i18n._langid_to_code(0x0407) is None         # 德语未支持 → 回退


@pytest.mark.parametrize("raw,expected", [
    ("zh-CN", "zh-CN"), ("zh_CN", "zh-CN"), ("zh-Hans", "zh-CN"), ("zh", "zh-CN"),
    ("zh-TW", "zh-TW"), ("zh_HK", "zh-TW"), ("zh-Hant", "zh-TW"),
    ("en-US", "en"), ("en", "en"),
    ("ja-JP", "ja"), ("ko-KR", "ko"),
    ("de-DE", None), ("", None), ("auto", None),
])
def test_normalize_language(raw, expected):
    assert i18n.normalize_language(raw) == expected


def test_t_falls_back_to_source_text():
    """缺翻译时回退原文，绝不返回空串——否则界面会出现空白。"""
    old = i18n.get_language()
    try:
        i18n.set_language("en")
        assert i18n.t("这条肯定没翻译过") == "这条肯定没翻译过"
    finally:
        i18n.set_language(old)


def test_t_returns_source_unchanged_in_chinese():
    old = i18n.get_language()
    try:
        i18n.set_language("zh-CN")
        assert i18n.t("就绪") == "就绪"
        assert i18n.t("任意未翻译内容") == "任意未翻译内容"
    finally:
        i18n.set_language(old)


def test_t_supports_placeholders_in_all_languages():
    old = i18n.get_language()
    try:
        for code in i18n.LANGUAGE_CODES:
            i18n.set_language(code)
            out = i18n.t("当前版本 v{ver} · 检查更新", ver="9.9.9")
            assert "9.9.9" in out, f"{code} 占位符未替换"
    finally:
        i18n.set_language(old)


def test_t_bad_placeholder_falls_back_instead_of_raising():
    """译文写错占位符时不能把界面搞崩。"""
    old = i18n.get_language()
    try:
        i18n.set_language("en")
        assert i18n.t("当前版本 v{ver} · 检查更新", wrong="x") == "当前版本 v{ver} · 检查更新"
    finally:
        i18n.set_language(old)


def test_every_supported_language_has_some_translations():
    for code in i18n.LANGUAGE_CODES:
        if code == i18n.SOURCE_LANG:
            continue
        assert i18n.coverage(code) > 0, f"{code} 没有任何翻译"


def test_language_setting_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.load_settings()["language"] == "auto"        # 默认跟随系统
    core.save_settings({**core.load_settings(), "language": "ja"})
    assert core.load_settings()["language"] == "ja"


# ---------------------------------------------------------------------------
# 检测结果缓存
# ---------------------------------------------------------------------------
def test_detection_cache_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    result = {"installs": [{"kind": "source", "path": "D:/x", "version": "1.2.3"}],
              "duplicates": 2}
    stamp = core.save_detection_cache(result, saved_at="2026-09-10T18:30:00")
    assert stamp == "2026-09-10T18:30:00"
    cached = core.load_detection_cache()
    assert cached["saved_at"] == stamp
    assert cached["result"]["installs"][0]["kind"] == "source"
    assert cached["result"]["duplicates"] == 2


def test_detection_cache_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path / "nope"))
    assert core.load_detection_cache() == {}


def test_detection_cache_corrupted_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    core.cache_file().write_text("{ 坏掉的 json", encoding="utf-8")
    assert core.load_detection_cache() == {}


def test_detection_cache_wrong_shape_returns_empty(monkeypatch, tmp_path):
    """结构不对（缺 result，或 result 不是 dict）也要走「无缓存」路径。"""
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    core.cache_file().write_text('{"saved_at": "2026-09-10T18:30:00"}', encoding="utf-8")
    assert core.load_detection_cache() == {}
    core.cache_file().write_text('{"saved_at": "x", "result": [1, 2]}', encoding="utf-8")
    assert core.load_detection_cache() == {}


def test_cache_time_text_formats_and_falls_back():
    assert core.cache_time_text("2026-09-10T18:30:00") == "2026-09-10 18:30"
    assert core.cache_time_text("") == ""
    # 解析不了时不应抛异常
    assert core.cache_time_text("garbage") == "garbage"


def test_save_detection_cache_handles_unserializable_values(monkeypatch, tmp_path):
    """检测结果里混入 Path 等类型时也要能存下来（default=str 兜底）。"""
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.save_detection_cache({"path": tmp_path}) != ""
    assert core.load_detection_cache()["result"]["path"] == str(tmp_path)


# ---------------------------------------------------------------------------
# 插件 / 技能的下载来源
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name,expected", [
    ("dsh-whale-widget", "https://www.npmjs.com/package/dsh-whale-widget"),
    ("@deepseek-ai/dsh-base", "https://www.npmjs.com/package/@deepseek-ai/dsh-base"),
    ("", ""), ("（未指定）", ""), ("—", ""),
])
def test_npm_url_for(name, expected):
    assert core.npm_url_for(name) == expected


@pytest.mark.parametrize("raw,expected", [
    ("git@github.com:user/repo.git", "https://github.com/user/repo"),
    ("ssh://git@github.com/user/repo.git", "https://github.com/user/repo"),
    ("https://github.com/user/repo", "https://github.com/user/repo"),
    ("https://github.com/user/repo.git", "https://github.com/user/repo"),
    ("", ""),
])
def test_normalize_git_url(raw, expected):
    assert core.normalize_git_url(raw) == expected


def test_git_remote_url_returns_empty_for_non_git_dir(tmp_path):
    assert core.git_remote_url(tmp_path) == ""
    assert core.git_remote_url(tmp_path / "nope") == ""


def test_remember_source_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.load_sources() == {}
    key = core.source_key("skill", "my-skill")
    assert core.remember_source(key, "https://example.com/skill") is True
    saved = core.load_sources()
    assert saved[key]["url"] == "https://example.com/skill"


def test_remember_source_rejects_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.remember_source("", "https://x") is False
    assert core.remember_source("k", "") is False


def test_source_url_for_plugin_uses_npm_page(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    item = {"name": "dsh-whale-widget", "path": str(tmp_path)}
    assert core.source_url_for(item, "plugin") == \
        "https://www.npmjs.com/package/dsh-whale-widget"


def test_source_url_for_skill_falls_back_to_remembered(monkeypatch, tmp_path):
    """技能没有 git 来源时，应退回此前记住的来源。"""
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    item = {"name": "my-skill", "path": str(tmp_path)}          # tmp_path 不是 git 仓库
    assert core.source_url_for(item, "skill") == ""
    core.remember_source(core.source_key("skill", "my-skill"), "https://example.com/s")
    assert core.source_url_for(item, "skill") == "https://example.com/s"


def test_source_url_for_returns_empty_when_unknown(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.source_url_for({"name": "", "path": ""}, "skill") == ""
    assert core.source_url_for({}, "plugin") == ""


# ---------------------------------------------------------------------------
# 多语言：禁止模块级翻译调用
# ---------------------------------------------------------------------------
def test_no_module_level_translation_calls():
    """模块级的 t() 会在 import 时求值，那时语言还没从设置里加载，
    结果会被永久冻死在导入时的语言上。

    这是实际踩过的坑：GRADE_LABELS 的取值曾被包成 t("稳定版")，
    表现为「版本性质」列显示成上一次会话的语言（如日文），
    而界面其余部分是当前语言。此处做回归防护。
    """
    import ast
    bad = []
    for fname in ("updater_core.py", "updater_gui.pyw"):
        tree = ast.parse((REPO_ROOT / fname).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue                      # 函数/类体内可以用 t()
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                        and sub.func.id == "t"):
                    bad.append(f"{fname}:{sub.lineno}")
    assert not bad, "模块级不得调用 t()（会在导入时冻结语言）：" + ", ".join(bad)


def test_grade_label_follows_current_language():
    """版本性质标签必须按当前语言即时翻译。"""
    old = i18n.get_language()
    try:
        i18n.set_language("ja")
        assert core.grade_label_of("stable") == "安定版"
        i18n.set_language("en")
        assert core.grade_label_of("stable") == "Stable"
        i18n.set_language("zh-CN")
        assert core.grade_label_of("stable") == "稳定版"
        assert core.grade_label_of("") == ""
        assert core.grade_label_of("unknown-grade") == "不稳定版"
    finally:
        i18n.set_language(old)


def test_kind_info_strings_exist_in_tables():
    """KIND_INFO 的值是**折行拼接后的整串**，必须以完整字符串作为键存在于表里。

    这是实际踩过的坑：按 token 提取时会得到各段而不是整条，
    结果整条查不到译文、浮窗回退中文（用户报告「切换语言后类型说明浮窗
    还是一样」）。
    """
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader(
        "updater_gui_probe", str(REPO_ROOT / "updater_gui.pyw"))
    mod = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("updater_gui_probe", loader))
    loader.exec_module(mod)
    missing = []
    for kind, info in mod.KIND_INFO.items():
        for field in ("badge", "title", "what", "role", "how"):
            val = info.get(field)
            if not val:
                continue
            for code in ("zh-TW", "en", "ja", "ko"):
                if val not in i18n.TABLES.get(code, {}):
                    missing.append(f"{code}:{kind}:{field}")
    assert not missing, "KIND_INFO 文案缺翻译：" + ", ".join(sorted(set(missing)))


def test_npm_update_blocked_when_dsh_running(monkeypatch):
    """DSH 在运行时必须拦住 npm 全局更新。

    否则 npm 会替换正在被占用的原生模块（如 sharp-win32-x64-*.node），
    以「EPERM: operation not permitted, unlink ...」失败，并可能留下
    缺少子模块文件的损坏安装树——这正是实际发生过的故障。
    """
    from pathlib import Path as _P
    monkeypatch.setattr(core, "_is_port_open", lambda *a, **k: True)
    with pytest.raises(RuntimeError) as ei:
        core.update_npm_global(_P("."))
    assert "3080" in str(ei.value)


def test_running_node_count_returns_int():
    """无论平台都要返回整数，不能抛异常。"""
    assert isinstance(core.running_node_count(), int)


def test_rebuild_hint_key_translated_in_all_languages():
    """源码更新后「请重新构建」的提示必须四语言齐全。

    这条提示关系到用户能否启动 DSH（构建产物 apps/cli/lib 不在保留列表里），
    缺翻译就会在最需要它的时候显示成看不懂的语言。
    """
    import i18n as _i18n
    NL = chr(92) + "n"
    key = ("注意：原目录中的构建产物（apps/cli/lib）未随源码保留。" + NL +
           "若你用它直接启动 DSH，请重新执行：pnpm install && pnpm run build")
    for code in ("zh-TW", "en", "ja", "ko"):
        assert key in _i18n.TABLES.get(code, {}), f"{code} 缺该提示的翻译"


def test_every_literal_translation_key_exists_in_all_tables():
    """源码里每个 t("...") 字面量键，四种语言都必须有译文。

    专防两类实际发生过的遗漏：
    1. 折行拼接合并后产生的**新模板键**忘了补翻译（会静默回退中文）
    2. 手工重建键时把换行写成了字面量反斜杠+n，导致键不匹配
       （曾让「请先关闭 DSH 再更新 npm」这条重要提示失效）
    """
    import ast
    keys = {}
    for fname in ("updater_gui.pyw", "updater_core.py"):
        tree = ast.parse((REPO_ROOT / fname).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "t" and node.args):
                try:
                    v = ast.literal_eval(node.args[0])
                except Exception:
                    continue
                if isinstance(v, str) and v.strip():
                    keys.setdefault(v, f"{fname}:{node.lineno}")
    assert keys, "没有提取到任何翻译键，提取逻辑可能失效"
    bad = []
    for code in ("zh-TW", "en", "ja", "ko"):
        table = i18n.TABLES.get(code, {})
        for k in keys:
            if k not in table:
                bad.append(f"{code} 缺 {keys[k]} {k[:40]!r}")
    assert not bad, "翻译缺失：\n" + "\n".join(bad[:12])


def test_update_source_accepts_build_flag():
    """update_source_from_zip 必须接受 run_pnpm_build（否则 GUI 传参会 TypeError）。"""
    import inspect
    sig = inspect.signature(core.update_source_from_zip)
    assert "run_pnpm_build" in sig.parameters
    assert sig.parameters["run_pnpm_build"].default is False


def test_run_pnpm_step_reports_missing_pnpm(monkeypatch, tmp_path):
    """找不到 pnpm 时要给出可读错误，而不是静默跳过构建。

    否则用户会拿到"更新成功"却启动失败（缺 client bundles），很难排查。
    """
    monkeypatch.setattr(core.shutil, "which", lambda *a, **k: None)
    with pytest.raises(RuntimeError) as ei:
        core._run_pnpm_step(tmp_path, ["run", "build"], lambda *a: None, "pnpm run build")
    assert "pnpm" in str(ei.value)


# ---------------------------------------------------------------------------
# 更新前自动关闭 DSH
# ---------------------------------------------------------------------------
def test_processes_on_port_returns_list():
    """必须返回列表且不抛异常；空闲端口应为空列表。"""
    assert isinstance(core.processes_on_port(59999), list)
    assert core.processes_on_port(59999) == []


def test_close_dsh_on_free_port_is_noop():
    """端口空闲时不应结束任何进程（这里只能测空闲端口，
    决不能对真实运行的 DSH 调用，否则会打断用户正在用的程序）。"""
    res = core.close_dsh(59999, log=lambda *a: None)
    assert res["ok"] is True
    assert res["closed"] == []
    assert res["errors"] == []


def test_update_paths_go_through_auto_close():
    """两条更新路径（源码 / npm）都必须先经过自动关闭检查。

    否则 DSH 在运行时点更新会直接失败：源码路径被端口检查拦住、
    npm 路径则以 EPERM 中断并可能损坏安装。
    """
    src = (REPO_ROOT / "updater_gui.pyw").read_text(encoding="utf-8")
    assert "def _ensure_dsh_closed" in src
    assert src.count("if not self._ensure_dsh_closed(") >= 2, "应接入源码与 npm 两条路径"


# ---------------------------------------------------------------------------
# 更新历史与回滚
# ---------------------------------------------------------------------------
def _fake_checkout(root, version):
    d = Path(root) / "deepseek-harness-master"
    (d / "apps" / "cli").mkdir(parents=True, exist_ok=True)
    (d / "package.json").write_text(
        json.dumps({"name": "@deepseek-ai/dsh-root", "version": version}), encoding="utf-8")
    return d


def test_history_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.load_history() == []
    assert core.append_history({"kind": "npm", "old_version": "1.0", "new_version": "2.0"})
    h = core.load_history()
    assert len(h) == 1 and h[0]["old_version"] == "1.0"
    assert h[0]["at"], "应自动补上时间"


def test_history_rejects_bad_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    assert core.append_history({}) is False       # 没有 kind
    assert core.append_history("不是一个 dict") is False


def test_list_source_backups_newest_first(tmp_path):
    target = _fake_checkout(tmp_path, "2.0")
    for stamp in ("20260101-000000", "20260202-000000"):
        (tmp_path / (target.name + ".dsh-bak-" + stamp)).mkdir()
    got = core.list_source_backups(target)
    assert [g["stamp"] for g in got] == ["20260202-000000", "20260101-000000"]


def test_rollback_source_swaps_directories(tmp_path):
    """回滚后：当前目录=旧版本，回滚前的状态被另存为新备份（回滚本身可逆）。"""
    target = _fake_checkout(tmp_path, "2.0")
    backup = tmp_path / (target.name + ".dsh-bak-20260101-000000")
    backup.mkdir()
    (backup / "package.json").write_text(
        json.dumps({"name": "@deepseek-ai/dsh-root", "version": "1.0"}), encoding="utf-8")

    res = core.rollback_source(target, backup, log=lambda *a: None)
    assert res["ok"] and res["version"] == "1.0"
    now = json.loads((target / "package.json").read_text(encoding="utf-8"))["version"]
    assert now == "1.0"
    saved = Path(res["saved_current"])
    assert saved.is_dir()
    assert json.loads((saved / "package.json").read_text(encoding="utf-8"))["version"] == "2.0"


def test_rollback_source_rejects_invalid_backup(tmp_path):
    target = _fake_checkout(tmp_path, "2.0")
    bad = tmp_path / (target.name + ".dsh-bak-坏备份")
    bad.mkdir()                                    # 空目录，不是有效检出
    with pytest.raises(RuntimeError):
        core.rollback_source(target, bad, log=lambda *a: None)
    assert (target / "package.json").is_file(), "失败时不能动到当前目录"


def test_rollback_targets_aggregates_three_kinds(tmp_path, monkeypatch):
    monkeypatch.setenv("DSH_UPDATER_SETTINGS_DIR", str(tmp_path))
    target = _fake_checkout(tmp_path, "2.0")
    (tmp_path / (target.name + ".dsh-bak-20260101-000000")).mkdir()
    # 固定扫描结果：否则会把开发机上真实的检出与备份算进来（环境依赖）
    monkeypatch.setattr(core, "find_source_checkouts", lambda *a, **k: [])
    core.append_history({"kind": "source", "path": str(target),
                         "old_version": "1.0", "new_version": "2.0"})
    core.append_history({"kind": "npm", "old_version": "0.9", "new_version": "1.0"})
    t = core.rollback_targets()
    assert len(t["source"]) == 1 and t["source"][0]["from_version"] == "1.0"
    assert len(t["npm"]) == 1 and t["npm"][0]["version"] == "0.9"
    assert t["profile"] == [], "未更新过 profile 时应为空"


def test_all_used_ttk_styles_are_defined():
    """所有 style="X" 用到的 ttk 样式，都必须在 _setup_style 里配置过。

    实际踩过的坑：回滚窗口用了 style="Hint.TLabel"，但这个样式从未定义，
    ttk 拿到未配置的样式名会渲染成一块突兀的黑色背景（深色下尤其明显）。
    """
    import re
    src = (REPO_ROOT / "updater_gui.pyw").read_text(encoding="utf-8")
    used = set(re.findall(r'style\s*=\s*"([^"]+)"', src))
    defined = set(re.findall(r's\.(?:configure|map)\(\s*"([^"]+)"', src))
    missing = sorted(x for x in used if x not in defined)
    assert not missing, "使用了但未定义的 ttk 样式：" + ", ".join(missing)


def test_startup_syncs_palette_with_saved_theme():
    """启动时必须把 CLR 调色板同步成已保存的主题。

    实际踩过的坑：只恢复 _dark 标志、不同步 CLR（模块级调色板导入时固定为
    浅色），会出现「标志是深色、界面却是浅色」的错位，而且下次点切换还会
    反过来（_dark 变 False 却应用深色）。这是 v0.7.7 真实存在的问题。
    """
    src = (REPO_ROOT / "updater_gui.pyw").read_text(encoding="utf-8")
    anchor = 'self._dark = bool(self.settings.get("dark_mode"))'
    assert anchor in src, "找不到恢复主题标志的代码"
    tail = src[src.index(anchor):src.index(anchor) + 900]
    assert "CLR.update(THEMES[" in tail, \
        "恢复 _dark 之后没有同步 CLR —— 会导致标志与配色错位"


# ---------------------------------------------------------------------------
# DSH 插件包：package.json / lib/client.js / updater_core.py --json
# ---------------------------------------------------------------------------
def _plugin_manifest() -> dict:
    return json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8-sig"))


def test_package_version_matches_gui_app_version():
    """package.json 的版本必须和 GUI 的 APP_VERSION 一致。

    插件页显示的是 package.json 的版本，桌面版显示的是 APP_VERSION；
    两个数字一旦岔开，用户会看到两个「当前版本」。
    """
    src = (REPO_ROOT / "updater_gui.pyw").read_text(encoding="utf-8")
    found = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', src)
    assert found, "updater_gui.pyw 里找不到 APP_VERSION"
    assert found.group(1) == _plugin_manifest()["version"], \
        f"package.json={_plugin_manifest()['version']} 与 APP_VERSION={found.group(1)} 不一致"


def _local_python_modules(entry: Path) -> set:
    """从 entry 出发，收集它（含传递依赖）用到的同目录模块文件名。"""
    seen, queue = set(), [entry]
    while queue:
        path = queue.pop()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for name in re.findall(r"^(?:from|import)\s+(i18n\w*)", text, re.M):
            queue.append(REPO_ROOT / f"{name}.py")
    return {p.name for p in seen}


def test_plugin_files_cover_every_runtime_module():
    """package.json 的 files 白名单必须覆盖 updater_core.py 的全部本地依赖。

    插件是按 files 打包后进用户 profile 的（pnpm 只装白名单里的文件）：
    漏掉任何一个 i18n_*.py，Python 侧就 ImportError，检测/回滚在用户机器上
    直接不可用——而本地开发（整仓库都在）完全复现不出来。
    """
    from fnmatch import fnmatch

    patterns = _plugin_manifest()["files"]
    needed = {"index.js", "cordis.patch.yml", "icon.png", "lib/client.js",
              "locale/zh.json", "locale/en.json"} | _local_python_modules(REPO_ROOT / "updater_core.py")
    missing = sorted(name for name in needed
                     if not any(fnmatch(name, pattern) for pattern in patterns))
    assert not missing, "files 白名单漏了这些运行时文件：" + ", ".join(missing)


def test_plugin_client_declaration_is_complete():
    """dsh.client 声明、./client 导出与实际产物三者必须对齐。

    client 半边少一样，插件页里不会有任何报错，只是会话标题栏的按钮不出现。
    """
    manifest = _plugin_manifest()
    assert manifest["dsh"]["client"]["platform"] == "web"
    exported = manifest["exports"]["./client"]
    assert (REPO_ROOT / exported).is_file(), f"{exported} 不存在"
    bundle = (REPO_ROOT / exported).read_text(encoding="utf-8")
    assert "window.__ModuleLoader__.load(" in bundle, "客户端产物必须是闭包工厂格式"
    assert f"id: '{manifest['name']}'" in bundle, "工厂注册的 id 必须等于包名"
    assert (REPO_ROOT / manifest["dsh"]["bundle"]["patch"]).is_file()


def test_bundle_patch_module_name_matches_package_name():
    """cordis.patch.yml 里引用的模块名必须等于 package.json 的包名。

    这两个名字对不上时（例如 npm 包改名后漏改 patch），DSH 装完插件不会报错，
    但 profile 启动时找不到插件模块 —— 按钮和工具都会静默消失。
    """
    manifest = _plugin_manifest()
    patch_path = REPO_ROOT / manifest["dsh"]["bundle"]["patch"]
    text = patch_path.read_text(encoding="utf-8")
    names = re.findall(r"^\s*name:\s*(\S+)\s*$", text, re.M)
    assert names, "cordis.patch.yml 里没找到 name 行"
    assert manifest["name"] in names, (
        f"bundle patch 的 name={names} 与 package.json 包名 {manifest['name']} 不一致")


def test_checkout_detection_tolerates_utf8_bom(tmp_path):
    """package.json 带 BOM 也要能识别。

    Windows 上的记事本 / 部分编辑器会写 BOM，json.loads 遇到 BOM 直接抛错，
    结果是「明明是正确的检出，检测却说不是」——回滚会被安全阀挡下来。
    """
    root = tmp_path / "proj"
    root.mkdir()
    payload = json.dumps({"name": "@deepseek-ai/dsh-root", "version": "1.0"})
    (root / "package.json").write_bytes(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    cli = root / "apps" / "cli"
    cli.mkdir(parents=True)
    (cli / "package.json").write_text("{}", encoding="utf-8")
    assert core._looks_like_checkout_dir(root) is True
    assert core._is_source_checkout(root) is True


def test_cli_detect_offline_never_touches_network(monkeypatch, capsys):
    """--offline 必须一个网络请求都不发（界面靠它秒开）。"""
    touched = []
    monkeypatch.setattr(core, "fetch_official_versions",
                        lambda *a, **k: touched.append("official") or {})
    monkeypatch.setattr(core, "find_source_checkouts", lambda: [])
    monkeypatch.setattr(core, "find_npm_global", lambda: [])
    monkeypatch.setattr(core, "find_profiles", lambda: [])
    code = core._cli_main(["detect", "--offline"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert code == 0 and payload["ok"] is True
    assert payload["data"]["offline"] is True
    assert payload["data"]["official"] is None
    assert touched == [], "--offline 下不允许联网"


def test_cli_detect_reports_installs_without_translation(monkeypatch, capsys):
    """检测结果必须是「机器可读」的：状态码而不是译文。"""
    checkout = Path("D:/fake/deepseek-harness-master")
    monkeypatch.setattr(core, "fetch_official_versions", lambda *a, **k: {})
    monkeypatch.setattr(core, "find_source_checkouts", lambda: [(checkout, "source", "0.2.0")])
    monkeypatch.setattr(core, "find_npm_global", lambda: [])
    monkeypatch.setattr(core, "find_profiles", lambda: [])
    code = core._cli_main(["detect"])
    payload = json.loads(capsys.readouterr().out.strip())
    install = payload["data"]["installs"][0]
    assert code == 0
    assert install["kind"] == "source"
    assert install["version"] == "0.2.0"
    assert install["status"] in {"unknown", "latest", "update-available"}
    assert not re.search(r"[\u4e00-\u9fff]", json.dumps(payload, ensure_ascii=False)), \
        "CLI 结果里不应出现中文文案（前端自己出文案）"


def test_cli_unknown_action_fails_cleanly(capsys):
    code = core._cli_main(["没这个动作"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert code == 1 and payload["ok"] is False
    assert payload["error"], "失败时必须带上原因"


# ---------------------------------------------------------------------------
# 源码版 zip：解压后必须真的能跑
# ---------------------------------------------------------------------------
def test_source_zip_is_runnable(tmp_path):
    """源码版 zip 解压出来必须能 import —— 真实执行，不看清单。

    踩过的坑：v0.7.7 及更早的源码 zip 只装了 7 个文件，漏掉了全部 i18n 模块，
    用户按 README「下载 ZIP」解压后第一行 `from i18n import t` 就
    ModuleNotFoundError。清单类断言挡不住这种漏，必须真的跑一次。
    """
    import subprocess
    import sys
    import zipfile

    import pack_source

    out = pack_source.build_source_zip("9.9.9", tmp_path)
    with zipfile.ZipFile(out) as archive:
        archive.extractall(tmp_path / "x")
    inner = tmp_path / "x" / "dsh-updater-src-v9.9.9"

    done = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", "import updater_core; print('ok')"],
        cwd=inner, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert done.returncode == 0, f"源码版 zip 跑不起来：{done.stderr[-400:]}"

    # 解压后两种用法都要能直接用：桌面版 + DSH 网页插件
    for name in ("package.json", "cordis.patch.yml", "index.js",
                 "lib/client.js", "locale/zh.json", "icon.png"):
        assert (inner / name).is_file(), f"源码版 zip 缺少 {name}"


# ---------------------------------------------------------------------------
# 官方版本抓取：多源并发 + 本地缓存（v0.8.1 检测提速）
# ---------------------------------------------------------------------------
def _official_sample(npm_version="0.2.0-rc.2", gh_version="0.2.1-rc.2"):
    """构造一份「完整」的官方版本结果（两个关键版本号都有）。"""
    data = core._empty_official()
    data["github"].update({"version": gh_version, "ok": True,
                           "tags": ["0.2.1-rc.2", "0.2.0-rc.2"]})
    data["npm"].update({"version": npm_version, "ok": True,
                        "dist_tags": {"latest": npm_version},
                        "versions": [npm_version, "0.2.0-rc.1"]})
    return data


def _fake_http_get_router(seen=None, gh_version="0.2.1-rc.2", npm_version="0.2.0-rc.2"):
    """按 URL 返回合理的官方数据，模拟所有源都可用（不联网）。"""
    def fake_http_get(url, timeout=25.0, binary=False, headers=None):
        if seen is not None:
            seen.append(url)
        if "package.json" in url:
            payload = {"version": gh_version, "engines": {"node": ">=22"}}
        elif url.rstrip("/").endswith("/latest"):
            payload = {"version": npm_version, "engines": {"node": ">=22"}}
        elif "dist-tags" in url:
            payload = {"latest": npm_version}
        elif "commits" in url:
            payload = [{"sha": "abcdef1234",
                        "commit": {"message": "feat: something\n\nbody",
                                   "committer": {"date": "2026-10-01T00:00:00Z"}}}]
        elif "api.github.com" in url and "tags" in url:
            payload = [{"name": "0.2.1-rc.2"}]
        elif "data.jsdelivr.com" in url:
            payload = {"tags": {"0.2.1-rc.2": "sha"}}
        elif "registry" in url:
            payload = {"dist-tags": {"latest": npm_version},
                       "versions": {npm_version: {"engines": {"node": ">=22"}},
                                    "0.2.0-rc.1": {}}}
        else:
            raise AssertionError(f"未预期的 URL：{url}")
        return json.dumps(payload).encode("utf-8")
    return fake_http_get


def test_fetch_official_versions_merges_sources(monkeypatch):
    """GitHub metadata + npm metadata 并发抓取后要能合并成旧结构。"""
    monkeypatch.setattr(core, "http_get", _fake_http_get_router())
    # 这个测试要检查所有数据都合并进来：关掉「必需项到齐就提前返回」的优化，
    # 否则可选项（最近提交 / tags）可能还没来得及写进结果。
    original_probe = core._parallel_probe
    monkeypatch.setattr(core, "_parallel_probe",
                        lambda candidates, budget, required=None:
                            original_probe(candidates, budget, required=None))
    out = core.fetch_official_versions(fresh=True)
    assert out["github"]["version"] == "0.2.1-rc.2"
    assert out["github"]["engines_node"] == ">=22"
    assert out["npm"]["version"] == "0.2.0-rc.2"
    assert out["npm"]["engines_node"] == ">=22"
    assert "0.2.1-rc.2" in out["github"]["tags"]
    assert "0.2.0-rc.2" in out["npm"]["versions"]
    assert out["github"]["recent"], "最近提交应被解析出来"
    assert out["github"]["recent"][0]["sha"] == "abcdef12"


def test_fetch_official_versions_cache_hit_skips_network(monkeypatch):
    """5 分钟内的完整缓存必须零网络直接返回（这正是「检测秒回」的关键）。"""
    core.save_official_cache(_official_sample())
    calls = []

    def boom(*args, **kwargs):
        calls.append(args)
        raise AssertionError("缓存命中时不应该联网")

    monkeypatch.setattr(core, "http_get", boom)
    out = core.fetch_official_versions()
    assert out["npm"]["version"] == "0.2.0-rc.2"
    assert out["github"]["version"] == "0.2.1-rc.2"
    assert calls == []


def test_fetch_official_versions_returns_cache_copy(monkeypatch):
    """缓存返回必须是副本：调用方加了 assess 字段也不该污染下次结果。"""
    core.save_official_cache(_official_sample())
    monkeypatch.setattr(core, "http_get",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应联网")))
    first = core.fetch_official_versions()
    first["github"]["version"] = "tampered"
    first["github"]["assess"] = {"grade": "stable"}
    second = core.fetch_official_versions()
    assert second["github"]["version"] == "0.2.1-rc.2"
    assert "assess" not in second["github"]


def test_fetch_official_versions_fresh_bypasses_cache(monkeypatch):
    core.save_official_cache(_official_sample(npm_version="0.1.0"))
    monkeypatch.setattr(core, "http_get",
                        _fake_http_get_router(npm_version="0.2.0-rc.2"))
    out = core.fetch_official_versions(fresh=True)
    assert out["npm"]["version"] == "0.2.0-rc.2"


def test_incomplete_cache_expires_after_short_ttl(monkeypatch):
    """抓取失败（两个关键版本号缺一个）时缓存只保留 30 秒，别把失败锁 5 分钟。"""
    import datetime as _dt

    incomplete = core._empty_official()
    core.save_official_cache(incomplete)
    calls = []

    def fake(url, timeout=25.0, binary=False, headers=None):
        calls.append(url)
        raise AssertionError("新鲜缓存不应联网")

    monkeypatch.setattr(core, "http_get", fake)
    core.fetch_official_versions()
    assert calls == []

    old = (_dt.datetime.now() - _dt.timedelta(seconds=core.OFFICIAL_FAIL_TTL + 5)
           ).isoformat(timespec="seconds")
    core.save_official_cache(incomplete, saved_at=old)
    monkeypatch.setattr(core, "http_get", _fake_http_get_router(seen=calls))
    out = core.fetch_official_versions()
    assert calls, "不完整缓存超过 OFFICIAL_FAIL_TTL 后必须重新抓取"
    assert out["npm"]["version"] == "0.2.0-rc.2"


def test_complete_cache_survives_fail_ttl(monkeypatch):
    """完整缓存 1 分钟内仍然有效（失败 TTL 不能误伤正常结果）。"""
    import datetime as _dt

    stamp = (_dt.datetime.now() - _dt.timedelta(seconds=60)).isoformat(timespec="seconds")
    core.save_official_cache(_official_sample(), saved_at=stamp)
    monkeypatch.setattr(core, "http_get",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应联网")))
    out = core.fetch_official_versions()
    assert out["github"]["version"] == "0.2.1-rc.2"


def test_merge_keeps_stale_lists_but_never_stale_version():
    """旧缓存只能兜底 tags/versions 清单，不能冒充 latest 版本（否则会误报已是最新）。"""
    previous = _official_sample()
    out = core._merge_official({}, previous)
    assert out["github"]["tags"] == previous["github"]["tags"]
    assert out["npm"]["versions"] == previous["npm"]["versions"]
    assert out["github"]["version"] is None
    assert out["npm"]["version"] is None
    assert out["github"]["error"], "所有源都失败时要留下原因"
    assert out["npm"]["error"]


def test_parallel_probe_runs_candidates_concurrently():
    import time as _time

    def make(delay, value):
        def fn():
            _time.sleep(delay)
            return value
        return fn

    started = _time.perf_counter()
    parts = core._parallel_probe(
        {"a": [make(0.25, "A")], "b": [make(0.25, "B")], "c": [make(0.25, "C")]},
        budget=3.0,
    )
    elapsed = _time.perf_counter() - started
    assert parts == {"a": "A", "b": "B", "c": "C"}
    assert elapsed < 0.6, f"三个 0.25s 请求应并发（实际 {elapsed:.2f}s，串行要 0.75s）"


def test_parallel_probe_exits_when_required_satisfied():
    """必需信息到齐就返回，不为可选项（如 GitHub「最近提交」）干等超时。"""
    import time as _time

    def slow_optional():
        _time.sleep(2.0)
        return "late"

    started = _time.perf_counter()
    parts = core._parallel_probe(
        {"must": [lambda: "ok"], "optional": [slow_optional]},
        budget=5.0, required=[{"must"}],
    )
    elapsed = _time.perf_counter() - started
    assert parts["must"] == "ok"
    assert elapsed < 1.0, f"必需项到齐应立即返回（实际 {elapsed:.2f}s）"


def test_parallel_probe_required_alternative_group():
    """required 每组「任一 key 成功」即可，方便表达「npm 两个通道取其一」。"""
    def boom():
        raise RuntimeError("down")

    parts = core._parallel_probe(
        {"a": [boom], "b": [lambda: "B"], "c": [boom]},
        budget=2.0, required=[{"a", "b"}],
    )
    assert parts["b"] == "B"


def test_probe_npm_latest_parses_engines(monkeypatch):
    monkeypatch.setattr(
        core, "http_get",
        lambda url, timeout=25.0, binary=False, headers=None:
            json.dumps({"version": "1.2.3", "engines": {"node": ">=22"}}).encode())
    probe = core._probe_npm_latest("https://registry.npmjs.org/@deepseek-ai/dsh/latest")
    assert probe["version"] == "1.2.3"
    assert probe["engines_node"] == ">=22"


def test_probe_gh_tags_supports_jsdelivr_dict(monkeypatch):
    """jsDelivr 的 tags 是 {tag: sha} 字典，api.github.com 的则是 [{name}] 列表。"""
    monkeypatch.setattr(
        core, "http_get",
        lambda url, timeout=25.0, binary=False, headers=None:
            json.dumps({"tags": {"v1.2.3": "sha", "dsh-v0.9.0": "sha"}}).encode())
    assert core._probe_gh_tags("https://data.jsdelivr.com/v1/package/gh/x/y") == [
        "v1.2.3", "0.9.0"]


def test_fetch_self_latest_uses_cache(monkeypatch):
    """更新器自身版本检查也缓存 5 分钟：重复点「版本」不再打 GitHub API。"""
    calls = []

    def fake(url, timeout=20):
        calls.append(url)
        return [{"tag_name": "v0.9.0", "published_at": "2026-10-01T00:00:00Z",
                 "html_url": "https://example.com/rel"}]

    monkeypatch.setattr(core, "http_get_json", fake)
    first = core.fetch_self_latest("0.8.0")
    assert first["ok"] is True and first["has_update"] is True
    for _ in range(2):
        again = core.fetch_self_latest("0.8.0")
        assert again["latest"] == "0.9.0"
    assert len(calls) == 1, "缓存命中后不应重复请求 GitHub"
    forced = core.fetch_self_latest("0.8.0", fresh=True)
    assert forced["latest"] == "0.9.0"
    assert len(calls) == 2, "fresh=True 必须跳过缓存"


def test_cli_detect_accepts_fresh_flag(monkeypatch, capsys):
    seen = {}

    def fake_detect(**kwargs):
        seen.update(kwargs)
        return {"installs": [], "official": None, "errors": []}

    monkeypatch.setattr(core, "detect_all", fake_detect)
    code = core._cli_main(["detect", "--fresh"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert code == 0 and payload["ok"] is True
    assert seen.get("fresh") is True


# ---------------------------------------------------------------------------
# 插件内更新 DSH：暂存 → DSH 关闭后看护进程应用（v0.10.0）
# ---------------------------------------------------------------------------
def _make_fake_dsh_zip(path: Path, version: str, *, lock_text: str = "lock: same\n") -> bytes:
    """造一个最小的 DeepSeek Harness 官方源码 zip（能通过 _is_source_checkout）。"""
    root = "deepseek-harness-master"
    files = {
        "package.json": json.dumps(
            {"name": "@deepseek-ai/dsh-root", "version": version}),
        "apps/cli/package.json": json.dumps(
            {"name": "@deepseek-ai/dsh", "version": version}),
        "apps/cli/src/bin.ts": "// cli\n",
        "pnpm-lock.yaml": lock_text,
    }
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            zf.writestr(f"{root}/{name}", content)
    return path.read_bytes()


def _make_checkout_dir(root: Path, version: str, *, build: bool = False,
                       lock_text: str = "lock: same\n") -> Path:
    """造一个本地源码检出（含 node_modules 里的一枚哨兵文件）。"""
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        json.dumps({"name": "@deepseek-ai/dsh-root", "version": version}), encoding="utf-8")
    (root / "apps" / "cli").mkdir(parents=True, exist_ok=True)
    (root / "apps" / "cli" / "package.json").write_text("{}", encoding="utf-8")
    (root / "pnpm-lock.yaml").write_text(lock_text, encoding="utf-8")
    sentinel = root / "node_modules" / "keep" / "a.txt"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("keep", encoding="utf-8")
    if build:
        lib = root / "apps" / "cli" / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        (lib / "bin.js").write_text("// old build\n", encoding="utf-8")
    return root


def _patch_update_download(monkeypatch, zip_bytes: bytes, tmp_path: Path) -> None:
    """让 download_file 不联网，直接落一份假官方源码 zip。"""
    zip_path = tmp_path / "fake-dsh.zip"
    zip_path.write_bytes(zip_bytes)
    data = zip_path.read_bytes()

    def fake_download(url, dest, log=print, timeout=120.0, progress_cb=None):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest

    monkeypatch.setattr(core, "download_file", fake_download)


def _stage_fake_update(monkeypatch, tmp_path, *, target_version="0.1.0",
                       new_version="0.2.0", build=False,
                       old_lock="lock: same\n", new_lock="lock: same\n",
                       restart=None, wait_timeout=1800.0, watcher_pid=4321):
    """公共前置：造目标目录 + 假 zip，然后 stage 一次更新。"""
    target = _make_checkout_dir(tmp_path / "dsh", target_version, build=build,
                                lock_text=old_lock)
    zip_bytes = _make_fake_dsh_zip(tmp_path / "upstream.zip", new_version,
                                   lock_text=new_lock)
    _patch_update_download(monkeypatch, zip_bytes, tmp_path)
    monkeypatch.setattr(core, "_spawn_update_watcher", lambda manifest_path: watcher_pid)
    staged = core.stage_source_update(target, restart=restart or {}, port=3999,
                                      wait_timeout=wait_timeout)
    return target, staged


def test_stage_source_update_writes_manifest_without_touching_target(monkeypatch, tmp_path):
    """暂存阶段：只下载到同级暂存目录，绝不碰正在被 DSH 使用的目标目录。"""
    target, staged = _stage_fake_update(
        monkeypatch, tmp_path, build=True, old_lock="lock: old\n",
        new_lock="lock: new\n", restart={"execPath": "C:/node.exe",
                                         "args": ["apps/cli/lib/bin.js", "web"],
                                         "cwd": str(tmp_path)})
    assert staged["ok"] is True and staged["staged"] is True
    assert staged["old_version"] == "0.1.0"
    assert staged["new_version"] == "0.2.0"
    assert staged["run_build"] is True, "目标有 apps/cli/lib，必须重新构建"
    assert staged["run_install"] is True, "pnpm-lock.yaml 变了，必须重新 install"
    assert staged["restart"] is True
    assert staged["wait_port"] == 3999
    assert Path(staged["staging"]).is_dir()
    assert (Path(staged["staging"]) / "package.json").is_file()
    # 目标目录本身没被动过
    assert core._read_dir_version(target) == "0.1.0"
    manifest = core.load_pending_update()
    assert manifest["status"] == "waiting"
    assert manifest["watcher_pid"] == 4321
    assert manifest["wait_port"] == 3999
    assert manifest["restart"]["execPath"] == "C:/node.exe"


def test_stage_source_update_rejects_non_checkout(monkeypatch, tmp_path):
    bogus = tmp_path / "not-a-checkout"
    bogus.mkdir()
    with pytest.raises(RuntimeError):
        core.stage_source_update(bogus)


def test_apply_pending_update_swaps_and_keeps_node_modules(monkeypatch, tmp_path):
    target, _staged = _stage_fake_update(monkeypatch, tmp_path)
    run_calls = []
    monkeypatch.setattr(core, "_run_pnpm_step",
                        lambda t, args, log, what: run_calls.append((list(args), what)))
    result = core.apply_pending_update()
    assert result["ok"] is True and result["new_version"] == "0.2.0"
    assert core._read_dir_version(target) == "0.2.0"
    # node_modules 必须从备份里搬回新目录
    assert (target / "node_modules" / "keep" / "a.txt").is_file()
    # 没 build、锁文件也没变 → 不应跑 pnpm
    assert run_calls == []
    manifest = core.load_pending_update()
    assert manifest["status"] == "done"
    assert Path(manifest["backup"]).is_dir(), "旧版本要留备份，便于回滚"
    # 暂存目录已被移走
    assert not Path(manifest["staging"]).exists()


def test_apply_pending_update_runs_install_and_build(monkeypatch, tmp_path):
    target, _staged = _stage_fake_update(
        monkeypatch, tmp_path, build=True, old_lock="lock: old\n", new_lock="lock: new\n")
    calls = []
    monkeypatch.setattr(core, "_run_pnpm_step",
                        lambda t, args, log, what: calls.append((list(args), what)))
    result = core.apply_pending_update()
    assert result["ok"] is True
    kinds = [tuple(args) for args, _ in calls]
    assert ("install",) in kinds and ("run", "build") in kinds


def test_apply_pending_update_rolls_back_when_build_fails(monkeypatch, tmp_path):
    """构建失败必须自动回滚到旧版本——否则用户重启会得到一个跑不起来的 DSH。"""
    target, _staged = _stage_fake_update(monkeypatch, tmp_path, build=True)

    def boom(target_dir, args, log, what):
        raise RuntimeError("pnpm 挂了")

    monkeypatch.setattr(core, "_run_pnpm_step", boom)
    with pytest.raises(RuntimeError):
        core.apply_pending_update()
    assert core._read_dir_version(target) == "0.1.0", "失败后必须回滚到旧版本"
    assert (target / "node_modules" / "keep" / "a.txt").is_file()
    manifest = core.load_pending_update()
    assert manifest["status"] == "failed"
    assert "pnpm 挂了" in manifest["error"]


def test_pending_update_status_and_cancel(monkeypatch, tmp_path):
    target, staged = _stage_fake_update(monkeypatch, tmp_path)
    status = core.pending_update_status()
    assert status["present"] is True
    assert status["status"] == "waiting"
    assert status["old_version"] == "0.1.0" and status["new_version"] == "0.2.0"
    assert status["target"] == str(target)
    assert isinstance(status["log_tail"], list)

    killed = []
    monkeypatch.setattr(core.os, "kill", lambda pid, sig: killed.append(pid))
    result = core.cancel_pending_update()
    assert result["ok"] is True and result["canceled"] is True
    assert killed == [4321]
    assert not Path(staged["staging"]).exists(), "取消后暂存目录要删掉"
    assert core.pending_update_status()["status"] == "canceled"
    assert core.cancel_pending_update()["canceled"] is False


def test_cancel_refuses_while_applying(monkeypatch, tmp_path):
    _target, staged = _stage_fake_update(monkeypatch, tmp_path)
    core._set_pending_status("applying")
    with pytest.raises(RuntimeError):
        core.cancel_pending_update()
    # 状态和暂存目录都不能被取消操作破坏
    assert core.pending_update_status()["status"] == "applying"
    assert Path(staged["staging"]).is_dir()


def test_update_source_immediate_applies_without_waiting(monkeypatch, tmp_path):
    """目标没被运行中的 DSH 占用时：直接更新，不写清单、不等 DSH 关闭。"""
    target = _make_checkout_dir(tmp_path / "dsh", "0.1.0")
    zip_bytes = _make_fake_dsh_zip(tmp_path / "upstream.zip", "0.2.0")
    _patch_update_download(monkeypatch, zip_bytes, tmp_path)
    monkeypatch.setattr(core, "_run_pnpm_step",
                        lambda t, args, log, what: None)
    result = core.update_source_immediate(target)
    assert result["applied"] is True and result["new_version"] == "0.2.0"
    assert core._read_dir_version(target) == "0.2.0"
    assert (target / "node_modules" / "keep" / "a.txt").is_file()
    assert core.load_pending_update() == {}, "直更模式不该留下待应用清单"
    leftovers = list(target.parent.glob(".dsh-stage-*")) + list(target.parent.glob("dsh.dsh-stage-*"))
    assert leftovers == [], "暂存目录必须清理干净"


def test_watcher_expires_when_dsh_never_closes(monkeypatch, tmp_path):
    _target, staged = _stage_fake_update(monkeypatch, tmp_path, wait_timeout=0.1)
    monkeypatch.setattr(core, "_is_port_open", lambda *a, **k: True)
    monkeypatch.setattr(core.time, "sleep", lambda seconds: None)
    result = core.watch_and_apply_pending_update()
    assert result == {"ok": False, "reason": "timeout"}
    assert core.pending_update_status()["status"] == "expired"
    assert not Path(staged["staging"]).exists(), "超时后要清理暂存目录"


def test_watcher_applies_after_port_closes(monkeypatch, tmp_path):
    target, _staged = _stage_fake_update(monkeypatch, tmp_path)
    monkeypatch.setattr(core, "_is_port_open", lambda *a, **k: False)
    monkeypatch.setattr(core.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(core, "_run_pnpm_step", lambda t, args, log, what: None)
    result = core.watch_and_apply_pending_update()
    assert result["ok"] is True and result["applied"] is True
    assert core._read_dir_version(target) == "0.2.0"
    assert core.pending_update_status()["status"] == "done"
    assert result["restarted"] is False, "清单里没有重启信息时不应尝试重启"


def test_restart_requires_existing_executable(tmp_path):
    logs = []
    ok = core._restart_dsh_after_update(
        {"execPath": str(tmp_path / "missing-node.exe"), "args": [], "cwd": str(tmp_path)},
        3999, logs.append)
    assert ok is False
    assert logs, "失败原因要写进日志，别静默"


def test_decode_restart_spec_roundtrip():
    import base64 as _b64

    spec = {"execPath": "C:/node.exe", "args": ["apps/cli/lib/bin.js", "web"],
            "cwd": "D:/deepseek-harness-master/deepseek-harness-master"}
    encoded = _b64.b64encode(json.dumps(spec).encode("utf-8")).decode("ascii")
    assert core._decode_restart_spec(encoded) == spec
    assert core._decode_restart_spec("") == {}
    assert core._decode_restart_spec("!!!not-base64!!!") == {}
    assert core._decode_restart_spec(_b64.b64encode(b'{"args": ["x"]}').decode()) == {'args': ['x']}


def test_update_watcher_script_is_valid_python():
    """看护脚本是运行时生成的，语法错误会让更新永远卡在 waiting。"""
    source = core._update_watcher_script()
    compile(source, "<update-watcher>", "exec")
    assert "watch_and_apply_pending_update" in source
    assert "sys.path.insert" in source


def test_cli_update_status_without_pending(capsys):
    code = core._cli_main(["update-status"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert code == 0 and payload["ok"] is True
    assert payload["data"] == {"present": False}


def test_cli_stage_source_reports_clean_error(capsys, tmp_path):
    code = core._cli_main(["stage-source", str(tmp_path / "missing")])
    payload = json.loads(capsys.readouterr().out.strip())
    assert code == 1 and payload["ok"] is False
    assert "不存在" in payload["error"]


def test_resume_pending_update_respawns_watcher(monkeypatch, tmp_path):
    """目录被占用导致应用失败后：保留暂存目录，可「重试应用」重新挂看护进程。"""
    _target, _staged = _stage_fake_update(monkeypatch, tmp_path)
    # 模拟一次「被占用」失败：状态保持 waiting，错误留在清单里
    core._set_pending_status("waiting", error="目录仍被其他进程占用")
    killed = []
    monkeypatch.setattr(core.os, "kill", lambda pid, sig: killed.append(pid))
    monkeypatch.setattr(core, "_spawn_update_watcher", lambda manifest_path: 5555)
    result = core.resume_pending_update()
    assert result["ok"] is True and result["resumed"] is True
    assert result["watcher_pid"] == 5555
    assert killed == [4321], "重试前要先结束旧看护进程"
    status = core.pending_update_status()
    assert status["status"] == "waiting"
    assert status["error"] == "", "重试时要清掉上一次的错误"
    assert status["watcher_pid"] == 5555
    assert status["can_retry"] is True


def test_resume_pending_update_rejects_missing_staging(monkeypatch, tmp_path):
    target, staged = _stage_fake_update(monkeypatch, tmp_path)
    import shutil as _shutil
    _shutil.rmtree(staged["staging"], ignore_errors=True)
    with pytest.raises(RuntimeError):
        core.resume_pending_update()


def test_occupied_failure_keeps_staging_for_retry(monkeypatch, tmp_path):
    """目录被占用时不能标记 failed：暂存更新要留着，用户关掉占用进程后能重试。"""
    target, staged = _stage_fake_update(monkeypatch, tmp_path)
    original_move = core.shutil.move

    def fake_move(src, dst):
        if Path(src) == target:
            raise OSError("目标目录仍被其他进程占用（模拟）")
        return original_move(src, dst)

    monkeypatch.setattr(core.shutil, "move", fake_move)
    monkeypatch.setattr(core, "_UPDATE_SWAP_RETRY", 0.05)
    monkeypatch.setattr(core.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(core, "_run_pnpm_step", lambda t, args, log, what: None)
    with pytest.raises(RuntimeError):
        core.apply_pending_update()
    status = core.pending_update_status()
    assert status["status"] == "waiting", "被占用应可重试，不能判死刑"
    assert status["can_retry"] is True
    assert "占用" in status["error"]
    assert Path(staged["staging"]).is_dir()


def test_status_can_retry_false_after_cancel(monkeypatch, tmp_path):
    _target, _staged = _stage_fake_update(monkeypatch, tmp_path)
    monkeypatch.setattr(core.os, "kill", lambda pid, sig: None)
    core.cancel_pending_update()
    status = core.pending_update_status()
    assert status["status"] == "canceled"
    assert status["can_retry"] is False


def test_cli_resume_staged_roundtrip(monkeypatch, tmp_path, capsys):
    _target, _staged = _stage_fake_update(monkeypatch, tmp_path)
    monkeypatch.setattr(core.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(core, "_spawn_update_watcher", lambda manifest_path: 7777)
    capsys.readouterr()  # 丢掉暂存阶段的普通日志
    code = core._cli_main(["resume-staged"])
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and payload["ok"] is True
    assert payload["data"]["watcher_pid"] == 7777


# ---------------------------------------------------------------------------
# 运行时 profile 指向源码检出时，插件里也能直接更新它
# ---------------------------------------------------------------------------
def test_resolve_runtime_source_root_follows_junction(monkeypatch, tmp_path):
    """profile 的 @deepseek-ai/dsh 若是 junction 指向检出 apps/cli，应解析出检出根。"""
    checkout = make_checkout(tmp_path / "checkout", version="0.2.0")
    profile = tmp_path / "profile"
    pkg = profile / "node_modules" / "@deepseek-ai" / "dsh"
    pkg.mkdir(parents=True)
    fake_real = checkout / "apps" / "cli"
    fake_real.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(core.os.path, "realpath", lambda path: str(fake_real))
    assert core.resolve_runtime_source_root(profile) == checkout


def test_resolve_runtime_source_root_returns_none_for_plain_runtime(monkeypatch, tmp_path):
    """纯 npm 安装的运行时不在源码检出里 → 不给更新按钮。"""
    profile = tmp_path / "profile"
    (profile / "node_modules" / "@deepseek-ai" / "dsh").mkdir(parents=True)
    somewhere = tmp_path / "elsewhere" / "dsh"
    somewhere.mkdir(parents=True)
    monkeypatch.setattr(core.os.path, "realpath", lambda path: str(somewhere))
    assert core.resolve_runtime_source_root(profile) is None


def test_cli_detect_exposes_update_target(monkeypatch):
    checkout = Path("D:/fake/deepseek-harness-master")
    profile = Path("C:/Users/x/.dsh/profiles/web")
    monkeypatch.setattr(core, "fetch_official_versions", lambda *a, **k: {})
    monkeypatch.setattr(core, "find_source_checkouts", lambda: [(checkout, "source", "0.2.0")])
    monkeypatch.setattr(core, "find_npm_global", lambda: [])
    monkeypatch.setattr(core, "find_profiles",
                        lambda: [(profile, "profile", "0.2.0", "0.2.0")])
    monkeypatch.setattr(core, "resolve_runtime_source_root", lambda path: checkout)
    data = core._cli_detect(offline=True)
    by_kind = {row["kind"]: row for row in data["installs"]}
    assert by_kind["source"]["updateable"] is True
    assert by_kind["source"]["update_target"] == str(checkout)
    assert by_kind["profile"]["updateable"] is True, "profile 能指向检出时也应可更新"
    assert by_kind["profile"]["update_target"] == str(checkout)


def test_detect_all_keeps_gui_updateable_semantics(monkeypatch):
    """detect_all（桌面 GUI 用）的 updateable 语义不能变：profile 仍不是可直接替换的目录。"""
    checkout = Path("D:/fake/deepseek-harness-master")
    profile = Path("C:/x/.dsh/profiles/web")
    monkeypatch.setattr(core, "find_source_checkouts", lambda: [])
    monkeypatch.setattr(core, "find_npm_global", lambda: [])
    monkeypatch.setattr(core, "find_profiles",
                        lambda: [(profile, "profile", "0.2.0", "0.2.0")])
    monkeypatch.setattr(core, "resolve_runtime_source_root", lambda path: checkout)
    data = core.detect_all(fetch_official=False)
    assert data["installs"][0]["update_target"] == str(checkout)
    assert data["installs"][0]["updateable"] is False


