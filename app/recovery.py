"""Crash markers, rotating logs and safe recovery for the desktop pet."""

from __future__ import annotations

import json
import logging
import time
import traceback
import uuid
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable


@dataclass(frozen=True, slots=True)
class RecoveryStatus:
    unclean_exit: bool = False
    consecutive_crashes: int = 0
    safe_mode: bool = False


def configure_logging(path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if any(getattr(handler, "baseFilename", None) == str(path) for handler in root.handlers):
        return
    handler = RotatingFileHandler(
        path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)


class CrashRecovery:
    """Detect unclean exits and keep a small atomic session marker."""

    def __init__(
        self,
        marker_path: Path,
        crash_reports_dir: Path,
        *,
        version: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.marker_path = Path(marker_path)
        self.crash_reports_dir = Path(crash_reports_dir)
        self.version = str(version)
        self.clock = clock
        self.session_id = uuid.uuid4().hex
        self.status = RecoveryStatus()
        self._fatal = False
        self._last_report: Path | None = None

    @property
    def fatal(self) -> bool:
        return self._fatal

    @property
    def last_report(self) -> Path | None:
        return self._last_report

    def begin(self) -> RecoveryStatus:
        previous = self._read_marker()
        unclean = bool(previous.get("active"))
        previous_count = self._safe_int(previous.get("consecutive_crashes"))
        count = previous_count + 1 if unclean else 0
        self.status = RecoveryStatus(
            unclean_exit=unclean,
            consecutive_crashes=count,
            safe_mode=count >= 2,
        )
        now = self.clock()
        self._write_marker(
            {
                "active": True,
                "session_id": self.session_id,
                "version": self.version,
                "started_at": now,
                "last_heartbeat": now,
                "consecutive_crashes": count,
                "safe_mode": self.status.safe_mode,
            }
        )
        return self.status

    def heartbeat(self) -> None:
        marker = self._read_marker()
        if marker.get("session_id") != self.session_id:
            return
        marker["last_heartbeat"] = self.clock()
        self._write_marker(marker)

    def record_exception(
        self,
        exc_type: type[BaseException],
        error: BaseException,
        tb: object,
    ) -> Path:
        self._fatal = True
        if self._last_report is not None:
            return self._last_report
        self.crash_reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self.clock()))
        report = self.crash_reports_dir / f"crash-{timestamp}.log"
        formatted = "".join(traceback.format_exception(exc_type, error, tb))
        report.write_text(
            f"DaFeiYu Desktop Pet {self.version}\n"
            f"session={self.session_id}\n"
            f"time={self.clock():.3f}\n\n{formatted}",
            encoding="utf-8",
        )
        marker = self._read_marker()
        marker.update(
            {
                "active": True,
                "last_error": f"{exc_type.__name__}: {error}",
                "last_error_at": self.clock(),
                "crash_report": str(report),
            }
        )
        self._write_marker(marker)
        self._last_report = report
        logging.getLogger(__name__).critical("Unhandled exception\n%s", formatted)
        return report

    def finish(self) -> None:
        if self._fatal:
            return
        marker = self._read_marker()
        if marker.get("session_id") != self.session_id:
            return
        marker.update(
            {
                "active": False,
                "clean_exit_at": self.clock(),
                "consecutive_crashes": 0,
                "safe_mode": False,
            }
        )
        self._write_marker(marker)

    def _read_marker(self) -> dict[str, object]:
        try:
            value = json.loads(self.marker_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _write_marker(self, value: dict[str, object]) -> None:
        self.marker_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.marker_path.with_suffix(self.marker_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.marker_path)

    @staticmethod
    def _safe_int(value: object) -> int:
        return max(0, int(value)) if isinstance(value, int) and not isinstance(value, bool) else 0
