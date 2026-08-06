from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from behavior.events import EventType
from dialogue.personality import normalize_personality


class DialogueManager:
    """Loads dialogue JSON and chooses clean local lines without any model call."""

    _category_file = {
        "coding": "coding",
        "github": "github",
        "video": "video",
        "document": "document",
        "paper": "document",
        "browser": "daily",
        "ai_chat": "daily",
    }

    def __init__(self, dialogue_dir: Path, rng: random.Random | None = None) -> None:
        self.dialogue_dir = Path(dialogue_dir)
        self._rng = rng or random.Random()
        self._cache: dict[str, dict[str, Any]] = {}

    def pick_for_event(self, event_type: EventType, category: str, *, personality: str) -> str | None:
        if event_type == EventType.USER_IDLE:
            return self._pick_named("idle", "idle", personality)
        if event_type == EventType.USER_RETURN:
            return self._pick_named("idle", "return", personality)
        if event_type == EventType.LATE_NIGHT:
            return self._pick_named("late_night", "lines", personality)
        if event_type == EventType.APP_STAY:
            filename = self._category_file.get(category, "daily")
            return self._pick_named(filename, "lines", personality)
        return None

    def pick_interaction(self, kind: str, *, personality: str) -> str | None:
        return self._pick_named("interaction", kind, personality)

    def pick_daily(self, *, personality: str) -> str | None:
        return self._pick_named("daily", "lines", personality)

    def pick_inner_voice(self, *, personality: str) -> str | None:
        return self._pick_named("inner_voice", "lines", personality)

    def _pick_named(self, filename: str, key: str, personality: str) -> str | None:
        payload = self._load(filename)
        choices = payload.get(key, {})
        if not isinstance(choices, dict):
            return None
        personality = normalize_personality(personality)
        lines = choices.get(personality) or choices.get("standard") or []
        valid_lines = [line for line in lines if isinstance(line, str) and line.strip()]
        return self._rng.choice(valid_lines) if valid_lines else None

    def _load(self, filename: str) -> dict[str, Any]:
        if filename not in self._cache:
            try:
                self._cache[filename] = json.loads(
                    (self.dialogue_dir / f"{filename}.json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError, TypeError):
                self._cache[filename] = {}
        return self._cache[filename]
