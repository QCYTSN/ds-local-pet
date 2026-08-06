from __future__ import annotations

import math
import time
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPolygonF

from pet.animation import AnimationController, SpriteKey


@dataclass(slots=True)
class Bubble:
    text: str = ""
    until: float = 0.0
    inner: bool = False

    @property
    def visible(self) -> bool:
        return bool(self.text and time.monotonic() < self.until)


class PetRenderer:
    """Draw the bubble and sprite independently from movement and sensors."""

    def __init__(self, bubble_height: int, margin: int) -> None:
        self.bubble_height = bubble_height
        self.margin = margin
        self.bubble_font = QFont("Microsoft YaHei UI", 11)

    def paint(
        self,
        widget,
        *,
        sprites,
        current_key: SpriteKey,
        animation: AnimationController,
        walking: bool,
        bubble: Bubble,
    ) -> None:
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if bubble.visible:
            self._draw_bubble(painter, widget.width(), bubble)

        now = animation.elapsed
        if walking:
            walk_phase = math.sin(now * 10.5)
            sway = walk_phase * 6.0
            bob = -abs(math.sin(now * 5.25)) * 12.0
            walk_scale_x = 1.0 + walk_phase * 0.035
            walk_scale_y = 1.0 - walk_phase * 0.025
        else:
            sway = math.sin(now * 2.5) * 1.5
            bob = 0.0
            walk_scale_x = walk_scale_y = 1.0
        breath = 1.0 + 0.02 * math.sin(now * 2.5)
        eat = (
            1.0 + 0.12 * max(0.0, math.sin(animation.eat_strength * math.pi))
            if animation.eat_strength > 0
            else 1.0
        )
        scale = breath * eat
        jump = (
            -abs(math.sin(animation.jump_strength * math.pi))
            * 14
            * animation.jump_strength
            if animation.jump_strength > 0
            else 0.0
        )
        action_rotation = action_scale_x = action_scale_y = 0.0
        if animation.idle_action == "sway":
            action_rotation = (
                math.sin(animation.idle_action_strength * math.pi * 2)
                * 10
                * animation.idle_action_strength
            )
        elif animation.idle_action == "stretch":
            action_scale_y = 0.06 * math.sin(animation.idle_action_strength * math.pi)
            action_scale_x = -0.03 * math.sin(animation.idle_action_strength * math.pi)

        def draw_one(key: SpriteKey | None, opacity: float) -> None:
            if key is None or key not in sprites:
                return
            _, sprite_height, facing = key
            pixmap = sprites[key]
            image_height = pixmap.height() * scale * walk_scale_y * (1 + action_scale_y)
            image_width = pixmap.width() * scale * walk_scale_x * (1 + action_scale_x)
            center_x = widget.width() / 2
            bottom = self.bubble_height + self.margin + sprite_height
            image_x = center_x - image_width / 2
            image_y = bottom - image_height + jump + bob
            painter.save()
            painter.setOpacity(opacity)
            painter.translate(center_x, bottom)
            painter.rotate(sway + action_rotation)
            painter.translate(-center_x, -bottom)
            if facing < 0:
                painter.translate(center_x, 0)
                painter.scale(-1, 1)
                painter.translate(-center_x, 0)
            painter.drawPixmap(
                QRectF(image_x, image_y, image_width, image_height),
                pixmap,
                QRectF(0, 0, pixmap.width(), pixmap.height()),
            )
            painter.restore()

        if animation.crossfade > 0:
            draw_one(animation.previous_sprite_key, animation.crossfade)
            draw_one(current_key, 1.0 - animation.crossfade)
        else:
            draw_one(current_key, 1.0)

    def _draw_bubble(self, painter: QPainter, width: int, bubble: Bubble) -> None:
        font = QFont(self.bubble_font)
        if bubble.inner:
            font.setItalic(True)
            background, foreground = QColor(232, 232, 238, 235), QColor(125, 125, 138)
        else:
            background, foreground = QColor(255, 255, 255, 235), QColor(60, 60, 80)
        metrics = QFontMetrics(font)
        max_width = min(240, width - 16)
        lines: list[str] = []
        current = ""
        for character in bubble.text:
            if current and metrics.horizontalAdvance(current + character) > max_width - 20:
                lines.append(current)
                current = character
            else:
                current += character
        if current:
            lines.append(current)
        if not lines:
            return
        bubble_width = max(metrics.horizontalAdvance(line) for line in lines) + 20
        bubble_height = len(lines) * metrics.height() + 14
        bubble_x = (width - bubble_width) / 2
        bubble_y = 6.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(QRectF(bubble_x, bubble_y, bubble_width, bubble_height), 10, 10)
        tail = QPointF(width / 2, bubble_y + bubble_height)
        painter.drawPolygon(
            QPolygonF(
                [
                    tail,
                    QPointF(tail.x() - 6, tail.y() + 8),
                    QPointF(tail.x() + 6, tail.y() + 8),
                ]
            )
        )
        painter.setPen(foreground)
        painter.setFont(font)
        for index, line in enumerate(lines):
            painter.drawText(
                QRectF(
                    bubble_x,
                    bubble_y + 7 + index * metrics.height(),
                    bubble_width,
                    metrics.height(),
                ),
                Qt.AlignmentFlag.AlignCenter,
                line,
            )
