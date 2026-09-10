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
    assert len(names) == len(pack_source.SOURCE_FILES)
    assert all(n.startswith("dsh-updater-src-v9.9.9/") for n in names)
    assert "dsh-updater-src-v9.9.9/updater_core.py" in names
    assert "dsh-updater-src-v9.9.9/updater_gui.pyw" in names


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
