from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

SpriteKey: TypeAlias = tuple[str, int, int]


@dataclass(slots=True)
class AnimationController:
    elapsed: float = 0.0
    jump_strength: float = 0.0
    eat_strength: float = 0.0
    crossfade: float = 0.0
    previous_sprite_key: SpriteKey | None = None
    idle_action: str | None = None
    idle_action_strength: float = 0.0

    def tick(self, delta_seconds: float) -> None:
        self.elapsed += delta_seconds
        self.jump_strength = max(0.0, self.jump_strength - delta_seconds * 3.0)
        self.eat_strength = max(0.0, self.eat_strength - delta_seconds * 2.5)
        self.crossfade = max(0.0, self.crossfade - delta_seconds * 7.5)
        self.idle_action_strength = max(
            0.0, self.idle_action_strength - delta_seconds * 1.5
        )
        if self.idle_action_strength == 0.0:
            self.idle_action = None

    def start_jump(self, strength: float = 1.0) -> None:
        self.jump_strength = max(self.jump_strength, min(1.0, strength))

    def start_eating(self) -> None:
        self.eat_strength = 1.0
        self.start_jump(0.55)

    def start_crossfade(self, previous_sprite_key: SpriteKey) -> None:
        self.previous_sprite_key = previous_sprite_key
        self.crossfade = 1.0

    def start_idle_action(self, action: str) -> None:
        self.idle_action = action
        self.idle_action_strength = 1.0
