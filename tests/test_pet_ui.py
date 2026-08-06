from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

from pet.renderer import Bubble
from settings.panel import PetControlPanel


def _panel() -> PetControlPanel:
    return PetControlPanel(
        on_mode=lambda _mode: None,
        on_size=lambda _size: None,
        on_feed=lambda: None,
        on_say=lambda: None,
        on_snap=lambda: None,
        on_awareness=lambda _enabled: None,
        on_read_window_title=lambda _enabled: None,
        on_idle_detection=lambda _enabled: None,
        on_topmost=lambda _enabled: None,
        on_fullscreen_hide=lambda _enabled: None,
        on_passthrough=lambda _enabled: None,
        on_autostart=lambda _enabled: None,
        on_action=lambda _action: None,
        on_hide=lambda: None,
        on_privacy=lambda: None,
        on_quit=lambda: None,
    )


class BubbleTimingTests(unittest.TestCase):
    def test_bubble_has_a_short_enter_and_exit_fade(self) -> None:
        bubble = Bubble(text="hello", appeared_at=1.0, until=3.0)
        self.assertAlmostEqual(bubble.opacity_at(1.065), 0.5, places=2)
        self.assertEqual(bubble.opacity_at(1.2), 1.0)
        self.assertAlmostEqual(bubble.opacity_at(2.9), 0.5, places=2)
        self.assertEqual(bubble.opacity_at(3.0), 0.0)


class CompactControlPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_popup_stays_compact_and_avoids_pet_when_screen_has_room(self) -> None:
        panel = _panel()
        try:
            panel.sync(
                mode="wander",
                size=0.70,
                awareness=True,
                read_window_title=True,
                idle_detection=True,
                topmost=True,
                fullscreen_hide=False,
                passthrough=False,
                autostart=False,
                state_name="待机",
            )
            area = self.application.primaryScreen().availableGeometry()
            pet = QRect(
                area.center().x() - 52,
                area.top() + max(120, area.height() // 3),
                104,
                180,
            )
            if area.width() < panel.width() + pet.width() + 42:
                self.skipTest("screen is too narrow for a non-overlapping compact popup")

            panel.popup_near_pet(pet)
            self.application.processEvents()
            self.assertLessEqual(panel.width(), 258)
            self.assertFalse(panel.geometry().intersects(pet))

            collapsed_height = panel.height()
            panel._toggle_advanced()
            self.application.processEvents()
            self.assertGreater(panel.height(), collapsed_height)
            panel._toggle_advanced()
            self.application.processEvents()
            self.assertLessEqual(panel.height(), collapsed_height)
        finally:
            panel.hide()


if __name__ == "__main__":
    unittest.main()
