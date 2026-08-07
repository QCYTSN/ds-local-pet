#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build a standalone Windows release package for 大肥鱼桌宠.

Usage:
    .\.venv\Scripts\python.exe tools\build_release.py

This script:
1. Installs PyInstaller if missing
2. Builds a onedir (one-folder) bundle — chosen over onefile for:
   - Faster startup (no extraction to temp directory)
   - Lower false-positive rate from antivirus
   - Simpler resource path handling
   - Easier debugging
3. Copies required runtime assets into the bundle
4. Creates a versioned zip archive
5. Prints the output location and size

For build rationale, see docs/RELEASE_BUILD.md.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# ---- paths ---------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.version import VERSION, APP_NAME  # noqa: E402

RELEASE_NAME = f"DS-Local-Pet-v{VERSION}-win-x64"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = DIST_DIR / RELEASE_NAME
ZIP_PATH = DIST_DIR / f"{RELEASE_NAME}.zip"

# Assets that must be bundled with the executable
REQUIRED_ASSET_DIRS = (
    "assets/processed/runtime",
    "assets/manifests",
    "assets/dialogue",
    "assets/previews/contact_sheet",
    "assets/previews/gifs",
)
REQUIRED_ASSET_FILES = (
    "assets/app_categories.json",
    "assets/privacy_rules.json",
)

# Files that MUST NOT be bundled
EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "assets/source",
    "assets/references",
    "assets/candidates",
    "assets/processed/masters",
    "assets/manifests/extraction_report.json",
    "assets/manifests/source_inventory.json",
    "assets/manifests/state_extraction_report.json",
}
EXCLUDED_PATTERNS = {"*.pyc", "*.pyo", "*.tmp", "*.log", "config.json", "pet_state.json"}


# ---- helpers -------------------------------------------------------------


def _pip_install(package: str) -> None:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package],
        cwd=PROJECT_ROOT,
    )


def _run_pyinstaller(args: list[str]) -> None:
    cmd = [sys.executable, "-m", "PyInstaller"] + args
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=PROJECT_ROOT)


def _copy_assets() -> None:
    """Copy runtime assets into the PyInstaller bundle."""
    target = RELEASE_DIR / "_internal"
    for rel_path in REQUIRED_ASSET_DIRS:
        src = PROJECT_ROOT / rel_path
        if not src.exists():
            print(f"  WARNING: required asset directory missing: {rel_path}")
            continue
        dst = target / rel_path
        shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"  Copied {rel_path}")

    for rel_path in REQUIRED_ASSET_FILES:
        src = PROJECT_ROOT / rel_path
        if not src.exists():
            print(f"  WARNING: required asset file missing: {rel_path}")
            continue
        dst = target / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  Copied {rel_path}")

    # Copy icon
    icon_src = PROJECT_ROOT / "icon.ico"
    if icon_src.exists():
        shutil.copy2(icon_src, target / "icon.ico")


def _publish_icon() -> None:
    """Copy icon.ico to release root for shortcut creation."""
    icon_src = PROJECT_ROOT / "icon.ico"
    if icon_src.exists():
        shutil.copy2(icon_src, RELEASE_DIR / "icon.ico")


def _strip_dev_artifacts() -> None:
    """Remove any unintended files from the bundle."""
    for item in RELEASE_DIR.rglob("*"):
        if item.is_dir() and item.name in EXCLUDED_DIRS:
            shutil.rmtree(item, ignore_errors=True)
            print(f"  Removed excluded dir: {item.relative_to(RELEASE_DIR)}")
            continue
        if item.is_file():
            if item.name in EXCLUDED_PATTERNS or item.suffix in {".pyc", ".pyo"}:
                item.unlink()
                print(f"  Removed excluded file: {item.relative_to(RELEASE_DIR)}")


def _create_zip() -> Path:
    """Create the final release zip archive."""
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    files = sorted(p for p in RELEASE_DIR.rglob("*") if p.is_file())
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(DIST_DIR).as_posix())
    return ZIP_PATH


# ---- main ----------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="构建大肥鱼桌宠 Windows 发布包。")
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="保留之前的构建中间文件（用于调试）。",
    )
    args = parser.parse_args()

    # Step 1: Ensure PyInstaller is available
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        _pip_install("pyinstaller")

    # Step 2: Clean previous build
    if not args.no_clean:
        for path in [DIST_DIR, PROJECT_ROOT / "build"]:
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                print(f"Cleaned {path.relative_to(PROJECT_ROOT)}")

    # Step 3: PyInstaller onedir build
    print(f"\nBuilding {APP_NAME} v{VERSION}...")
    _run_pyinstaller([
        "--onedir",
        "--name",
        RELEASE_NAME,
        "--noconsole",
        "--icon",
        str(PROJECT_ROOT / "icon.ico"),
        "--add-data",
        f"{PROJECT_ROOT / 'icon.ico'}{os.pathsep}.",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(PROJECT_ROOT / "build"),
        "--specpath",
        str(PROJECT_ROOT / "build"),
        "--clean",
        "--noconfirm",
        "--log-level",
        "WARN",
        "--hidden-import",
        "PIL._tkinter_finder",
        str(PROJECT_ROOT / "main.py"),
    ])

    # Step 4: Copy runtime assets into the bundle
    print("\nCopying runtime assets...")
    _copy_assets()

    # Step 5: Copy icon to release root
    _publish_icon()

    # Step 6: Strip dev artifacts
    print("\nStripping dev artifacts...")
    _strip_dev_artifacts()

    # Step 7: Create zip
    print("\nCreating release archive...")
    zip_path = _create_zip()

    # Step 8: Report
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    exe_path = RELEASE_DIR / f"{RELEASE_NAME}.exe"
    exe_size_mb = exe_path.stat().st_size / (1024 * 1024) if exe_path.exists() else 0
    total_files = len(list(RELEASE_DIR.rglob("*")))
    total_dirs = len(list(RELEASE_DIR.rglob("*")))

    print(f"\n{'=' * 60}")
    print(f"  Release: {RELEASE_NAME}")
    print(f"  Bundle dir: {RELEASE_DIR}")
    print(f"  Archive:    {zip_path}")
    print(f"  Archive size: {size_mb:.1f} MB")
    print(f"  EXE size:     {exe_size_mb:.1f} MB")
    print(f"  Items in bundle: {total_files + total_dirs}")
    print(f"{'=' * 60}")

    # Verify integrity
    print("\nVerifying bundle integrity...")
    required_paths = [
        RELEASE_DIR / f"{RELEASE_NAME}.exe",
        RELEASE_DIR / "_internal" / "assets" / "manifests" / "actions.json",
        RELEASE_DIR / "_internal" / "assets" / "dialogue",
        RELEASE_DIR / "_internal" / "assets" / "processed" / "runtime" / "states",
    ]
    for path in required_paths:
        if path.exists():
            print(f"  [OK] {path.relative_to(RELEASE_DIR)}")
        else:
            print(f"  [MISSING] {path.relative_to(RELEASE_DIR)}")

    print("\nDone. Ready for release.")


if __name__ == "__main__":
    main()