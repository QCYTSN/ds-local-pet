"""Frame timing and crossfaded render snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from .clip import (
    Anchor,
    AnimationClip,
    AnimationPhase,
    AnimationProgram,
    ClipFrame,
    PetAction,
)
from .transitions import Crossfade


@dataclass(frozen=True, slots=True)
class RenderLayer:
    frame: ClipFrame
    action: PetAction
    anchor: Anchor
    mirrored: bool
    asset_id: str
    phase: AnimationPhase


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
    phase: AnimationPhase


class AnimationPlayer:
    def __init__(self) -> None:
        self._program: AnimationProgram | None = None
        self._clip: AnimationClip | None = None
        self._phase = AnimationPhase.BODY
        self._pending_program: AnimationProgram | None = None
        self._pending_crossfade = True
        self._elapsed_seconds = 0.0
        self._previous: RenderLayer | None = None
        self._transition = Crossfade()

    @property
    def clip(self) -> AnimationClip | None:
        return self._clip

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_seconds

    def play(
        self,
        animation: AnimationClip | AnimationProgram,
        *,
        crossfade: bool = True,
        immediate: bool = False,
    ) -> bool:
        program = (
            animation
            if isinstance(animation, AnimationProgram)
            else AnimationProgram(action=animation.action, body=animation)
        )
        if (
            self._program is not None
            and self._program.action == program.action
            and self._program.body.identity == program.body.identity
            and self._pending_program is None
        ):
            return False

        if self._program is not None and self._program.action == program.action:
            # Direction changes inside the same action should keep the gait
            # phase moving instead of replaying its start pose.
            self._activate_program(program, crossfade=crossfade, start_with_enter=False)
            return True

        if (
            not immediate
            and self._program is not None
            and self._program.exit is not None
        ):
            self._pending_program = program
            self._pending_crossfade = crossfade
            if self._phase != AnimationPhase.EXIT:
                self._activate_clip(self._program.exit, crossfade=False)
            return True

        self._activate_program(program, crossfade=crossfade, start_with_enter=True)
        return True

    def _activate_program(
        self,
        program: AnimationProgram,
        *,
        crossfade: bool,
        start_with_enter: bool,
    ) -> None:
        self._program = program
        self._pending_program = None
        clip = program.enter if start_with_enter and program.enter is not None else program.body
        self._activate_clip(clip, crossfade=crossfade)

    def _activate_clip(self, clip: AnimationClip, *, crossfade: bool) -> None:
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
        self._phase = clip.phase
        self._elapsed_seconds = 0.0
        if keep_previous and self._previous is not None:
            self._transition.start()
        else:
            self._transition.clear()
            self._previous = None

    def tick(self, delta_seconds: float) -> None:
        remaining = max(0.0, delta_seconds)
        while remaining > 1e-9:
            clip = self._clip
            phase_duration = (
                clip.duration_ms / 1000.0
                if clip is not None
                and self._phase in {AnimationPhase.ENTER, AnimationPhase.EXIT}
                and clip.duration_ms is not None
                else None
            )
            advance = remaining
            if phase_duration is not None:
                advance = min(advance, max(0.0, phase_duration - self._elapsed_seconds))
            self._elapsed_seconds += advance
            self._transition.tick(advance)
            remaining -= advance

            if phase_duration is None or self._elapsed_seconds + 1e-9 < phase_duration:
                break
            if self._phase == AnimationPhase.ENTER and self._program is not None:
                self._activate_clip(self._program.body, crossfade=False)
                continue
            if self._phase == AnimationPhase.EXIT and self._pending_program is not None:
                pending = self._pending_program
                pending_crossfade = self._pending_crossfade
                self._activate_program(
                    pending,
                    crossfade=pending_crossfade,
                    start_with_enter=True,
                )
                continue
            break
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
            phase=self._phase,
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
            phase=clip.phase,
        )
