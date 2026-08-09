from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6.QtCore import QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget
from PySide6.QtCore import Qt


FOODS = ("小鱼", "虾", "贝", "海藻", "点心")


@dataclass(frozen=True, slots=True)
class InteractionOutcome:
    kind: str
    body_region: str = "body"
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    held_seconds: float = 0.0


class InteractionController:
    """Recognizes click, head-pat, drag, and keeps drag samples for future throws."""

    def __init__(self) -> None:
        self._press_pos: QPoint | None = None
        self._body_region = "body"
        self._pressed_at = 0.0
        self.dragging = False
        self._samples: list[tuple[float, QPoint]] = []

    @property
    def active(self) -> bool:
        return self._press_pos is not None

    @property
    def body_region(self) -> str:
        return self._body_region

    @property
    def held_seconds(self) -> float:
        return max(0.0, time.monotonic() - self._pressed_at) if self.active else 0.0

    def press(
        self,
        position: QPoint,
        local_x: float,
        local_y: float,
        body_left: float,
        body_top: float,
        body_width: float,
        body_height: float,
    ) -> None:
        self._press_pos = position
        self._body_region = self.classify_region(
            local_x,
            local_y,
            body_left,
            body_top,
            body_width,
            body_height,
        )
        self._pressed_at = time.monotonic()
        self.dragging = False
        self._samples = [(time.monotonic(), position)]

    @staticmethod
    def classify_region(
        local_x: float,
        local_y: float,
        body_left: float,
        body_top: float,
        body_width: float,
        body_height: float,
    ) -> str:
        if body_width <= 0 or body_height <= 0:
            return "body"
        x = (float(local_x) - float(body_left)) / float(body_width)
        y = (float(local_y) - float(body_top)) / float(body_height)
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return "body"
        if 0.27 <= x <= 0.73 and 0.20 <= y <= 0.43:
            return "face"
        if 0.14 <= x <= 0.86 and 0.02 <= y <= 0.40:
            return "head"
        if (x >= 0.72 or x <= 0.24) and 0.45 <= y <= 0.88:
            return "tail"
        return "body"

    def move(self, position: QPoint) -> bool:
        if self._press_pos is None:
            return False
        self._samples.append((time.monotonic(), position))
        self._samples = self._samples[-18:]
        if not self.dragging and (position - self._press_pos).manhattanLength() > 6:
            self.dragging = True
        return self.dragging

    def release(self, position: QPoint) -> InteractionOutcome | None:
        if self._press_pos is None:
            return None
        self._samples.append((time.monotonic(), position))
        was_dragging = self.dragging
        region = self._body_region
        held_seconds = max(0.0, time.monotonic() - self._pressed_at)
        velocity_x, velocity_y = self._velocity()
        self._press_pos = None
        self._pressed_at = 0.0
        self.dragging = False
        self._samples = []
        if was_dragging:
            return InteractionOutcome("drag", region, velocity_x, velocity_y, held_seconds)
        return InteractionOutcome("click", region, held_seconds=held_seconds)

    def cancel(self) -> None:
        self._press_pos = None
        self.dragging = False
        self._pressed_at = 0.0
        self._samples = []

    def _velocity(self) -> tuple[float, float]:
        if len(self._samples) < 2:
            return 0.0, 0.0
        end_time, end_pos = self._samples[-1]
        # Only the final flick should influence a throw.  Using the entire drag
        # made a long, slow carry look fast and made a pause before release
        # retain stale velocity.
        recent = [sample for sample in self._samples if sample[0] >= end_time - 0.16]
        if len(recent) < 2:
            return 0.0, 0.0
        start_time, start_pos = recent[0]
        duration = max(0.001, end_time - start_time)
        if duration < 0.018:
            return 0.0, 0.0
        return (
            (end_pos.x() - start_pos.x()) / duration,
            (end_pos.y() - start_pos.y()) / duration,
        )


class FoodPanel(QWidget):
    """Small transient picker retained from the original interaction design."""

    def __init__(self, on_pick) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("foodPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(336, 66)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        for food in FOODS:
            button = QToolButton()
            button.setText(food)
            button.setFont(QFont("Microsoft YaHei UI", 10))
            button.setFixedSize(49, 44)
            button.setStyleSheet(
                "QToolButton{background:rgba(240,249,255,242);border:none;"
                "border-radius:10px;color:#153a59;font-weight:600;}"
                "QToolButton:hover{background:#ffffff;color:#0b5f92;}"
            )
            button.clicked.connect(lambda _, value=food: on_pick(value))
            layout.addWidget(button)
        close = QToolButton()
        close.setText("关闭")
        close.setFont(QFont("Microsoft YaHei UI", 12))
        close.setFixedSize(34, 28)
        close.setStyleSheet(
            "QToolButton{background:rgba(255,255,255,36);border:none;border-radius:8px;color:#cae2f0;}"
            "QToolButton:hover{background:rgba(255,255,255,75);color:#fff;}"
        )
        close.clicked.connect(self.hide)
        layout.addWidget(close)
        self.setStyleSheet(
            "#foodPanel{background:rgba(10,43,70,235);border-radius:14px;}"
        )

    def popup_at(self, x: float, y: float) -> None:
        self.move(round(x - self.width() / 2), round(y - self.height() - 10))
        self.show()
        self.raise_()
