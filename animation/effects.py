"""Subtle procedural motion layered on top of authored sprite frames."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EffectPose:
    offset_x: float = 0.0
    offset_y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation_degrees: float = 0.0
    shadow_scale: float = 1.0
    shadow_opacity: float = 0.22
    decoration: str | None = None


def pose_for(effect: str, elapsed_seconds: float) -> EffectPose:
    """Return restrained motion; it complements, never pretends to be key art."""

    time = max(0.0, elapsed_seconds)
    breath = math.sin(time * 2.35)
    if effect == "breath":
        return EffectPose(scale_x=1.0 - breath * 0.006, scale_y=1.0 + breath * 0.012)
    if effect == "micro_idle":
        return EffectPose(
            offset_y=breath * 0.35,
            scale_x=1.0 - breath * 0.002,
            scale_y=1.0 + breath * 0.004,
            shadow_opacity=0.20,
        )
    if effect == "think":
        sway = math.sin(time * 2.2)
        return EffectPose(
            offset_y=-1.5 + breath * 1.1,
            rotation_degrees=sway * 1.8,
            scale_y=1.0 + breath * 0.009,
            decoration="thought",
        )
    if effect == "walk_placeholder":
        phase = math.sin(time * 12.0)
        # This is intentionally a placeholder gait: heel-to-toe weight and a
        # tiny step bob, never a claim of real animated leg artwork.
        return EffectPose(
            offset_y=-abs(phase) * 3.5,
            rotation_degrees=phase * 0.7,
            scale_x=1.0 + phase * 0.006,
            scale_y=1.0 - abs(phase) * 0.012,
            shadow_scale=1.0 - abs(phase) * 0.14,
            shadow_opacity=0.18,
        )
    if effect == "walk_frames":
        # The legs are authored in four separate frames.  This tiny weight
        # transfer only ties the shadow to the gait; it never substitutes for
        # the actual stepping artwork.
        phase = math.sin(time * math.tau * 2.08)
        return EffectPose(
            offset_y=-abs(phase) * 0.75,
            shadow_scale=1.0 - abs(phase) * 0.05,
            shadow_opacity=0.20,
        )
    if effect == "walk_start":
        progress = min(1.0, time / 0.26)
        anticipation = math.sin(progress * math.pi)
        return EffectPose(
            offset_y=anticipation * 1.2,
            scale_x=1.0 + anticipation * 0.018,
            scale_y=1.0 - anticipation * 0.025,
            shadow_scale=1.0 + anticipation * 0.05,
            shadow_opacity=0.20,
        )
    if effect == "walk_stop":
        settle = math.exp(-time * 12.0) * math.cos(time * 24.0)
        return EffectPose(
            offset_y=abs(settle) * 0.8,
            scale_x=1.0 + settle * 0.012,
            scale_y=1.0 - settle * 0.018,
            shadow_scale=1.0 + settle * 0.04,
            shadow_opacity=0.20,
        )
    if effect == "bounce":
        phase = max(0.0, math.sin(time * math.pi * 2.15))
        return EffectPose(
            offset_y=-phase * 10.0,
            scale_x=1.0 + phase * 0.018,
            scale_y=1.0 - phase * 0.024,
            shadow_scale=1.0 - phase * 0.23,
            decoration="sparkle",
        )
    if effect == "head_pat":
        settle = math.exp(-time * 4.8) * math.sin(time * 9.0)
        return EffectPose(
            offset_y=abs(settle) * 0.8,
            scale_x=1.0 + settle * 0.003,
            scale_y=1.0 - settle * 0.005,
            shadow_opacity=0.20,
        )
    if effect == "talk":
        phase = math.sin(time * 7.6)
        return EffectPose(offset_y=-abs(phase) * 1.8, rotation_degrees=phase * 0.7, decoration="voice")
    if effect == "angry":
        phase = math.sin(time * 20.0)
        return EffectPose(offset_x=phase * 2.5, rotation_degrees=phase * 1.1, decoration="anger")
    if effect == "recoil":
        impulse = math.exp(-time * 8.0)
        return EffectPose(offset_x=-impulse * 10.0, scale_x=1.0 - impulse * 0.035, rotation_degrees=-impulse * 3.0)
    if effect == "poke_frames":
        impulse = math.exp(-time * 7.0)
        return EffectPose(
            offset_x=-impulse * 2.0,
            rotation_degrees=-impulse * 0.8,
            shadow_opacity=0.20,
        )
    if effect == "tail_react":
        settle = math.exp(-time * 5.5) * math.sin(time * 13.0)
        return EffectPose(
            offset_x=settle * 0.8,
            rotation_degrees=settle * 0.7,
            shadow_opacity=0.20,
        )
    if effect == "eat":
        phase = max(0.0, math.sin(time * 11.0))
        return EffectPose(offset_y=-phase * 2.8, scale_x=1.0 + phase * 0.012, scale_y=1.0 - phase * 0.015, decoration="crumb")
    if effect == "sweep":
        phase = math.sin(time * 4.2)
        return EffectPose(offset_x=phase * 2.5, rotation_degrees=phase * 2.4, decoration="sweep")
    if effect == "sleep":
        return EffectPose(offset_y=breath * 1.6, scale_x=1.0 - breath * 0.008, scale_y=1.0 + breath * 0.013, decoration="sleep")
    if effect == "sleep_enter":
        progress = min(1.0, time / 1.05)
        return EffectPose(offset_y=progress * 1.0, shadow_scale=1.0 + progress * 0.04)
    if effect == "sleep_wake":
        progress = min(1.0, time / 0.90)
        return EffectPose(offset_y=(1.0 - progress) * 0.8, shadow_opacity=0.20)
    if effect == "float":
        phase = math.sin(time * 5.8)
        return EffectPose(offset_y=phase * 2.4, rotation_degrees=phase * 2.2, shadow_opacity=0.0)
    if effect == "fall":
        progress = min(1.0, time / 0.42)
        return EffectPose(
            rotation_degrees=progress * 10.0,
            scale_x=1.0 + progress * 0.012,
            scale_y=1.0 - progress * 0.018,
            shadow_opacity=0.0,
        )
    if effect == "landing":
        settle = math.exp(-time * 8.0) * math.cos(time * 19.0)
        compression = max(0.0, settle)
        return EffectPose(
            offset_y=compression * 2.0,
            scale_x=1.0 + compression * 0.055,
            scale_y=1.0 - compression * 0.075,
            shadow_scale=1.0 + compression * 0.16,
            shadow_opacity=0.25,
        )
    if effect == "dizzy":
        phase = math.sin(time * 10.0)
        return EffectPose(offset_x=phase * 1.5, rotation_degrees=phase * 2.8, decoration="dizzy")
    return EffectPose()
