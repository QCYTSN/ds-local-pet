from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


class PrivacyPolicy:
    """A deny-first local privacy filter. No titles are persisted or transmitted."""

    def __init__(self, rules_path: Path):
        try:
            rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            rules = {}
        self.process_names = {
            self._normalize(item)
            for item in rules.get("process_names", [])
            if isinstance(item, str)
        }
        self.title_keywords = tuple(
            self._normalize(item)
            for item in rules.get("title_keywords", [])
            if isinstance(item, str)
        )

    def is_private(
        self,
        process_name: str,
        window_title: str,
        custom_process_names: Iterable[str] = (),
    ) -> bool:
        process = self._normalize(process_name)
        custom = {self._normalize(item) for item in custom_process_names if isinstance(item, str)}
        if process and (process in self.process_names or process in custom):
            return True
        title = self._normalize(window_title)
        return bool(title and any(keyword in title for keyword in self.title_keywords))

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip().casefold()
