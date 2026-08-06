from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.paths import AppPaths
from app.single_instance import SingleInstance
from pet.window import PetWindow
from settings.config import ConfigManager


def run(argv: list[str] | None = None) -> int:
    """Create the Qt application, then hand control to the pet window."""
    application = QApplication(argv if argv is not None else sys.argv)
    application.setQuitOnLastWindowClosed(False)
    instance = SingleInstance()
    if not instance.acquire():
        return 0
    paths = AppPaths.discover()
    config = ConfigManager(paths.config_path)
    window = PetWindow(paths, config)
    instance.set_activation_handler(window.activate_from_shortcut)
    application.aboutToQuit.connect(instance.close)
    return application.exec()
