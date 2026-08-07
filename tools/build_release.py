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
3. Copies an explicit whitelist of runtime assets into the bundle
4. Verifies bundle integrity and fails hard when a runtime dependency is missing
5. Creates a versioned zip archive
6. Prints the output location and size

Packaging policy: the release contains only what the running application
actually reads. Development manifests, source inventories, reference art and
candidate sheets are never copied in the first place — there is no
"copy everything then delete" step to get wrong.

For build rationale, see docs/RELEASE_BUILD.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
INTERNAL_SUBDIR = "_internal"

# ---- runtime asset whitelist ---------------------------------------------
# Every entry below is read by the application at runtime. Nothing else from
# assets/ or sprites/ is shipped. Keep this list in sync with the code that
# reads it (referenced in the comments).

RUNTIME_ASSET_DIRS = (
    # animation.asset_registry -> frames referenced by actions.json
    "assets/processed/runtime/states",
    # dialogue.local_rules.DialogueManager
    "assets/dialogue",
)

RUNTIME_ASSET_FILES = (
    # animation.asset_registry.AssetRegistry — the only runtime manifest
    "assets/manifests/actions.json",
    # behavior.classifier.AppClassifier
    "assets/app_categories.json",
    # awareness privacy policy
    "assets/privacy_rules.json",
    # pet.window._create_tray -> QIcon(paths.sprite_dir / "icon.png")
    "sprites/icon.png",
)

# Dialogue files DialogueManager can request by name (see _category_file and
# the pick_* helpers). All of them must exist in the bundle.
REQUIRED_DIALOGUE_FILES = (
    "coding.json",
    "daily.json",
    "document.json",
    "github.json",
    "idle.json",
    "inner_voice.json",
    "interaction.json",
    "late_night.json",
    "video.json",
)

# Non-critical: nice to have, missing only produces a warning.
OPTIONAL_BUNDLE_PATHS = (
    f"{INTERNAL_SUBDIR}/icon.ico",
)

# ---- forbidden content ---------------------------------------------------
# Anything matching these must never reach the release. Checked against both
# the staged directory and the final zip.

FORBIDDEN_PATH_FRAGMENTS = (
    "assets/references",
    "assets/source/",
    "assets/candidates",
    "assets/processed/masters",
    "/tests/",
    "/tools/",
    "/build/",
    "/.git/",
    "/.venv/",
    "__pycache__",
)

FORBIDDEN_FILE_NAMES = {
    "source_inventory.json",
    "extraction_report.json",
    "state_extraction_report.json",
    "runtime_inventory.json",
    "character_spec.json",
    "config.json",
    "pet_state.json",
    ".gitignore",
}

FORBIDDEN_FILE_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log", ".spec"}

# sprites/ holds paid/third-party reference art. Only the tray icon may ship.
ALLOWED_SPRITE_FILES = {"icon.png"}

# ---- build hygiene -------------------------------------------------------

JUNK_DIR_NAMES = {"__pycache__", ".git", ".venv", ".idea", ".vscode"}
JUNK_FILE_NAMES = {"Thumbs.db", ".DS_Store", "config.json", "pet_state.json"}
JUNK_FILE_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log"}

# ---- developer path leak detection ---------------------------------------

TEXT_SCAN_SUFFIXES = {
    ".json", ".txt", ".md", ".ini", ".cfg", ".conf", ".toml",
    ".yml", ".yaml", ".py", ".spec", ".xml", ".csv",
}
# Payload we own; scanned with a broad regex as well as literal needles.
OWNED_PAYLOAD_PREFIXES = (f"{INTERNAL_SUBDIR}/assets/", f"{INTERNAL_SUBDIR}/sprites/")
GENERIC_DEV_PATH_RE = re.compile(r"[A-Za-z]:[\\/]{1,2}(?:Users|Github_Ku)[\\/]", re.IGNORECASE)


def _literal_dev_needles() -> tuple[str, ...]:
    """Absolute paths that must never appear in shipped text files."""
    roots = {str(PROJECT_ROOT), str(Path.home())}
    needles: set[str] = set()
    for root in roots:
        needles.add(root)                            # D:\Github_Ku\ds-local-pet
        needles.add(root.replace("\\", "\\\\"))      # JSON-escaped form
        needles.add(root.replace("\\", "/"))         # posix-style form
    return tuple(sorted(needles))


DEV_PATH_NEEDLES = _literal_dev_needles()


# ---- helpers -------------------------------------------------------------


class BuildError(RuntimeError):
    """Raised when the release bundle is not fit to ship."""


def _pip_install(package: str) -> None:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package],
        cwd=PROJECT_ROOT,
    )


def _run_pyinstaller(args: list[str]) -> None:
    cmd = [sys.executable, "-m", "PyInstaller"] + args
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=PROJECT_ROOT)


