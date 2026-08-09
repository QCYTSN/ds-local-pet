from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 5,
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
    "comfort": {
        "activity_level": "balanced",
        "walk_speed": 82.0,
        "reduced_motion": False,
        "hover_pause": True,
        "desktop_surfaces": True,
    },
    "updates": {
        "enabled": True,
        "last_checked_at": 0.0,
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
        self._runtime_overrides: dict[str, Any] = {}
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        raw = self._read_mapping(self.path)
        if not raw:
            raw = self._read_mapping(self.path.with_suffix(self.path.suffix + ".bak"))
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
        backup = self.path.with_suffix(self.path.suffix + ".bak")
        if self.path.is_file() and self._read_mapping(self.path):
            try:
                backup.write_bytes(self.path.read_bytes())
            except OSError:
                pass
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self._runtime_overrides.get(key, self.data.get(key, default))

    def section(self, key: str) -> dict[str, Any]:
        value = self.data.get(key)
        result = deepcopy(value) if isinstance(value, dict) else {}
        override = self._runtime_overrides.get(key)
        if isinstance(override, dict):
            result.update(deepcopy(override))
        return result

    def apply_runtime_overrides(self, values: dict[str, Any]) -> None:
        """Apply safe-mode values without overwriting the user's settings."""
        self._runtime_overrides = deepcopy(values)

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        self.data[key] = value
        if save:
            self.save()

    def set_nested(self, section: str, key: str, value: Any, *, save: bool = True) -> None:
        # Persist only the user's real settings.  Runtime overrides are used by
        # recovery safe mode and must never leak into config.json merely because
        # the user changed an unrelated option while safe mode was active.
        current = self.data.get(section)
        target = deepcopy(current) if isinstance(current, dict) else {}
        target[key] = value
        self.data[section] = target
        if save:
            self.save()

    @staticmethod
    def _read_mapping(path: Path) -> dict[str, Any]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        return raw if isinstance(raw, dict) else {}
