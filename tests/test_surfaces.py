from __future__ import annotations

import unittest

from pet.surfaces import DesktopSurfaceTracker


class FakeWindowReader:
    def __init__(self) -> None:
        self.handle = 42
        self.rects = {42: (200, 360, 900, 820)}

    def foreground_handle(self) -> int:
        return self.handle

    def read(self, handle: int):
        return self.rects.get(handle)


class DesktopSurfaceTrackerTests(unittest.TestCase):
    def test_window_becomes_a_platform_and_follows_when_moved(self) -> None:
        reader = FakeWindowReader()
        tracker = DesktopSurfaceTracker(reader)  # type: ignore[arg-type]
        self.assertTrue(tracker.observe_foreground(now=1.0))
        platforms = tracker.physics_platforms(
            work_area_top=0,
            widget_height=220,
            now=1.0,
        )
        self.assertEqual(platforms[0].surface_id, "window:42")
        self.assertTrue(tracker.attach("window:42", widget_x=400, widget_width=160))

        reader.rects[42] = (250, 410, 950, 870)
        update = tracker.follow_attachment(
            now=2.0,
            widget_x=400,
            widget_width=160,
            widget_height=220,
        )

        self.assertIsNotNone(update)
        self.assertFalse(update.lost)
        self.assertEqual(update.y, 190)
        self.assertGreater(update.x, 400)

    def test_lost_window_detaches_so_gravity_can_take_over(self) -> None:
        reader = FakeWindowReader()
        tracker = DesktopSurfaceTracker(reader)  # type: ignore[arg-type]
        tracker.observe_foreground(now=1.0)
        tracker.attach("window:42", widget_x=400, widget_width=160)
        del reader.rects[42]

        update = tracker.follow_attachment(
            now=2.0,
            widget_x=400,
            widget_width=160,
            widget_height=220,
        )

        self.assertTrue(update.lost)
        self.assertFalse(tracker.attached)


if __name__ == "__main__":
    unittest.main()
