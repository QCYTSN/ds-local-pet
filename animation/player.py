"""Frame timing and crossfaded render snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from .clip import Anchor, AnimationClip, ClipFrame, PetAction
from .transitions import Crossfade


@dataclass(frozen=True, slots=True)
class RenderLayer:
    frame: ClipFrame
    action: PetAction
    anchor: Anchor
    mirrored: bool
    asset_id: str


@dataclass(frozen=True, slots=True)
class PlayerSnapshot:
    current: RenderLayer | None
    previous: RenderLayer | None
    current_opacity: float
    previous_opacity: float
    elapsed_seconds: float
    effect: str
    quality: str
    requires_real_frames: bool


class AnimationPlayer:
    def __init__(self) -> None:
        self._clip: AnimationClip | None = None
        self._elapsed_seconds = 0.0
        self._previous: RenderLayer | None = None
        self._transition = Crossfade()

    @property
    def clip(self) -> AnimationClip | None:
        return self._clip

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_seconds

    def play(self, clip: AnimationClip, *, crossfade: bool = True) -> bool:
        if self._clip is not None and self._clip.identity == clip.identity:
            return False
        previous = self._layer_for_current_frame()
        # Crossfading unrelated full-body poses makes two heads, arms or tails
        # visibly overlap.  Keep the tiny fade only when it is genuinely the
        # same visual asset and direction; every actual state change gets a
        # clean, intentional cut followed by its own motion effect.
        keep_previous = bool(
            crossfade
            and previous is not None
            and previous.asset_id == clip.asset_id
            and previous.mirrored == clip.mirrored
            and previous.anchor == clip.anchor
        )
        self._previous = previous if keep_previous else None
        self._clip = clip
        self._elapsed_seconds = 0.0
        if keep_previous and self._previous is not None:
            self._transition.start()
        else:
            self._transition.clear()
            self._previous = None
        return True

    def tick(self, delta_seconds: float) -> None:
        self._elapsed_seconds += max(0.0, delta_seconds)
        self._transition.tick(delta_seconds)
        if not self._transition.active:
            self._previous = None

    def snapshot(self) -> PlayerSnapshot:
        current = self._layer_for_current_frame()
        progress = self._transition.progress
        previous = self._previous if self._transition.active else None
        clip = self._clip
        return PlayerSnapshot(
            current=current,
            previous=previous,
            current_opacity=progress if previous is not None else 1.0,
            previous_opacity=(1.0 - progress) if previous is not None else 0.0,
            elapsed_seconds=self._elapsed_seconds,
            effect=clip.effect if clip is not None else "breath",
            quality=clip.quality if clip is not None else "placeholder",
            requires_real_frames=clip.requires_real_frames if clip is not None else False,
        )

    def _layer_for_current_frame(self) -> RenderLayer | None:
        clip = self._clip
        if clip is None or not clip.frames:
            return None
        frame_count = len(clip.frames)
        frame_index = int(self._elapsed_seconds * 1000.0 // max(1, clip.frame_duration_ms))
        if clip.loop:
            frame_index %= frame_count
        else:
            frame_index = min(frame_count - 1, frame_index)
        return RenderLayer(
            frame=clip.frames[frame_index],
            action=clip.action,
            anchor=clip.anchor,
            mirrored=clip.mirrored,
            asset_id=clip.asset_id,
        )
