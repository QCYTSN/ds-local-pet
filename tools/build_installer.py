#!/usr/bin/env python
"""Compile the verified Windows bundle into a per-user Inno Setup installer."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.version import VERSION  # noqa: E402


RELEASE_NAME = f"DS-Local-Pet-v{VERSION}-win-x64"
RELEASE_DIR = PROJECT_ROOT / "dist" / RELEASE_NAME
DIST_DIR = PROJECT_ROOT / "dist"
INSTALLER_PATH = DIST_DIR / f"DS-Local-Pet-Setup-v{VERSION}.exe"
CHECKSUM_PATH = INSTALLER_PATH.with_suffix(INSTALLER_PATH.suffix + ".sha256")
ISS_PATH = PROJECT_ROOT / "installer" / "dafeiyu.iss"


class InstallerBuildError(RuntimeError):
    pass


def find_iscc(explicit: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    discovered = shutil.which("ISCC.exe") or shutil.which("iscc")
    if discovered:
        candidates.append(Path(discovered))
    for environment_name in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        base = os.environ.get(environment_name)
        if not base:
            continue
        candidates.extend(
            (
                Path(base) / "Inno Setup 6" / "ISCC.exe",
                Path(base) / "Programs" / "Inno Setup 6" / "ISCC.exe",
            )
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise InstallerBuildError(
        "未找到 Inno Setup 6 编译器（ISCC.exe）。请安装 Inno Setup 6，"
        "或通过 --iscc 指定编译器路径。"
    )


def build_bundle() -> None:
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "tools" / "build_release.py")],
        cwd=PROJECT_ROOT,
        check=True,
    )


def verify_bundle() -> Path:
    executable = RELEASE_DIR / f"{RELEASE_NAME}.exe"
    if not executable.is_file():
        raise InstallerBuildError(f"缺少已验证发布程序：{executable}")
    if not (RELEASE_DIR / "_internal" / "assets" / "manifests" / "actions.json").is_file():
        raise InstallerBuildError("发布目录不完整：缺少运行时动作清单。")
    return executable


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="构建大肥鱼桌宠 Windows 安装程序。")
    parser.add_argument(
        "--skip-bundle",
        action="store_true",
        help="复用 dist 中已经验证的 onedir 发布目录。",
    )
    parser.add_argument("--iscc", help="Inno Setup 6 的 ISCC.exe 路径。")
    args = parser.parse_args()

    if not args.skip_bundle:
        build_bundle()
    executable = verify_bundle()
    compiler = find_iscc(args.iscc)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for old_output in (INSTALLER_PATH, CHECKSUM_PATH):
        if old_output.is_file():
            old_output.unlink()

    command = [
        str(compiler),
        f"/DAppVersion={VERSION}",
        f"/DSourceDir={RELEASE_DIR}",
        f"/DOutputDir={DIST_DIR}",
        f"/DExeName={executable.name}",
        str(ISS_PATH),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    if not INSTALLER_PATH.is_file():
        raise InstallerBuildError(f"安装程序没有生成到预期位置：{INSTALLER_PATH}")

    checksum = sha256(INSTALLER_PATH)
    CHECKSUM_PATH.write_text(
        f"{checksum}  {INSTALLER_PATH.name}\n",
        encoding="ascii",
    )
    print(f"Installer: {INSTALLER_PATH}")
    print(f"SHA-256:   {checksum}")
    print(f"Checksum:  {CHECKSUM_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (InstallerBuildError, subprocess.CalledProcessError) as error:
        print(f"\nINSTALLER BUILD FAILED\n{error}", file=sys.stderr)
        raise SystemExit(1)
