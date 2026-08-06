# -*- coding: utf-8 -*-
"""Entry point for the modular, local-first DaFeiYu desktop pet."""

from __future__ import annotations

import sys

from app.application import run


def main() -> None:
    try:
        raise SystemExit(run())
    except Exception as error:
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            application = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "大肥鱼桌宠出错", str(error))
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
