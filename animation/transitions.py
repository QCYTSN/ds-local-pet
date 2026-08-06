"""Tiny transition helper used to avoid hard sprite pops."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Crossfade:
    duration_seconds: float = 0.09
    elapsed_seconds: float = 0.0
    active: bool = False

    def start(self) -> None:
        self.elapsed_seconds = 0.0
        self.active = True

    def clear(self) -> None:
        self.elapsed_seconds = self.duration_seconds
        self.active = False

    def tick(self, delta_seconds: float) -> None:
        if not self.active:
            return
        self.elapsed_seconds += max(0.0, delta_seconds)
        if self.elapsed_seconds >= self.duration_seconds:
            self.clear()

    @property
    def progress(self) -> float:
        if not self.active or self.duration_seconds <= 0:
            return 1.0
        ratio = min(1.0, self.elapsed_seconds / self.duration_seconds)
        # Smoothstep makes the short crossfade read as a transition, not a flash.
        return ratio * ratio * (3.0 - 2.0 * ratio)
