from __future__ import annotations

import time


class Cooldown:
    """Global and per-context response cooldowns, all kept in memory only."""

    def __init__(self, global_seconds: float, context_seconds: float) -> None:
        self.global_seconds = global_seconds
        self.context_seconds = context_seconds
        self._last_global = float("-inf")
        self._last_context: dict[str, float] = {}

    def can_fire(self, context_key: str, *, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if now - self._last_global < self.global_seconds:
            return False
        return now - self._last_context.get(context_key, float("-inf")) >= self.context_seconds

    def record(self, context_key: str, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._last_global = now
        self._last_context[context_key] = now
