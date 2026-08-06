from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 3,
    "mode": "wander",
    "size": 0.7,
    "topmost": True,
    "passthrough": False,
    "autostart": False,
    "x": None,
    "y": None,
    "personality": "standard",
    "awareness": {
        "enabled": True,
        "read_window_title": True,
        "idle_detection": True,
        "hide_on_fullscreen": False,
        "poll_interval_ms": 1000,
        "min_dwell_seconds": 15,
        "global_cooldown_seconds": 150,
        "context_cooldown_seconds": 900,
    },
    "privacy": {
        "custom_process_names": [],
    },
}


def _merge_defaults(default: Any, value: Any) -> Any:
    if isinstance(default, dict):
        merged = deepcopy(default)
        if not isinstance(value, dict):
            return merged
        for key, default_value in default.items():
            if key in value:
                merged[key] = _merge_defaults(default_value, value[key])
        return merged
    if default is None:
        return value
    if type(value) is type(default):
        return value
    return deepcopy(default)


class ConfigManager:
    """Small JSON-backed settings store with schema-safe default merging."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            raw = {}
        merged = _merge_defaults(DEFAULT_CONFIG, raw)
        previous_schema = raw.get("schema_version", 1) if isinstance(raw, dict) else 1
        # Version 2 used a permissive fullscreen heuristic. Keep the feature
        # available, but turn it off during migration so ordinary maximized apps
        # cannot make the pet appear to flicker.
        if not isinstance(previous_schema, int) or previous_schema < 3:
            merged["awareness"]["hide_on_fullscreen"] = False
        merged["schema_version"] = DEFAULT_CONFIG["schema_version"]
        return merged

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def section(self, key: str) -> dict[str, Any]:
        value = self.data.get(key)
        return value if isinstance(value, dict) else {}

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        self.data[key] = value
        if save:
            self.save()

    def set_nested(self, section: str, key: str, value: Any, *, save: bool = True) -> None:
        target = self.section(section)
        target[key] = value
        self.data[section] = target
        if save:
            self.save()
