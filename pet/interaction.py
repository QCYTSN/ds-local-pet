from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6.QtCore import QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget
from PySide6.QtCore import Qt


FOODS = ("🐟", "🍰", "🍭", "🍡", "💎")


@dataclass(frozen=True, slots=True)
class InteractionOutcome:
    kind: str
    body_region: str = "body"
    velocity_x: float = 0.0
    velocity_y: float = 0.0


class InteractionController:
    """Recognizes click, head-pat, drag, and keeps drag samples for future throws."""

    def __init__(self) -> None:
        self._press_pos: QPoint | None = None
        self._body_region = "body"
        self.dragging = False
        self._samples: list[tuple[float, QPoint]] = []

    def press(self, position: QPoint, local_y: float, body_top: float, body_height: float) -> None:
        self._press_pos = position
        self._body_region = (
            "head" if body_top <= local_y <= body_top + body_height * 0.34 else "body"
        )
        self.dragging = False
        self._samples = [(time.monotonic(), position)]

    def move(self, position: QPoint) -> bool:
        if self._press_pos is None:
            return False
        self._samples.append((time.monotonic(), position))
        self._samples = self._samples[-8:]
        if not self.dragging and (position - self._press_pos).manhattanLength() > 6:
            self.dragging = True
        return self.dragging

    def release(self, position: QPoint) -> InteractionOutcome | None:
        if self._press_pos is None:
            return None
        self._samples.append((time.monotonic(), position))
        was_dragging = self.dragging
        region = self._body_region
        velocity_x, velocity_y = self._velocity()
        self._press_pos = None
        self.dragging = False
        self._samples = []
        if was_dragging:
            return InteractionOutcome("drag", region, velocity_x, velocity_y)
        return InteractionOutcome("click", region)

    def cancel(self) -> None:
        self._press_pos = None
        self.dragging = False
        self._samples = []

    def _velocity(self) -> tuple[float, float]:
        if len(self._samples) < 2:
            return 0.0, 0.0
        end_time, end_pos = self._samples[-1]
        start_time, start_pos = self._samples[0]
        duration = max(0.001, end_time - start_time)
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
        self.setFixedSize(310, 64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        for food in FOODS:
            button = QToolButton()
            button.setText(food)
            button.setFont(QFont("Segoe UI Emoji", 20))
            button.setFixedSize(44, 44)
            button.setStyleSheet(
                "QToolButton{background:rgba(255,255,255,235);border:2px solid #ffb3c8;"
                "border-radius:22px;} QToolButton:hover{background:#ffe3ec;border-color:#ff7fa8;}"
            )
            button.clicked.connect(lambda _, value=food: on_pick(value))
            layout.addWidget(button)
        close = QToolButton()
        close.setText("✕")
        close.setFont(QFont("Microsoft YaHei UI", 12))
        close.setFixedSize(26, 26)
        close.setStyleSheet(
            "QToolButton{background:rgba(255,255,255,200);border:none;border-radius:13px;color:#666;}"
            "QToolButton:hover{background:#ff7fa8;color:#fff;}"
        )
        close.clicked.connect(self.hide)
        layout.addWidget(close)
        self.setStyleSheet(
            "#foodPanel{background:rgba(40,40,60,190);border-radius:14px;}"
        )

    def popup_at(self, x: float, y: float) -> None:
        self.move(round(x - self.width() / 2), round(y - self.height() - 10))
        self.show()
        self.raise_()
