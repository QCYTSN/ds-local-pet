from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pet.state import PetState, PetStateStore
from settings.config import ConfigManager


class ConfigManagerTests(unittest.TestCase):
    def test_invalid_or_partial_json_gets_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "mode": "still",
                        "awareness": {"enabled": False},
                        "size": "not-a-number",
                    }
                ),
                encoding="utf-8",
            )
            config = ConfigManager(path)
            self.assertEqual(config.get("mode"), "still")
            self.assertEqual(config.get("size"), 0.7)
            self.assertFalse(config.section("awareness")["enabled"])
            self.assertTrue(config.section("awareness")["read_window_title"])

    def test_nested_setting_persists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            config = ConfigManager(path)
            config.set_nested("awareness", "enabled", False)
            restored = ConfigManager(path)
            self.assertFalse(restored.section("awareness")["enabled"])


class PetStateStoreTests(unittest.TestCase):
    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pet_state.json"
            store = PetStateStore(path)
            state = PetState()
            state.feed()
            store.save(state)
            restored = store.load()
            self.assertEqual(restored.total_feedings, 1)
            self.assertGreater(restored.energy, 0.78)
