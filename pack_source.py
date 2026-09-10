# -*- coding: utf-8 -*-
"""打包「源码版」zip —— 本地与 GitHub Actions 共用同一套逻辑。

用法：
    python pack_source.py                # 版本号取自 updater_gui.pyw 的 APP_VERSION
    python pack_source.py 0.6.8          # 显式指定版本号
    python pack_source.py --outdir dist  # 指定输出目录（默认 dist）

产物：<outdir>/dsh-updater-src-v<版本>.zip
zip 内为顶层目录 dsh-updater-src-v<版本>/，与历史发布件保持一致。

设计要点：
  * 版本号默认从 updater_gui.pyw 读取，避免打包件与实际代码版本不一致；
  * 文件清单是显式常量，保证每次打包内容可预期、可复核；
  * 缺文件时直接报错退出，不生成半成品 zip。
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# 随源码版分发的文件（顺序即 zip 内顺序）。
# 说明文档是必须的——README 里有指向它的链接，缺了就是死链。
SOURCE_FILES = (
    "updater_core.py",
    "updater_gui.pyw",
    "启动更新器.bat",
    "dsh_updater.ico",
    "README.md",
    "SECURITY.md",
    "源码版更新与GitHub同步说明.md",
)

_APP_VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*"([^"]+)"', re.M)


def read_app_version(root: Path | None = None) -> str:
    """从 updater_gui.pyw 读取 APP_VERSION（单一事实来源）。"""
    gui = (root or REPO_ROOT) / "updater_gui.pyw"
    m = _APP_VERSION_RE.search(gui.read_text(encoding="utf-8", errors="replace"))
    if not m:
        raise RuntimeError(f"未能在 {gui.name} 中找到 APP_VERSION 定义")
    return m.group(1)


def build_source_zip(version: str, outdir: Path, root: Path | None = None) -> Path:
    """生成源码版 zip 并返回产物路径。"""
    base = Path(root) if root is not None else REPO_ROOT
    missing = [name for name in SOURCE_FILES if not (base / name).is_file()]
    if missing:
        raise FileNotFoundError("缺少待打包文件：" + "、".join(missing))

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"dsh-updater-src-v{version}.zip"
    top = f"dsh-updater-src-v{version}"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in SOURCE_FILES:
            z.write(base / name, f"{top}/{name}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="打包 dsh-updater 源码版 zip")
    ap.add_argument("version", nargs="?", default=None,
                    help="版本号；省略则读取 updater_gui.pyw 的 APP_VERSION")
    ap.add_argument("--outdir", default="dist", help="输出目录（默认 dist）")
    args = ap.parse_args(argv)

    version = args.version or read_app_version()
    try:
        out = build_source_zip(version, Path(args.outdir))
    except FileNotFoundError as e:
        print(f"打包失败：{e}", file=sys.stderr)
        return 1

    print(f"已生成 {out}（{out.stat().st_size:,} 字节，版本 v{version}）")
    for name in SOURCE_FILES:
        print(f"    {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
