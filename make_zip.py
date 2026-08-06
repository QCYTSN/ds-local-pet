# -*- coding: utf-8 -*-
"""Create a portable source archive without user data or build artifacts."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
IGNORED_PARTS = {".git", ".venv", "__pycache__", "build", "dist"}
IGNORED_NAMES = {"config.json", "pet_state.json"}


def should_include(path: Path, archive_path: Path) -> bool:
    if path.resolve() == archive_path.resolve():
        return False
    if path.name in IGNORED_NAMES or path.suffix in {".pyc", ".tmp"}:
        return False
    return not any(part in IGNORED_PARTS for part in path.parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="打包可分享的大肥鱼桌宠源代码。")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT.parent / "大肥鱼桌宠-源码.zip",
        help="输出 zip 路径（默认放在项目目录外）。",
    )
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file() and should_include(path, output)
    )
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(PROJECT_ROOT).as_posix())

    print(f"已打包 {len(files)} 个文件：{output}")
    print(f"大小：{output.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
