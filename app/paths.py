from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


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
    def config_path(self) -> Path:
        return self.app_dir / "config.json"

    @property
    def state_path(self) -> Path:
        return self.app_dir / "pet_state.json"

    @property
    def sprite_dir(self) -> Path:
        return self.bundle_dir / "sprites"

    @property
    def assets_dir(self) -> Path:
        return self.bundle_dir / "assets"
