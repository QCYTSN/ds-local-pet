from __future__ import annotations

import math
import time
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QPolygonF

from animation.effects import EffectPose, pose_for
from animation.player import PlayerSnapshot, RenderLayer


@dataclass(slots=True)
class Bubble:
    text: str = ""
    until: float = 0.0
    appeared_at: float = 0.0
    inner: bool = False
    state_name: str = ""

    @property
    def visible(self) -> bool:
        return bool(self.text and time.monotonic() < self.until)

    def opacity_at(self, now: float | None = None) -> float:
        """Use a short entrance/exit so speech feels attached to the pet."""

        now = time.monotonic() if now is None else now
        if not self.text or now >= self.until:
            return 0.0
        if self.appeared_at <= 0:
            return 1.0
        fade_in = min(1.0, max(0.0, (now - self.appeared_at) / 0.13))
        fade_out = min(1.0, max(0.0, (self.until - now) / 0.20))
        return min(fade_in, fade_out)


class PetRenderer:
    """Compose a manifest-selected sprite, subtle motion and a compact bubble."""

    def __init__(self, bubble_height: int, margin: int) -> None:
        self.bubble_height = bubble_height
        self.margin = margin
        # Use Qt's system default instead of pinning a Windows family.  That
        # preserves the platform's CJK fallback chain in bundled/offscreen runs.
        self.bubble_font = QFont()
        self.bubble_font.setPointSize(10)
        self.bubble_font.setWeight(QFont.Weight.DemiBold)

    def paint(self, widget, *, snapshot: PlayerSnapshot, bubble: Bubble) -> None:
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if bubble.visible:
            self._draw_bubble(painter, widget.width(), bubble)

        if snapshot.current is None:
            return
        pose = pose_for(snapshot.effect, snapshot.elapsed_seconds)
        floor = QPointF(widget.width() / 2.0, widget.height() - self.margin - 7.0)
        current_anchor = self._render_anchor(widget, snapshot.current)
        self._draw_shadow(painter, floor, snapshot.current, pose)
        if snapshot.previous is not None and snapshot.previous_opacity > 0:
            self._draw_layer(
                painter,
                snapshot.previous,
                self._render_anchor(widget, snapshot.previous),
                pose,
                snapshot.previous_opacity,
            )
        self._draw_layer(painter, snapshot.current, current_anchor, pose, snapshot.current_opacity)
        self._draw_decoration(painter, current_anchor, snapshot.current, pose, snapshot.elapsed_seconds)

    def _render_anchor(self, widget, layer: RenderLayer) -> QPointF:
        """Keep non-standing actions inside the allocated sprite slot.

        Ground-anchored clips pivot at the feet.  Dragging, falling and seated
        clips pivot near the centre of that same slot; drawing those clips at
        the floor was the cause of the "head only" crop during a grab.
        """

        slot_top = self.bubble_height + self.margin
        slot_bottom = widget.height() - self.margin - 7.0
        if layer.anchor.kind in {"drag", "seat", "sleep"}:
            return QPointF(widget.width() / 2.0, (slot_top + slot_bottom) / 2.0)
        return QPointF(widget.width() / 2.0, slot_bottom)

    def _draw_layer(
        self,
        painter: QPainter,
        layer: RenderLayer,
        ground: QPointF,
        pose: EffectPose,
        opacity: float,
    ) -> None:
        pixmap = layer.frame.pixmap
        if pixmap.isNull() or opacity <= 0:
            return
        anchor_x = pixmap.width() * layer.anchor.x
        anchor_y = pixmap.height() * layer.anchor.y
        painter.save()
        painter.setOpacity(max(0.0, min(1.0, opacity)))
        painter.translate(ground.x() + pose.offset_x, ground.y() + pose.offset_y)
        painter.rotate(pose.rotation_degrees)
        scale_x = pose.scale_x * (-1.0 if layer.mirrored else 1.0)
        painter.scale(scale_x, pose.scale_y)
        painter.translate(-anchor_x, -anchor_y)
        painter.drawPixmap(0, 0, pixmap)
        painter.restore()

    def _draw_shadow(
        self,
        painter: QPainter,
        ground: QPointF,
        layer: RenderLayer,
        pose: EffectPose,
    ) -> None:
        pixmap = layer.frame.pixmap
        width = max(22.0, pixmap.width() * 0.27 * pose.shadow_scale)
        height = max(4.0, pixmap.height() * 0.027 * pose.shadow_scale)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        # Two offset translucent ellipses create depth without a hard outline.
        painter.setBrush(QColor(10, 48, 87, max(0, int(pose.shadow_opacity * 34))))
        painter.drawEllipse(QRectF(ground.x() - width / 2 - 1, ground.y() - height / 2 + 2, width + 2, height + 2))
        painter.setBrush(QColor(10, 48, 87, max(0, int(pose.shadow_opacity * 130))))
        painter.drawEllipse(QRectF(ground.x() - width / 2, ground.y() - height / 2 + 1, width, height))
        painter.restore()

    def _draw_bubble(self, painter: QPainter, width: int, bubble: Bubble) -> None:
        opacity = bubble.opacity_at()
        if opacity <= 0:
            return
        font = QFont(self.bubble_font)
        if bubble.inner:
            font.setItalic(True)
            background = QColor(232, 243, 251, 248)
            foreground = QColor(50, 84, 113)
            accent = QColor(98, 148, 187)
            label = "内心 OS"
        else:
            background = QColor(250, 253, 255, 250)
            foreground = QColor(18, 57, 91)
            accent = QColor(51, 154, 213)
            label = "大肥鱼"
        metrics = QFontMetrics(font)
        label_font = QFont(font)
        label_font.setPointSize(8)
        label_font.setWeight(QFont.Weight.DemiBold)
        label_metrics = QFontMetrics(label_font)
        max_width = min(242, width - 18)
        lines = self._wrap_text(bubble.text, metrics, max_width - 28)
        if not lines:
            return
        bubble_width = max(126, max(metrics.horizontalAdvance(line) for line in lines) + 28)
        bubble_width = min(max_width, bubble_width)
        bubble_height = label_metrics.height() + len(lines) * metrics.height() + 17
        bubble_x = (width - bubble_width) / 2
        bubble_y = 4.0
        body = QRectF(bubble_x, bubble_y, bubble_width, bubble_height)

        painter.save()
        painter.setOpacity(opacity)
        painter.setPen(Qt.PenStyle.NoPen)
        # One light offset shadow keeps the bubble legible without turning it
        # into a heavy notification card.
        painter.setBrush(QColor(8, 42, 77, 25))
        painter.drawRoundedRect(body.translated(0, 3), 12, 12)
        painter.setBrush(background)
        painter.drawRoundedRect(body, 12, 12)
        tail = QPointF(width / 2, bubble_y + bubble_height)
        painter.drawPolygon(
            QPolygonF(
                [
                    tail,
                    QPointF(tail.x() - 5.0, tail.y() + 6),
                    QPointF(tail.x() + 5.0, tail.y() + 6),
                ]
            )
        )
        painter.setBrush(accent)
        painter.drawEllipse(QRectF(bubble_x + 12, bubble_y + 8, 5, 5))
        painter.setPen(accent)
        painter.setFont(label_font)
        painter.drawText(
            QRectF(bubble_x + 21, bubble_y + 4, bubble_width - 32, label_metrics.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            label,
        )
        painter.setPen(foreground)
        painter.setFont(font)
        for index, line in enumerate(lines):
            painter.drawText(
                QRectF(
                    bubble_x + 14,
                    bubble_y + label_metrics.height() + 7 + index * metrics.height(),
                    bubble_width - 28,
                    metrics.height(),
                ),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                line,
            )
        painter.restore()

    @staticmethod
    def _wrap_text(text: str, metrics: QFontMetrics, max_width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for character in text:
            if current and metrics.horizontalAdvance(current + character) > max_width:
                lines.append(current)
                current = character
            else:
                current += character
        if current:
            lines.append(current)
        return lines[:2]

    def _draw_decoration(
        self,
        painter: QPainter,
        ground: QPointF,
        layer: RenderLayer,
        pose: EffectPose,
        elapsed_seconds: float,
    ) -> None:
        kind = pose.decoration
        if kind is None:
            return
        pixmap = layer.frame.pixmap
        top = ground.y() - pixmap.height() * layer.anchor.y
        right = ground.x() + pixmap.width() * (1.0 - layer.anchor.x)
        left = ground.x() - pixmap.width() * layer.anchor.x
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if kind == "thought":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(92, 172, 222, 155))
            for index, radius in enumerate((3.0, 4.5, 6.0)):
                painter.drawEllipse(QRectF(right - 23 + index * 7, top + 25 - index * 9, radius * 2, radius * 2))
        elif kind == "sparkle":
            self._draw_sparkle(painter, QPointF(right - 17, top + 34), QColor(80, 177, 228, 210), 6)
            self._draw_sparkle(painter, QPointF(left + 22, top + 48), QColor(136, 211, 245, 180), 4)
        elif kind == "voice":
            painter.setPen(QPen(QColor(62, 155, 210, 190), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for index in range(2):
                rect = QRectF(right - 20 + index * 4, top + 50 - index * 3, 10 + index * 3, 14 + index * 3)
                painter.drawArc(rect, -55 * 16, 110 * 16)
        elif kind == "anger":
            painter.setPen(QPen(QColor(221, 91, 105, 205), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            center = QPointF(right - 19, top + 43)
            painter.drawLine(center + QPointF(-5, -5), center + QPointF(5, 5))
            painter.drawLine(center + QPointF(5, -5), center + QPointF(-5, 5))
        elif kind == "crumb":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(246, 186, 93, 205))
            for index in range(3):
                x = ground.x() + 6 + index * 4
                y = ground.y() - 35 + ((index + int(elapsed_seconds * 8)) % 3) * 3
                painter.drawEllipse(QRectF(x, y, 2.8, 2.8))
        elif kind == "sweep":
            painter.setPen(QPen(QColor(112, 194, 226, 155), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(QRectF(left + 8, ground.y() - 24, 27, 10), 180 * 16, 110 * 16)
        elif kind == "sleep":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(109, 157, 206, 145))
            drift = math.sin(elapsed_seconds * 2.0) * 2
            for index, radius in enumerate((3.0, 4.0, 5.0)):
                painter.drawEllipse(QRectF(right - 20 + index * 6, top + 38 - index * 12 + drift, radius * 2, radius * 2))
        elif kind == "dizzy":
            angle = elapsed_seconds * 4.0
            for index in range(3):
                theta = angle + index * (math.tau / 3.0)
                point = QPointF(ground.x() + math.cos(theta) * 22, top + 24 + math.sin(theta) * 10)
                self._draw_sparkle(painter, point, QColor(230, 177, 74, 200), 3.5)
        painter.restore()

    @staticmethod
    def _draw_sparkle(painter: QPainter, center: QPointF, color: QColor, radius: float) -> None:
        painter.setPen(QPen(color, max(1.0, radius / 3.0), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(center + QPointF(-radius, 0), center + QPointF(radius, 0))
        painter.drawLine(center + QPointF(0, -radius), center + QPointF(0, radius))
