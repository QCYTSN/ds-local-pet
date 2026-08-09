from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.paths import AppPaths
from app.recovery import CrashRecovery, RecoveryStatus, configure_logging
from app.single_instance import SingleInstance
from app.version import VERSION
from app.windows_integration import register_application_restart
from pet.window import PetWindow
from settings.config import ConfigManager


def run(argv: list[str] | None = None) -> int:
    """Create the Qt application, then hand control to the pet window."""
    application = QApplication(argv if argv is not None else sys.argv)
    application.setQuitOnLastWindowClosed(False)
    register_application_restart()
    instance = SingleInstance()
    if not instance.acquire():
        return 0

    paths = AppPaths.discover()
    paths.ensure_user_dirs()
    paths.migrate_legacy_user_data()
    configure_logging(paths.log_path)
    recovery = CrashRecovery(
        paths.recovery_path,
        paths.crash_reports_dir,
        version=VERSION,
    )
    recovery_status = recovery.begin()

    def handle_fatal(
        exc_type: type[BaseException],
        error: BaseException,
        tb: object,
    ) -> None:
        report = recovery.record_exception(exc_type, error, tb)
        logging.getLogger(__name__).critical("Fatal error saved to %s", report)
        try:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                None,
                "大肥鱼需要重新启动",
                "大肥鱼遇到了意外，已经保存恢复信息。\n"
                "重新打开会恢复上次状态；若连续失败，将自动进入安全模式。\n\n"
                f"诊断记录：{report}",
            )
        finally:
            application.exit(1)

    sys.excepthook = handle_fatal
    config = ConfigManager(paths.config_path)
    if recovery_status.safe_mode:
        config.apply_runtime_overrides(
            {
                "mode": "still",
                "awareness": {"enabled": False},
                "comfort": {
                    "reduced_motion": True,
                    "desktop_surfaces": False,
                },
            }
        )
    try:
        window = PetWindow(paths, config, recovery_status=recovery_status)
    except BaseException:
        exc_type, error, tb = sys.exc_info()
        if exc_type is not None and error is not None:
            recovery.record_exception(exc_type, error, tb)
        instance.close()
        raise
    instance.set_activation_handler(window.activate_from_shortcut)
    application.aboutToQuit.connect(instance.close)
    application.aboutToQuit.connect(recovery.finish)

    heartbeat = QTimer(application)
    heartbeat.timeout.connect(recovery.heartbeat)
    heartbeat.start(15_000)

    # Packaging/installer smoke tests need a deterministic, clean exit without
    # automating a frameless desktop window.  The hook is inert for normal users
    # and deliberately capped so an accidental value cannot create a long job.
    smoke_exit_raw = os.environ.get("DAFEIYU_SMOKE_EXIT_MS")
    if smoke_exit_raw:
        try:
            smoke_exit_ms = max(250, min(60_000, int(smoke_exit_raw)))
        except ValueError:
            smoke_exit_ms = 0
        if smoke_exit_ms:
            QTimer.singleShot(smoke_exit_ms, application.quit)
    return application.exec()
