"""Typed data exchanged by the asset registry, state machine and renderer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtGui import QPixmap


class PetAction(str, Enum):
    IDLE = "IDLE"
    THINKING = "THINKING"
    WALKING = "WALKING"
    HAPPY = "HAPPY"
    TALKING = "TALKING"
    ANGRY = "ANGRY"
    POKE_REACT = "POKE_REACT"
    EATING = "EATING"
    SWEEPING = "SWEEPING"
    SLEEPING = "SLEEPING"
    DRAGGING = "DRAGGING"
    FALLING = "FALLING"
    DIZZY = "DIZZY"

    @classmethod
    def coerce(cls, value: "PetAction | str") -> "PetAction":
        return value if isinstance(value, cls) else cls(str(value))


@dataclass(frozen=True, slots=True)
class Anchor:
    kind: str = "ground"
    x: float = 0.5
    y: float = 0.985


@dataclass(frozen=True, slots=True)
class ActionSpec:
    action: PetAction
    asset_id: str
    loop: bool
    duration_ms: int | None
    priority: int
    interruptible: bool
    return_state: PetAction
    anchor: Anchor
    effect: str
    quality: str
    requires_real_frames: bool


@dataclass(frozen=True, slots=True)
class ClipFrame:
    source: Path
    pixmap: QPixmap


@dataclass(frozen=True, slots=True)
class AnimationClip:
    action: PetAction
    asset_id: str
    frames: tuple[ClipFrame, ...]
    loop: bool
    duration_ms: int | None
    frame_duration_ms: int
    anchor: Anchor
    effect: str
    quality: str
    requires_real_frames: bool
    mirrored: bool = False

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.action,
            self.asset_id,
            tuple(frame.source for frame in self.frames),
            self.mirrored,
            self.anchor,
            self.effect,
        )
