"""Deterministic screen-space throw physics for the desktop pet.

The engine intentionally knows nothing about Qt.  The window converts the
current monitor's available geometry into :class:`PhysicsBounds`, while this
module handles velocity limiting, gravity, collisions and landing.  Keeping
the integrator pure makes the behaviour predictable and cheap to test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PhysicsPlatform:
    """One horizontal desktop surface that may catch a descending pet."""

    left: float
    right: float
    top: float
    surface_id: str


@dataclass(frozen=True, slots=True)
class PhysicsBounds:
    """Inclusive global-coordinate work area."""

    left: float
    top: float
    right: float
    bottom: float
    platforms: tuple[PhysicsPlatform, ...] = ()

    def position_limits(self, width: float, height: float) -> tuple[float, float, float, float]:
        max_x = max(self.left, self.right - max(0.0, width) + 1.0)
        max_y = max(self.top, self.bottom - max(0.0, height) + 1.0)
        return self.left, max_x, self.top, max_y


@dataclass(frozen=True, slots=True)
class PhysicsStep:
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    first_impact: bool = False
    settled: bool = False
    hard_landing: bool = False
    impact_speed: float = 0.0
    landed_surface_id: str | None = None


class ThrowPhysics:
    """A lightweight gravity and collision model for one top-level window."""

    def __init__(
        self,
        *,
        gravity: float = 2350.0,
        max_launch_speed: float = 1850.0,
        wall_restitution: float = 0.34,
        ceiling_restitution: float = 0.24,
        floor_restitution: float = 0.18,
        hard_impact_speed: float = 980.0,
        bounce_impact_speed: float = 360.0,
        settle_horizontal_speed: float = 42.0,
    ) -> None:
        self.gravity = float(gravity)
        self.max_launch_speed = float(max_launch_speed)
        self.wall_restitution = float(wall_restitution)
        self.ceiling_restitution = float(ceiling_restitution)
        self.floor_restitution = float(floor_restitution)
        self.hard_impact_speed = float(hard_impact_speed)
        self.bounce_impact_speed = float(bounce_impact_speed)
        self.settle_horizontal_speed = float(settle_horizontal_speed)

        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self._bounce_count = 0
        self._floor_contact = False
        self._has_impacted = False
        self._hard_landing = False
        self._largest_impact = 0.0
        self._landing_surface_id: str | None = None

    @property
    def speed(self) -> float:
        return math.hypot(self.velocity_x, self.velocity_y)

    def launch(self, x: float, y: float, velocity_x: float, velocity_y: float) -> None:
        velocity_x, velocity_y = self._limited_velocity(velocity_x, velocity_y)
        self.x = float(x)
        self.y = float(y)
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self._bounce_count = 0
        self._floor_contact = False
        self._has_impacted = False
        self._hard_landing = False
        self._largest_impact = 0.0
        self._landing_surface_id = None
        self.active = True

    def cancel(self) -> None:
        self.active = False
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self._floor_contact = False

    def projected_center(self, delta_seconds: float, width: float, height: float) -> tuple[float, float]:
        """Return a short look-ahead point used to select an adjacent monitor."""

        delta = max(0.0, min(0.10, float(delta_seconds)))
        projected_x = self.x + self.velocity_x * delta
        projected_y = self.y + self.velocity_y * delta + 0.5 * self.gravity * delta * delta
        return projected_x + width / 2.0, projected_y + height / 2.0

    def step(
        self,
        delta_seconds: float,
        *,
        width: float,
        height: float,
        bounds: PhysicsBounds,
    ) -> PhysicsStep:
        if not self.active:
            return PhysicsStep(
                self.x,
                self.y,
                self.velocity_x,
                self.velocity_y,
                hard_landing=self._hard_landing,
                impact_speed=self._largest_impact,
                landed_surface_id=self._landing_surface_id,
            )

        remaining = max(0.0, min(0.10, float(delta_seconds)))
        min_x, max_x, min_y, max_y = bounds.position_limits(width, height)
        first_impact = False
        settled = False

        # Small substeps prevent a fast throw from tunnelling through a monitor
        # edge when the timer is briefly delayed by other desktop work.
        while remaining > 1e-7 and self.active:
            step = min(remaining, 1.0 / 120.0)
            remaining -= step

            self.velocity_y += self.gravity * step
            previous_y = self.y
            self.x += self.velocity_x * step
            self.y += self.velocity_y * step

            if self.x < min_x:
                self.x = min_x
                if self.velocity_x < 0.0:
                    self.velocity_x = -self.velocity_x * self.wall_restitution
            elif self.x > max_x:
                self.x = max_x
                if self.velocity_x > 0.0:
                    self.velocity_x = -self.velocity_x * self.wall_restitution

            if self.y < min_y:
                self.y = min_y
                if self.velocity_y < 0.0:
                    self.velocity_y = -self.velocity_y * self.ceiling_restitution

            platform = self._crossed_platform(
                previous_y,
                self.y,
                self.x,
                width,
                height,
                bounds.platforms,
            )
            landing_y = max_y
            surface_id: str | None = None
            if platform is not None:
                landing_y = platform.top - height
                surface_id = platform.surface_id

            if platform is not None or self.y >= max_y:
                self.y = landing_y
                impact_speed = max(0.0, self.velocity_y)
                self._largest_impact = max(self._largest_impact, impact_speed)
                self._hard_landing = self._hard_landing or impact_speed >= self.hard_impact_speed
                self._landing_surface_id = surface_id
                if not self._has_impacted:
                    first_impact = True
                    self._has_impacted = True
                self._floor_contact = True

                if impact_speed >= self.bounce_impact_speed and self._bounce_count < 2:
                    self.velocity_y = -impact_speed * self.floor_restitution
                    self.velocity_x *= 0.72
                    self._bounce_count += 1
                    self._floor_contact = False
                else:
                    self.velocity_y = 0.0
                    # Exponential friction remains stable across timer rates.
                    self.velocity_x *= math.pow(0.045, step)
                    if abs(self.velocity_x) <= self.settle_horizontal_speed:
                        self.velocity_x = 0.0
                        self.active = False
                        settled = True

        return PhysicsStep(
            self.x,
            self.y,
            self.velocity_x,
            self.velocity_y,
            first_impact=first_impact,
            settled=settled,
            hard_landing=self._hard_landing,
            impact_speed=self._largest_impact,
            landed_surface_id=self._landing_surface_id,
        )

    @staticmethod
    def _crossed_platform(
        previous_y: float,
        current_y: float,
        current_x: float,
        width: float,
        height: float,
        platforms: tuple[PhysicsPlatform, ...],
    ) -> PhysicsPlatform | None:
        previous_bottom = previous_y + height
        current_bottom = current_y + height
        if current_bottom < previous_bottom:
            return None
        candidates: list[PhysicsPlatform] = []
        for platform in platforms:
            if previous_bottom > platform.top + 0.5 or current_bottom < platform.top:
                continue
            overlap = max(
                0.0,
                min(current_x + width, platform.right) - max(current_x, platform.left),
            )
            if overlap < min(36.0, width * 0.22):
                continue
            candidates.append(platform)
        return min(candidates, key=lambda item: item.top) if candidates else None

    def _limited_velocity(self, velocity_x: float, velocity_y: float) -> tuple[float, float]:
        velocity_x = float(velocity_x)
        velocity_y = float(velocity_y)
        speed = math.hypot(velocity_x, velocity_y)
        if speed <= self.max_launch_speed or speed <= 0.0:
            return velocity_x, velocity_y
        scale = self.max_launch_speed / speed
        return velocity_x * scale, velocity_y * scale
