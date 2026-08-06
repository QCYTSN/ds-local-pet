from __future__ import annotations

import unittest
from datetime import datetime

from awareness.context_snapshot import ContextSnapshot
from behavior.events import EventType
from behavior.scheduler import ContextEventScheduler


def snapshot(
    *,
    idle_seconds: float = 0.0,
    fullscreen: bool = False,
) -> ContextSnapshot:
    return ContextSnapshot(
        timestamp=0.0,
        process_name="Code.exe",
        window_title="pet/window.py - Visual Studio Code",
        pid=42,
        idle_seconds=idle_seconds,
        is_fullscreen=fullscreen,
        category="coding",
    )


class ContextEventSchedulerTests(unittest.TestCase):
    def test_app_stay_waits_for_dwell_time(self) -> None:
        scheduler = ContextEventScheduler(min_dwell_seconds=15.0)
        first = scheduler.observe(snapshot(), now=0.0, wall_clock=datetime(2026, 8, 6, 12))
        early = scheduler.observe(snapshot(), now=14.9, wall_clock=datetime(2026, 8, 6, 12))
        stayed = scheduler.observe(snapshot(), now=15.0, wall_clock=datetime(2026, 8, 6, 12))
        self.assertEqual([event.type for event in first], [EventType.APP_ENTER])
        self.assertEqual(early, [])
        self.assertEqual([event.type for event in stayed], [EventType.APP_STAY])

    def test_idle_return_and_fullscreen_events_are_edge_triggered(self) -> None:
        scheduler = ContextEventScheduler(min_dwell_seconds=1.0, idle_after_seconds=300.0)
        scheduler.observe(snapshot(), now=0.0, wall_clock=datetime(2026, 8, 6, 12))
        idle = scheduler.observe(
            snapshot(idle_seconds=301.0),
            now=2.0,
            wall_clock=datetime(2026, 8, 6, 12),
        )
        still_idle = scheduler.observe(
            snapshot(idle_seconds=302.0),
            now=3.0,
            wall_clock=datetime(2026, 8, 6, 12),
        )
        returned = scheduler.observe(snapshot(), now=4.0, wall_clock=datetime(2026, 8, 6, 12))
        fullscreen = scheduler.observe(
            snapshot(fullscreen=True),
            now=5.0,
            wall_clock=datetime(2026, 8, 6, 12),
        )
        self.assertIn(EventType.USER_IDLE, [event.type for event in idle])
        self.assertNotIn(EventType.USER_IDLE, [event.type for event in still_idle])
        self.assertIn(EventType.USER_RETURN, [event.type for event in returned])
        self.assertIn(EventType.FULLSCREEN_ENTER, [event.type for event in fullscreen])

    def test_late_night_is_only_emitted_once_per_day(self) -> None:
        scheduler = ContextEventScheduler()
        first = scheduler.observe(snapshot(), now=0.0, wall_clock=datetime(2026, 8, 6, 23))
        second = scheduler.observe(snapshot(), now=1.0, wall_clock=datetime(2026, 8, 6, 23, 30))
        self.assertIn(EventType.LATE_NIGHT, [event.type for event in first])
        self.assertNotIn(EventType.LATE_NIGHT, [event.type for event in second])
