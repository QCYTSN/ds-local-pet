from __future__ import annotations

import json
from pathlib import Path


class AppClassifier:
    """Classify an app from executable name first, then a short title rule."""

    def __init__(self, rules_path: Path):
        try:
            rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            rules = {}
        categories = rules.get("categories", {})
        self._process_categories = {
            self._normalize(process): category
            for category, processes in categories.items()
            if isinstance(processes, list)
            for process in processes
            if isinstance(process, str)
        }
        self._title_rules = tuple(
            (
                category,
                tuple(self._normalize(keyword) for keyword in keywords if isinstance(keyword, str)),
            )
            for category, keywords in rules.get("title_rules", {}).items()
            if isinstance(keywords, list)
        )

    def classify(self, process_name: str, window_title: str = "") -> str:
        process = self._normalize(
            process_name.replace("/", "\\").rsplit("\\", maxsplit=1)[-1]
        )
        title = self._normalize(window_title)
        base_category = self._process_categories.get(process, "unknown")
        # Executable names are more reliable for editors, chat clients, and games.
        # Titles refine browser and document windows only.
        if base_category in {"coding", "chat", "game"}:
            return base_category
        for category, keywords in self._title_rules:
            if any(keyword and keyword in title for keyword in keywords):
                return category
        if title.endswith(".pdf"):
            return "document"
        return base_category

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip().casefold()
