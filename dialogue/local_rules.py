from __future__ import annotations

import json
import random
from collections import deque
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
        self._recent: deque[str] = deque(maxlen=12)

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

    def pick_state(self, condition: str, *, personality: str) -> str | None:
        return self._pick_named("state", str(condition), personality)

    def pick_routine(self, situation: str, *, personality: str) -> str | None:
        return self._pick_named("routine", str(situation), personality)

    def pick_relationship(self, affinity: float, *, personality: str) -> str | None:
        try:
            value = float(affinity)
        except (TypeError, ValueError):
            value = 0.0
        tier = "close" if value >= 0.76 else ("familiar" if value >= 0.56 else "new")
        return self._pick_named("relationship", tier, personality)

    def _pick_named(self, filename: str, key: str, personality: str) -> str | None:
        payload = self._load(filename)
        choices = payload.get(key, {})
        if not isinstance(choices, dict):
            return None
        personality = normalize_personality(personality)
        lines = choices.get(personality) or choices.get("standard") or []
        valid_lines = [line for line in lines if isinstance(line, str) and line.strip()]
        if not valid_lines:
            return None
        fresh = [line for line in valid_lines if line not in self._recent]
        if not fresh and self._recent:
            fresh = [line for line in valid_lines if line != self._recent[-1]]
        selected = self._rng.choice(fresh or valid_lines)
        self._recent.append(selected)
        return selected

    def _load(self, filename: str) -> dict[str, Any]:
        if filename not in self._cache:
            try:
                self._cache[filename] = json.loads(
                    (self.dialogue_dir / f"{filename}.json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError, TypeError):
                self._cache[filename] = {}
        return self._cache[filename]