def _ignore_junk(_directory: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in JUNK_DIR_NAMES or name in JUNK_FILE_NAMES:
            ignored.add(name)
        elif Path(name).suffix.lower() in JUNK_FILE_SUFFIXES:
            ignored.add(name)
    return ignored


def _copy_runtime_assets() -> None:
    """Copy the runtime whitelist into the PyInstaller bundle."""
    target = RELEASE_DIR / INTERNAL_SUBDIR
    missing: list[str] = []

    for rel_path in RUNTIME_ASSET_DIRS:
        src = PROJECT_ROOT / rel_path
        if not src.is_dir():
            missing.append(rel_path)
            continue
        shutil.copytree(src, target / rel_path, dirs_exist_ok=True, ignore=_ignore_junk)
        print(f"  Copied dir  {rel_path}")

    for rel_path in RUNTIME_ASSET_FILES:
        src = PROJECT_ROOT / rel_path
        if not src.is_file():
            missing.append(rel_path)
            continue
        dst = target / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  Copied file {rel_path}")

    icon_src = PROJECT_ROOT / "icon.ico"
    if icon_src.is_file():
        shutil.copy2(icon_src, target / "icon.ico")
        shutil.copy2(icon_src, RELEASE_DIR / "icon.ico")
        print("  Copied file icon.ico")
    else:
        missing.append("icon.ico")

    if missing:
        raise BuildError(
            "缺少运行时资产源文件，无法打包：\n  - " + "\n  - ".join(missing)
        )


def _strip_build_junk() -> None:
    """Remove leftovers PyInstaller may have produced inside the bundle."""
    removed = 0
    for item in sorted(RELEASE_DIR.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if item.is_dir() and item.name in JUNK_DIR_NAMES:
            shutil.rmtree(item, ignore_errors=True)
            print(f"  Removed dir  {item.relative_to(RELEASE_DIR).as_posix()}")
            removed += 1
        elif item.is_file() and (
            item.name in JUNK_FILE_NAMES or item.suffix.lower() in JUNK_FILE_SUFFIXES
        ):
            item.unlink()
            print(f"  Removed file {item.relative_to(RELEASE_DIR).as_posix()}")
            removed += 1
    if removed == 0:
        print("  Nothing to strip.")


def _rel_paths(root: Path) -> list[str]:
    return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]


def _forbidden_hits(rel_paths: list[str]) -> list[str]:
    hits: list[str] = []
    for rel in rel_paths:
        probe = f"/{rel}"
        name = rel.rsplit("/", 1)[-1]
        if any(fragment in probe for fragment in FORBIDDEN_PATH_FRAGMENTS):
            hits.append(f"{rel}  (forbidden path)")
            continue
        if name in FORBIDDEN_FILE_NAMES:
            hits.append(f"{rel}  (forbidden file)")
            continue
        if Path(name).suffix.lower() in FORBIDDEN_FILE_SUFFIXES:
            hits.append(f"{rel}  (forbidden suffix)")
            continue
        if f"/{INTERNAL_SUBDIR}/sprites/" in probe and name not in ALLOWED_SPRITE_FILES:
            hits.append(f"{rel}  (non-runtime sprite)")
    return hits


def _scan_dev_paths() -> list[str]:
    """Recursively look for developer absolute paths in shipped text files."""
    hits: list[str] = []
    for path in sorted(RELEASE_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(RELEASE_DIR).as_posix()
        owned = rel.startswith(OWNED_PAYLOAD_PREFIXES)
        if path.suffix.lower() not in TEXT_SCAN_SUFFIXES and not owned:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for needle in DEV_PATH_NEEDLES:
            if needle in text:
                hits.append(f"{rel}  ->  {needle}")
        if owned:
            match = GENERIC_DEV_PATH_RE.search(text)
            if match:
                hits.append(f"{rel}  ->  {match.group(0)}")
    return sorted(set(hits))


def _verify_bundle() -> None:
    """Hard-fail integrity check. Runs before the zip is created."""
    errors: list[str] = []
    warnings: list[str] = []
    internal = RELEASE_DIR / INTERNAL_SUBDIR

    # 1. Critical runtime paths
    required = [
        f"{RELEASE_NAME}.exe",
        "icon.ico",
        f"{INTERNAL_SUBDIR}/assets/manifests/actions.json",
        f"{INTERNAL_SUBDIR}/assets/app_categories.json",
        f"{INTERNAL_SUBDIR}/assets/privacy_rules.json",
        f"{INTERNAL_SUBDIR}/assets/processed/runtime/states",
        f"{INTERNAL_SUBDIR}/assets/dialogue",
        f"{INTERNAL_SUBDIR}/sprites/icon.png",
    ]
    for rel in required:
        if (RELEASE_DIR / rel).exists():
            print(f"  [OK]      {rel}")
        else:
            errors.append(f"缺少运行时依赖：{rel}")
            print(f"  [MISSING] {rel}")

    # 2. Dialogue coverage
    for name in REQUIRED_DIALOGUE_FILES:
        if not (internal / "assets" / "dialogue" / name).is_file():
            errors.append(f"缺少台词资源：assets/dialogue/{name}")

    # 3. PyInstaller runtime present
    has_python_dll = any(internal.glob("python3*.dll"))
    has_base_library = (internal / "base_library.zip").is_file()
    has_pyside = (internal / "PySide6").is_dir()
    if not (has_python_dll and has_base_library and has_pyside):
        errors.append(
            "PyInstaller 运行时不完整 "
            f"(python3*.dll={has_python_dll}, base_library.zip={has_base_library}, PySide6={has_pyside})"
        )
    else:
        print("  [OK]      PyInstaller runtime (python3*.dll, base_library.zip, PySide6/)")

    # 4. Every frame referenced by actions.json must exist in the bundle
    actions_path = internal / "assets" / "manifests" / "actions.json"
    if actions_path.is_file():
        try:
            manifest = json.loads(actions_path.read_text(encoding="utf-8"))
        except ValueError as error:
            errors.append(f"actions.json 解析失败：{error}")
            manifest = {}
        frames_checked = 0
        frames_missing: list[str] = []
        for asset_id, asset in (manifest.get("assets") or {}).items():
            if not isinstance(asset, dict):
                continue
            for frames in (asset.get("frames") or {}).values():
                for frame in frames or []:
                    frames_checked += 1
                    if not (internal / str(frame)).is_file():
                        frames_missing.append(f"{asset_id}: {frame}")
        if frames_missing:
            errors.append(
                f"actions.json 引用的 {len(frames_missing)} 个运行时帧缺失，例如："
                + "; ".join(frames_missing[:5])
            )
        else:
            print(f"  [OK]      actions.json frames resolved ({frames_checked} files)")

    # 5. Forbidden content
    hits = _forbidden_hits(_rel_paths(RELEASE_DIR))
    if hits:
        errors.append("发行目录包含不应出现的文件：\n    - " + "\n    - ".join(hits[:20]))
    else:
        print("  [OK]      no development / private assets in bundle")

    # 6. Developer absolute paths
    leaks = _scan_dev_paths()
    if leaks:
        errors.append("发行目录文本文件包含开发机绝对路径：\n    - " + "\n    - ".join(leaks[:20]))
    else:
        print("  [OK]      no developer absolute paths in shipped text files")

    # 7. Optional extras
    for rel in OPTIONAL_BUNDLE_PATHS:
        if not (RELEASE_DIR / rel).exists():
            warnings.append(f"可选资源缺失：{rel}")

    for warning in warnings:
        print(f"  [WARN]    {warning}")

    if errors:
        raise BuildError("发行包校验失败：\n  - " + "\n  - ".join(errors))


def _create_zip() -> Path:
    """Create the final release zip archive."""
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    files = sorted(p for p in RELEASE_DIR.rglob("*") if p.is_file())
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(DIST_DIR).as_posix())
    return ZIP_PATH


def _verify_zip(zip_path: Path) -> None:
    """Re-check the archive itself, not just the staging directory."""
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    prefix = f"{RELEASE_NAME}/"
    stripped = [name[len(prefix):] for name in names if name.startswith(prefix)]
    if len(stripped) != len(names):
        raise BuildError("发行包 zip 内存在预期之外的顶层目录。")
    hits = _forbidden_hits(stripped)
    if hits:
        raise BuildError("发行 zip 包含不应出现的文件：\n  - " + "\n  - ".join(hits[:20]))
    if f"{RELEASE_NAME}.exe" not in stripped:
        raise BuildError("发行 zip 缺少可执行文件。")
    print(f"  [OK]      zip content verified ({len(stripped)} entries)")


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

    # Step 4: Copy the runtime asset whitelist
    print("\nCopying runtime assets (whitelist)...")
    _copy_runtime_assets()

    # Step 5: Strip build junk
    print("\nStripping build junk...")
    _strip_build_junk()

    # Step 6: Verify before packaging — a bad bundle must never become a zip
    print("\nVerifying bundle integrity...")
    _verify_bundle()

    # Step 7: Create and re-verify the zip
    print("\nCreating release archive...")
    zip_path = _create_zip()
    _verify_zip(zip_path)

    # Step 8: Report
    entries = list(RELEASE_DIR.rglob("*"))
    file_count = sum(1 for path in entries if path.is_file())
    dir_count = sum(1 for path in entries if path.is_dir())
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    exe_path = RELEASE_DIR / f"{RELEASE_NAME}.exe"
    exe_size_mb = exe_path.stat().st_size / (1024 * 1024)
    bundle_mb = sum(p.stat().st_size for p in entries if p.is_file()) / (1024 * 1024)

    print(f"\n{'=' * 62}")
    print(f"  Release:        {RELEASE_NAME}")
    print(f"  Bundle dir:     {RELEASE_DIR}")
    print(f"  Archive:        {zip_path}")
    print(f"  Archive size:   {size_mb:.1f} MB")
    print(f"  Bundle size:    {bundle_mb:.1f} MB")
    print(f"  EXE size:       {exe_size_mb:.1f} MB")
    print(f"  Files:          {file_count}")
    print(f"  Directories:    {dir_count}")
    print(f"{'=' * 62}")
    print("\nDone. Ready for release.")


if __name__ == "__main__":
    try:
        main()
    except BuildError as error:
        print(f"\nBUILD FAILED\n{error}", file=sys.stderr)
        raise SystemExit(1)
