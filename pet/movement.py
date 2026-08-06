from __future__ import annotations

import random
import time
from collections.abc import Callable

from PySide6.QtWidgets import QApplication, QWidget


class MovementController:
    """Movement modes are independent from rendering and slow context sensing."""

    modes = {"wander", "follow", "still"}

    def __init__(self, mode: str = "wander", speed: float = 380.0) -> None:
        self.mode = mode if mode in self.modes else "wander"
        self.speed = speed
        self.target: tuple[float, float] | None = None
        self.rest_until = 0.0
        self.current_speed = 0.0
        self.direction = "down"
        self.facing = 1

    @property
    def is_walking(self) -> bool:
        return self.target is not None

    def set_mode(self, mode: str) -> None:
        self.mode = mode if mode in self.modes else "wander"
        self.target = None
        self.current_speed = 0.0

    def set_direction(self, direction: str, facing: int | None = None) -> bool:
        changed_view = direction != self.direction
        self.direction = direction
        if facing is not None:
            self.facing = -1 if facing < 0 else 1
        return changed_view

    def rest_after_drag(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.target = None
        self.current_speed = 0.0
        self.rest_until = now + random.uniform(6.0, 14.0)

    def update(
        self,
        widget: QWidget,
        *,
        now: float,
        delta_seconds: float,
        set_direction: Callable[[str, int | None], None],
    ) -> bool:
        if self.mode == "follow":
            self._set_follow_target(widget)
        elif self.mode == "wander":
            self._set_wander_target(widget, now)
        else:
            self.target = None
            self.current_speed = 0.0
            return False

        if self.target is None:
            self.current_speed = max(0.0, self.current_speed - self.speed * delta_seconds * 4)
            return False

        target_x, target_y = self.target
        delta_x = target_x - widget.x()
        delta_y = target_y - widget.y()
        distance = (delta_x * delta_x + delta_y * delta_y) ** 0.5
        if distance < 8.0:
            self.target = None
            self.current_speed = 0.0
            self.rest_until = now + random.uniform(8.0, 18.0)
            set_direction("down", None)
            return False

        self.current_speed += (self.speed - self.current_speed) * min(1.0, delta_seconds * 15.0)
        step = min(distance, self.current_speed * delta_seconds)
        next_x = widget.x() + delta_x / distance * step
        next_y = widget.y() + delta_y / distance * step
        widget.move(round(next_x), round(next_y))

        if abs(delta_x) > abs(delta_y) * 1.15:
            set_direction("left" if delta_x < 0 else "right", -1 if delta_x < 0 else 1)
        else:
            set_direction("up" if delta_y < 0 else "down", None)
        return True

    def _set_follow_target(self, widget: QWidget) -> None:
        cursor = widget.cursor().pos()
        screen = QApplication.screenAt(cursor) or widget.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        near = (
            widget.x() - 100 <= cursor.x() <= widget.x() + widget.width() + 100
            and widget.y() - 100 <= cursor.y() <= widget.y() + widget.height() + 100
        )
        if near:
            self.target = None
            return
        max_x = geometry.right() - widget.width() + 1
        max_y = geometry.bottom() - widget.height() + 1
        target_x = max(geometry.left(), min(max_x, cursor.x() - widget.width() / 2))
        target_y = max(geometry.top(), min(max_y, cursor.y() - 90))
        self.target = (target_x, target_y)

    def _set_wander_target(self, widget: QWidget, now: float) -> None:
        if self.target is not None or now < self.rest_until:
            return
        screen = widget.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        left = geometry.left() + 20
        top = geometry.top() + 20
        right = max(left, geometry.right() - widget.width() - 20)
        bottom = max(top, geometry.bottom() - widget.height() - 20)
        self.target = (random.uniform(left, right), random.uniform(top, bottom))
