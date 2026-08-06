from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from animation.clip import PetAction
from app.paths import AppPaths
from pet.window import PetWindow
from settings.config import ConfigManager


class DragRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        existing = QApplication.instance()
        if existing is not None and not isinstance(existing, QApplication):
            raise unittest.SkipTest("已有非 GUI Qt 应用，跳过离屏渲染检查")
        cls.application = existing or QApplication([])

    def test_drag_anchor_keeps_the_full_sprite_inside_window(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = AppPaths(app_dir=Path(folder), bundle_dir=Path(__file__).resolve().parents[1])
            window = PetWindow(paths, ConfigManager(paths.config_path))
            try:
                window.timer.stop()
                window.awareness_timer.stop()
                window._request_action(PetAction.DRAGGING, reason="test", force=True)
                window.player.tick(0.2)
                image = QImage(window.size(), QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(0)
                painter = QPainter(image)
                window.render(painter, QPoint())
                painter.end()
                body_rows = [
                    y
                    for y in range(image.height())
                    if any(image.pixelColor(x, y).alpha() >= 200 for x in range(image.width()))
                ]
                self.assertTrue(body_rows)
                # The soft floor shadow may live near the lower edge; the
                # opaque character itself must not be clipped by that edge.
                self.assertLess(max(body_rows), image.height() - 4)
            finally:
                window.tray.hide()
                window.control_panel.hide()
                window.food_panel.hide()
                window.hide()

    def test_right_walking_uses_the_same_four_frames_mirrored(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = AppPaths(app_dir=Path(folder), bundle_dir=Path(__file__).resolve().parents[1])
            window = PetWindow(paths, ConfigManager(paths.config_path))
            try:
                window.timer.stop()
                window.awareness_timer.stop()
                window._set_direction("left")
                window._request_action(PetAction.WALKING, reason="test", force=True)
                window.player.tick(0.2)
                self.assertIsNotNone(window.player.clip)
                self.assertEqual(len(window.player.clip.frames), 4)
                self.assertFalse(window.player.snapshot().current.mirrored)

                window._set_direction("right")
                window.player.tick(0.2)
                snapshot = window.player.snapshot()
                self.assertIsNotNone(snapshot.current)
                self.assertTrue(snapshot.current.mirrored)

                image = QImage(window.size(), QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(0)
                painter = QPainter(image)
                window.render(painter, QPoint())
                painter.end()
                opaque = sum(
                    1
                    for y in range(image.height())
                    for x in range(image.width())
                    if image.pixelColor(x, y).alpha() >= 200
                )
                self.assertGreater(opaque, 1_000)
            finally:
                window.tray.hide()
                window.control_panel.hide()
                window.food_panel.hide()
                window.hide()


if __name__ == "__main__":
    unittest.main()
