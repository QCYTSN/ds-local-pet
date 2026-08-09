from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.recovery import CrashRecovery


class CrashRecoveryTests(unittest.TestCase):
    def recovery(self, root: Path, now: list[float]) -> CrashRecovery:
        return CrashRecovery(
            root / "session_recovery.json",
            root / "logs" / "crashes",
            version="0.2.0",
            clock=lambda: now[0],
        )

    def test_clean_exit_resets_crash_streak(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = [100.0]
            recovery = self.recovery(root, now)

            status = recovery.begin()
            now[0] = 115.0
            recovery.heartbeat()
            recovery.finish()

            marker = json.loads((root / "session_recovery.json").read_text(encoding="utf-8"))
            self.assertFalse(status.unclean_exit)
            self.assertFalse(marker["active"])
            self.assertEqual(marker["last_heartbeat"], 115.0)
            self.assertEqual(marker["consecutive_crashes"], 0)

    def test_two_consecutive_unclean_sessions_enable_safe_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = [100.0]
            first = self.recovery(root, now)
            first.begin()

            now[0] = 200.0
            second = self.recovery(root, now)
            second_status = second.begin()

            now[0] = 300.0
            third = self.recovery(root, now)
            third_status = third.begin()

            self.assertTrue(second_status.unclean_exit)
            self.assertEqual(second_status.consecutive_crashes, 1)
            self.assertFalse(second_status.safe_mode)
            self.assertEqual(third_status.consecutive_crashes, 2)
            self.assertTrue(third_status.safe_mode)

    def test_exception_writes_diagnostic_and_preserves_active_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = [100.0]
            recovery = self.recovery(root, now)
            recovery.begin()
            try:
                raise RuntimeError("test crash")
            except RuntimeError as error:
                report = recovery.record_exception(type(error), error, error.__traceback__)
            recovery.finish()

            marker = json.loads((root / "session_recovery.json").read_text(encoding="utf-8"))
            self.assertTrue(report.is_file())
            self.assertIn("RuntimeError: test crash", report.read_text(encoding="utf-8"))
            self.assertTrue(marker["active"])
            self.assertIn("RuntimeError: test crash", marker["last_error"])


if __name__ == "__main__":
    unittest.main()
