from __future__ import annotations

import unittest
from pathlib import Path

from awareness.context_snapshot import ContextSnapshot
from behavior.behavior_engine import BehaviorEngine
from behavior.cooldown import Cooldown
from behavior.events import ContextEvent, EventType
from dialogue.local_rules import DialogueManager


ASSETS = Path(__file__).resolve().parents[1] / "assets" / "dialogue"


def coding_snapshot(*, is_private: bool = False) -> ContextSnapshot:
    return ContextSnapshot(
        timestamp=0.0,
        process_name="Code.exe",
        window_title="window.py - Visual Studio Code",
        pid=42,
        idle_seconds=0.0,
        is_fullscreen=False,
        category="coding",
        is_private=is_private,
    )


class BehaviorEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BehaviorEngine(
            DialogueManager(ASSETS),
            Cooldown(global_seconds=10.0, context_seconds=60.0),
        )

    def test_stable_local_context_can_generate_one_reply(self) -> None:
        current = coding_snapshot()
        event = ContextEvent(EventType.APP_STAY, current, 0.0)
        reaction = self.engine.react(current, [event], personality="standard")
        self.assertIsNotNone(reaction)
        self.assertEqual(reaction.event_type, EventType.APP_STAY)
        self.assertEqual(reaction.category, "coding")

    def test_cooldown_and_privacy_suppress_replies(self) -> None:
        current = coding_snapshot()
        event = ContextEvent(EventType.APP_STAY, current, 0.0)
        self.assertIsNotNone(self.engine.react(current, [event], personality="standard"))
        second = ContextEvent(EventType.APP_STAY, current, 1.0)
        self.assertIsNone(self.engine.react(current, [second], personality="standard"))
        private = coding_snapshot(is_private=True)
        private_event = ContextEvent(EventType.APP_STAY, private, 100.0)
        self.assertIsNone(self.engine.react(private, [private_event], personality="standard"))
