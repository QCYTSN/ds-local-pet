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

    def test_old_fullscreen_default_is_migrated_to_safe_off(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "awareness": {"hide_on_fullscreen": True},
                    }
                ),
                encoding="utf-8",
            )
            config = ConfigManager(path)
            self.assertEqual(config.get("schema_version"), 5)
            self.assertFalse(config.section("awareness")["hide_on_fullscreen"])

    def test_comfort_defaults_are_added_without_overwriting_other_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(json.dumps({"mode": "still"}), encoding="utf-8")

            config = ConfigManager(path)

            self.assertEqual(config.get("mode"), "still")
            self.assertEqual(config.section("comfort")["activity_level"], "balanced")
            self.assertEqual(config.section("comfort")["walk_speed"], 82.0)
            self.assertTrue(config.section("comfort")["hover_pause"])

    def test_runtime_overrides_do_not_leak_into_saved_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            config = ConfigManager(path)
            config.apply_runtime_overrides(
                {
                    "mode": "still",
                    "comfort": {"reduced_motion": True, "desktop_surfaces": False},
                }
            )
            self.assertEqual(config.get("mode"), "still")
            self.assertTrue(config.section("comfort")["reduced_motion"])

            config.set_nested("comfort", "hover_pause", False)
            restored = ConfigManager(path)

            self.assertEqual(restored.get("mode"), "wander")
            self.assertFalse(restored.section("comfort")["reduced_motion"])
            self.assertTrue(restored.section("comfort")["desktop_surfaces"])
            self.assertFalse(restored.section("comfort")["hover_pause"])

    def test_corrupt_primary_config_recovers_from_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            backup = path.with_suffix(".json.bak")
            path.write_text("{broken", encoding="utf-8")
            backup.write_text(json.dumps({"mode": "still"}), encoding="utf-8")

            config = ConfigManager(path)

            self.assertEqual(config.get("mode"), "still")


class PetVisibleConditionTests(unittest.TestCase):
    def test_needs_are_expressed_as_words_instead_of_raw_bars(self) -> None:
        self.assertEqual(PetState(energy=0.2).visible_condition(), "tired")
        self.assertEqual(PetState(annoyance=0.5).visible_condition(), "annoyed")
        self.assertEqual(PetState(boredom=0.9).visible_condition(), "restless")


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

    def test_relationship_and_session_counters_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pet_state.json"
            store = PetStateStore(path)
            state = PetState()
            self.assertTrue(state.begin_session("2026-08-09"))
            self.assertFalse(state.begin_session("2026-08-09"))
            state.pet_head()
            state.tap(1.5)
            state.drag()
            store.save(state)

            restored = store.load()

            self.assertEqual(restored.sessions, 2)
            self.assertEqual(restored.total_head_pats, 1)
            self.assertEqual(restored.total_pokes, 1)
            self.assertEqual(restored.total_drags, 1)
            self.assertEqual(restored.last_session_date, "2026-08-09")
