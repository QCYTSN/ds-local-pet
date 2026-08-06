from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.paths import AppPaths
from pet.window import PetWindow
from settings.config import ConfigManager


def run(argv: list[str] | None = None) -> int:
    """Create the Qt application, then hand control to the pet window."""
    application = QApplication(argv if argv is not None else sys.argv)
    application.setQuitOnLastWindowClosed(False)
    paths = AppPaths.discover()
    config = ConfigManager(paths.config_path)
    PetWindow(paths, config)
    return application.exec()
