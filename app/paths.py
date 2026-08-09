from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


APP_DATA_DIR_NAME = "DaFeiYuDesktopPet"


@dataclass(frozen=True)
class AppPaths:
    """Paths that remain valid both from source and a PyInstaller bundle."""

    app_dir: Path
    bundle_dir: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        project_root = Path(__file__).resolve().parents[1]
        if getattr(sys, "frozen", False):
            app_dir = Path(sys.executable).resolve().parent
            bundle_dir = Path(getattr(sys, "_MEIPASS", app_dir))
            return cls(app_dir=app_dir, bundle_dir=bundle_dir)
        return cls(app_dir=project_root, bundle_dir=project_root)

    @property
    def data_dir(self) -> Path:
        """Writable per-user data, even when the app is installed read-only."""
        override = os.environ.get("DAFEIYU_DATA_DIR")
        if override:
            return Path(override).expanduser().resolve()
        if getattr(sys, "frozen", False):
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                return Path(local_app_data) / APP_DATA_DIR_NAME
        # Source checkouts intentionally keep the old local files so existing
        # developer workflows and tests remain predictable.
        return self.app_dir

    def ensure_user_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.updates_dir.mkdir(parents=True, exist_ok=True)

    def migrate_legacy_user_data(self) -> None:
        """Move pre-installer portable settings into LocalAppData once."""
        if self.data_dir.resolve() == self.app_dir.resolve():
            return
        self.ensure_user_dirs()
        for name in ("config.json", "pet_state.json"):
            source = self.app_dir / name
            target = self.data_dir / name
            if source.is_file() and not target.exists():
                shutil.copy2(source, target)

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def state_path(self) -> Path:
        return self.data_dir / "pet_state.json"

    @property
    def recovery_path(self) -> Path:
        return self.data_dir / "session_recovery.json"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def log_path(self) -> Path:
        return self.logs_dir / "dafeiyu.log"

    @property
    def crash_reports_dir(self) -> Path:
        return self.logs_dir / "crashes"

    @property
    def updates_dir(self) -> Path:
        return self.data_dir / "updates"

    @property
    def sprite_dir(self) -> Path:
        return self.bundle_dir / "sprites"

    @property
    def assets_dir(self) -> Path:
        return self.bundle_dir / "assets"
