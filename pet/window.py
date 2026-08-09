from __future__ import annotations

import ctypes
import os
import random
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QWidget,
)

from app.paths import AppPaths
from app.recovery import RecoveryStatus
from app.updater import UpdateClient, UpdateInfo, UpdateService, launch_installer
from app.version import VERSION
from awareness.privacy import PrivacyPolicy
from awareness.sensor import ContextSensor
from animation.asset_registry import AssetRegistry
from animation.clip import PetAction
from animation.player import AnimationPlayer
from animation.state_machine import ActionStateMachine
from behavior.activity_director import (
    ActivityCommand,
    ActivityCueType,
    ActivityDirector,
    MicroMotionDirector,
)
from behavior.behavior_engine import BehaviorEngine
from behavior.classifier import AppClassifier
from behavior.cooldown import Cooldown
from behavior.events import EventType
from behavior.scheduler import ContextEventScheduler
from dialogue.local_rules import DialogueManager
from dialogue.personality import normalize_personality
from pet.interaction import FoodPanel, InteractionController
from pet.movement import MovementController
from pet.physics import PhysicsBounds, ThrowPhysics
from pet.renderer import Bubble, PetRenderer
from pet.state import PetStateStore
from pet.surfaces import DesktopSurfaceTracker
from settings.config import ConfigManager
from settings.panel import PetControlPanel


BUBBLE_HEIGHT = 66
MARGIN = 4
BASE_SPRITE_HEIGHT = 340
SIZE_LEVELS = {"小": 0.55, "中": 0.70, "大": 0.90}
TICK_MS = 20

STATE_NAMES = {
    PetAction.IDLE: "待机",
    PetAction.BLINK: "眨眨眼",
    PetAction.GLANCE: "四处看看",
    PetAction.THINKING: "发呆",
    PetAction.WALKING: "散步",
    PetAction.HAPPY: "开心",
    PetAction.HEAD_PAT: "被摸摸",
    PetAction.TALKING: "说话",
    PetAction.ANGRY: "生气",
    PetAction.POKE_REACT: "被戳",
    PetAction.TAIL_REACT: "尾巴被碰",
    PetAction.EATING: "吃东西",
    PetAction.SWEEPING: "扫地",
    PetAction.SLEEPING: "睡觉",
    PetAction.DRAGGING: "抓取中",
    PetAction.FALLING: "落下",
    PetAction.LANDING: "着陆",
    PetAction.DIZZY: "眩晕",
}


class PetWindow(QWidget):
    """The transparent desktop pet window and the wiring between its modules."""

    def __init__(
        self,
        paths: AppPaths,
        config: ConfigManager,
        *,
        recovery_status: RecoveryStatus | None = None,
    ) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if config.get("topmost", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.paths = paths
        self.config = config
        self.recovery_status = recovery_status or RecoveryStatus()
        self.rng = random.Random()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("大肥鱼桌宠")

        self.current_height = self._height_for_size(
            self._normalized_size(config.get("size", 0.7))
        )
        self.asset_registry = AssetRegistry(paths.assets_dir)
        self.action_machine = ActionStateMachine(self.asset_registry.specs)
        self.player = AnimationPlayer()
        self._resize_window()

        comfort = config.section("comfort")
        self.movement = MovementController(
            config.get("mode", "wander"),
            speed=float(comfort.get("walk_speed", 82.0)),
            rng=self.rng,
        )
        self.physics = ThrowPhysics()
        self.interaction = InteractionController()
        self.renderer = PetRenderer(BUBBLE_HEIGHT, MARGIN)
        self.renderer.set_reduced_motion(bool(comfort.get("reduced_motion", False)))
        self.surface_tracker = DesktopSurfaceTracker(
            enabled=bool(comfort.get("desktop_surfaces", True))
        )
        self.bubble = Bubble()
        self._last_line = ""
        self._last_tick_at = time.monotonic()
        self._last_state_update = self._last_tick_at
        self._drag_offset: QPoint | None = None
        self._drag_last_pos: QPoint | None = None
        self._caught_throw = False
        self._pending_click_region = "body"
        self._hovered = False
        self._recent_pokes: deque[float] = deque(maxlen=8)
        self._recent_feedings: deque[float] = deque(maxlen=6)
        self._available_update: UpdateInfo | None = None
        self._downloaded_update: Path | None = None

        self.dialogue = DialogueManager(paths.assets_dir / "dialogue", self.rng)
        self.state_store = PetStateStore(paths.state_path)
        self.pet_state = self.state_store.load()
        self._first_session_today = self.pet_state.begin_session()
        activity_level = str(comfort.get("activity_level", "balanced"))
        self.activity_director = ActivityDirector(self.rng, activity_level=activity_level)
        self.micro_motion_director = MicroMotionDirector(
            self.rng,
            activity_level=activity_level,
        )
        self.update_service = UpdateService(
            UpdateClient(
                current_version=VERSION,
                updates_dir=paths.updates_dir,
            ),
            self,
        )
        self.update_service.checked.connect(self._on_update_checked)
        self.update_service.check_failed.connect(self._on_update_check_failed)
        self.update_service.downloaded.connect(self._on_update_downloaded)
        self.update_service.download_failed.connect(self._on_update_download_failed)

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._do_click_reaction)
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._do_long_press_reaction)
        self._long_press_handled = False
        self.food_panel = FoodPanel(self.on_food)
        self.control_panel = PetControlPanel(
            on_mode=self.set_mode,
            on_size=self.set_size,
            on_feed=self._open_food_panel,
            on_say=self._say_daily_line,
            on_snap=self.snap_into_screen,
            on_awareness=self.set_awareness_enabled,
            on_read_window_title=lambda enabled: self._set_awareness_flag("read_window_title", enabled),
            on_idle_detection=lambda enabled: self._set_awareness_flag("idle_detection", enabled),
            on_topmost=self.set_topmost,
            on_fullscreen_hide=lambda enabled: self._set_awareness_flag("hide_on_fullscreen", enabled),
            on_passthrough=self.set_passthrough,
            on_autostart=self.set_autostart,
            on_activity_level=self.set_activity_level,
            on_walk_speed=self.set_walk_speed,
            on_reduced_motion=self.set_reduced_motion,
            on_hover_pause=self.set_hover_pause,
            on_desktop_surfaces=self.set_desktop_surfaces,
            on_action=self._preview_action,
            on_hide=self._hide_from_panel,
            on_privacy=self._show_privacy_notice,
            on_quit=self.quit_app,
        )
        self._create_tray()

        self._create_awareness()
        self._sync_animation_clip(crossfade=False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

        self.persistence_timer = QTimer(self)
        self.persistence_timer.timeout.connect(self.save_snapshot)
        self.persistence_timer.start(30_000)

        self._restore_position()
        self.show()
        self.snap_into_screen()
        self._sync_awareness_timer()
        self._sync_surface_timer()
        QTimer.singleShot(1_600, self._show_startup_recovery_line)
        QTimer.singleShot(10_000, self._auto_check_updates)

    # ----- window and rendering -------------------------------------------------

    @staticmethod
    def _height_for_size(multiplier: float) -> int:
        return round(BASE_SPRITE_HEIGHT * float(multiplier))

    @staticmethod
    def _normalized_size(value: object) -> float:
        try:
            candidate = float(value)
        except (TypeError, ValueError):
            return 0.70
        for multiplier in SIZE_LEVELS.values():
            if abs(candidate - multiplier) < 0.01:
                return multiplier
        return 0.70

    def _resize_window(self) -> None:
        widths = []
        for direction in ("left", "right", "up", "down"):
            # Special poses such as sleeping and being held can legitimately be
            # wider than the standing sprite.  Reserve their width up front so
            # switching action never crops arms, tail or the lower body.
            for action in PetAction:
                clip = self.asset_registry.clip_for(
                    action,
                    height=self.current_height,
                    direction=direction,
                )
                widths.extend(frame.pixmap.width() for frame in clip.frames)
        if not widths:
            raise RuntimeError("当前桌宠尺寸没有可用的精灵图。")
        horizontal_margin = int(self.current_height * 0.062) + 6
        self.setFixedSize(
            max(widths) + horizontal_margin * 2,
            self.current_height + BUBBLE_HEIGHT + MARGIN * 2 + 10,
        )

    def _restore_position(self) -> None:
        x, y = self.config.get("x"), self.config.get("y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        self.move(
            geometry.right() - self.width() + 1 - 80,
            geometry.bottom() - self.height() + 1 - 60,
        )

    def _physics_bounds(self, lookahead_seconds: float = 0.0) -> PhysicsBounds:
        if self.physics.active:
            center_x, center_y = self.physics.projected_center(
                lookahead_seconds,
                self.width(),
                self.height(),
            )
            probe = QPoint(round(center_x), round(center_y))
        else:
            probe = self.frameGeometry().center()
        screen = QApplication.screenAt(probe) or self.screen() or QApplication.primaryScreen()
        if screen is None:
            return PhysicsBounds(0.0, 0.0, float(self.width()), float(self.height()))
        geometry = screen.availableGeometry()
        work_areas = [candidate.availableGeometry() for candidate in QApplication.screens()]
        left = min((area.left() for area in work_areas), default=geometry.left())
        right = max((area.right() for area in work_areas), default=geometry.right())
        top = min((area.top() for area in work_areas), default=geometry.top())
        return PhysicsBounds(
            float(left),
            float(top),
            float(right),
            float(geometry.bottom()),
            platforms=self.surface_tracker.physics_platforms(
                work_area_top=float(top),
                widget_height=float(self.height()),
            ),
        )

    def _launch_throw(self, velocity_x: float, velocity_y: float, *, reason: str) -> None:
        self.surface_tracker.detach()
        self.movement.rest_after_drag()
        self.physics.launch(self.x(), self.y(), velocity_x, velocity_y)
        self._request_action(
            PetAction.FALLING,
            reason=reason,
            force=True,
            immediate=True,
        )

    def paintEvent(self, _event) -> None:
        self.renderer.paint(
            self,
            snapshot=self.player.snapshot(),
            bubble=self.bubble,
        )

    def _set_direction(self, direction: str, facing: int | None = None) -> None:
        if self.movement.set_direction(direction, facing):
            self._sync_animation_clip()

    def _sync_animation_clip(
        self,
        *,
        crossfade: bool = True,
        immediate: bool = False,
    ) -> None:
        program = self.asset_registry.program_for(
            self.action_machine.current,
            height=self.current_height,
            direction=self.movement.direction,
        )
        self.player.play(program, crossfade=crossfade, immediate=immediate)
        self._refresh_control_panel()

    def _request_action(
        self,
        action: PetAction,
        *,
        now: float | None = None,
        reason: str,
        force: bool = False,
        immediate: bool = False,
    ) -> bool:
        now = time.monotonic() if now is None else now
        change = self.action_machine.request(action, now=now, reason=reason, force=force)
        if change is None:
            return False
        self._sync_animation_clip(immediate=immediate)
        return True

    def _refresh_control_panel(self) -> None:
        awareness = self.config.section("awareness")
        comfort = self.config.section("comfort")
        self.control_panel.sync(
            mode=self.movement.mode,
            size=self._normalized_size(self.config.get("size", 0.70)),
            awareness=bool(awareness.get("enabled", True)),
            read_window_title=bool(awareness.get("read_window_title", True)),
            idle_detection=bool(awareness.get("idle_detection", True)),
            topmost=bool(self.config.get("topmost", True)),
            fullscreen_hide=bool(awareness.get("hide_on_fullscreen", False)),
            passthrough=bool(self.config.get("passthrough", False)),
            autostart=bool(self.config.get("autostart", False)),
            activity_level=str(comfort.get("activity_level", "balanced")),
            walk_speed=float(comfort.get("walk_speed", 82.0)),
            reduced_motion=bool(comfort.get("reduced_motion", False)),
            hover_pause=bool(comfort.get("hover_pause", True)),
            desktop_surfaces=bool(comfort.get("desktop_surfaces", True)),
            state_name=self._display_state_name(),
        )

    def _display_state_name(self) -> str:
        if self.action_machine.current != PetAction.IDLE:
            return STATE_NAMES.get(self.action_machine.current, "待机")
        return {
            "tired": "有点困",
            "annoyed": "闹脾气",
            "restless": "想走走",
            "cheerful": "心情很好",
            "affectionate": "很亲近",
            "steady": "待机",
        }.get(self.pet_state.visible_condition(), "待机")

    def _open_food_panel(self) -> None:
        self._interrupt_activity()
        self.food_panel.popup_at(
            self.x() + self.width() / 2,
            self.y() + BUBBLE_HEIGHT,
        )

    def _say_daily_line(self) -> None:
        self.say(self.dialogue.pick_daily(personality=self._personality()))

    def _preview_action(self, raw_action: str) -> None:
        try:
            action = PetAction.coerce(raw_action)
        except ValueError:
            return
        self._interrupt_activity()
        if action == PetAction.SLEEPING:
            self.movement.rest_after_drag()
        self.physics.cancel()
        self._request_action(action, reason="panel_preview", force=True, immediate=True)

    def _hide_from_panel(self) -> None:
        self.control_panel.hide()
        self.hide()

    # ----- main animation loop --------------------------------------------------

    def tick(self) -> None:
        now = time.monotonic()
        delta_seconds = min(0.10, max(0.001, now - self._last_tick_at))
        self._last_tick_at = now
        self.player.tick(delta_seconds)
        if self.action_machine.update(now=now) is not None:
            self._sync_animation_clip()
        if not self.physics.active and not self.interaction.active:
            attachment = self.surface_tracker.follow_attachment(
                now=now,
                widget_x=float(self.x()),
                widget_width=float(self.width()),
                widget_height=float(self.height()),
            )
            if attachment is not None:
                if attachment.lost:
                    self._launch_throw(0.0, 0.0, reason="surface_lost")
                    self._schedule_routine_line("window_lost", delay_ms=900)
                else:
                    self.move(round(attachment.x), round(attachment.y))
        walking = False
        movable_actions = {PetAction.IDLE, PetAction.THINKING, PetAction.WALKING}
        cue = self.activity_director.current_cue
        activity_allows_movement = (
            not self.activity_director.active
            or (cue is not None and cue.kind == ActivityCueType.WALK)
        )
        hover_paused = self._hovered and bool(
            self.config.section("comfort").get("hover_pause", True)
        )
        if self.physics.active:
            self._tick_throw(delta_seconds, now)
        elif (
            not self.interaction.active
            and not hover_paused
            and activity_allows_movement
            and self.action_machine.current in movable_actions
        ):
            walking = self.movement.update(
                self,
                now=now,
                delta_seconds=delta_seconds,
                set_direction=self._set_direction,
                energy=self.pet_state.energy,
                horizontal_bounds=self.surface_tracker.movement_bounds(
                    widget_width=float(self.width())
                ),
            )
            if self.surface_tracker.attached:
                self.surface_tracker.record_pet_position(
                    widget_x=float(self.x()),
                    widget_width=float(self.width()),
                )
        if walking:
            self._request_action(PetAction.WALKING, now=now, reason="movement")
        elif not self.interaction.dragging and self.action_machine.current == PetAction.WALKING:
            self._request_action(PetAction.IDLE, now=now, reason="movement_stop", force=True)
        self._tick_activity(now)
        self._tick_micro_motion(now)
        if now - self._last_state_update >= 5.0:
            self.pet_state.advance(
                now - self._last_state_update,
                activity=self.action_machine.current.value.lower(),
            )
            self._last_state_update = now
        self.update()

    def _tick_throw(self, delta_seconds: float, now: float) -> None:
        step = self.physics.step(
            delta_seconds,
            width=self.width(),
            height=self.height(),
            bounds=self._physics_bounds(delta_seconds),
        )
        self.move(round(step.x), round(step.y))
        if not step.settled:
            return

        self.movement.rest_after_drag(now)
        self._set_direction("down")
        if step.landed_surface_id:
            self.surface_tracker.attach(
                step.landed_surface_id,
                widget_x=float(self.x()),
                widget_width=float(self.width()),
            )
        else:
            self.surface_tracker.detach()
        if self._request_action(
            PetAction.LANDING,
            now=now,
            reason="hard_landing" if step.hard_landing else "landing",
            force=True,
            immediate=True,
        ) and step.hard_landing:
            self.action_machine.queue_after_current(PetAction.DIZZY)
        if step.landed_surface_id:
            self._schedule_routine_line("window_land", delay_ms=1_100)
        elif step.hard_landing:
            self._schedule_routine_line("hard_landing", delay_ms=2_200)
        else:
            self._schedule_routine_line("soft_landing", delay_ms=1_000)

    def _tick_activity(self, now: float) -> None:
        hover_paused = self._hovered and bool(
            self.config.section("comfort").get("hover_pause", True)
        )
        command = self.activity_director.update(
            now=now,
            state=self.pet_state,
            can_start=(
                self.action_machine.current == PetAction.IDLE
                and not self.interaction.active
                and not self.movement.is_walking
                and not self.control_panel.isVisible()
                and not self.food_panel.isVisible()
                and not hover_paused
            ),
            is_walking=self.movement.is_walking,
            allow_movement=self.movement.mode == "wander",
        )
        if command is not None:
            self._execute_activity_command(command, now)

    def _tick_micro_motion(self, now: float) -> None:
        comfort = self.config.section("comfort")
        hover_paused = self._hovered and bool(comfort.get("hover_pause", True))
        action = self.micro_motion_director.update(
            now=now,
            state=self.pet_state,
            can_start=(
                self.action_machine.current == PetAction.IDLE
                and not self.activity_director.active
                and not self.interaction.active
                and not self.movement.is_walking
                and not self.physics.active
                and not self.control_panel.isVisible()
                and not self.food_panel.isVisible()
                and not hover_paused
            ),
            reduced_motion=bool(comfort.get("reduced_motion", False)),
        )
        if action is not None:
            self._request_action(action, now=now, reason="idle_micro_motion")

    def _execute_activity_command(self, command: ActivityCommand, now: float) -> None:
        reason = f"activity_{command.activity.value}"
        if command.cue_type == ActivityCueType.COMPLETE:
            self.pet_state.finish_activity(command.activity.value)
            return
        if command.cue_type == ActivityCueType.WALK:
            started = self.movement.request_short_wander(
                self,
                body_widths=command.distance_body_widths,
                now=now,
                away_from_cursor=command.away_from_cursor,
                horizontal_bounds=self.surface_tracker.movement_bounds(
                    widget_width=float(self.width())
                ),
            )
            if not started:
                self.activity_director.skip_walk(now=now)
            return
        if command.cue_type == ActivityCueType.SPEAK:
            personality = self._personality()
            condition = self.pet_state.visible_condition()
            line = None
            if condition != "steady" and self.rng.random() < 0.72:
                line = self.dialogue.pick_state(condition, personality=personality)
            if line is None:
                line = (
                    self.dialogue.pick_inner_voice(personality=personality)
                    if command.inner
                    else self.dialogue.pick_daily(personality=personality)
                )
            self.say(line, inner=command.inner, from_activity=True)
            return
        if command.action is None:
            self.activity_director.interrupt(now=now)
            return
        changed = self._request_action(command.action, now=now, reason=reason)
        if not changed and self.action_machine.current != command.action:
            self.activity_director.interrupt(now=now)

    def _interrupt_activity(self, *, delay_seconds: float | None = None) -> None:
        now = time.monotonic()
        interrupted = self.activity_director.interrupt(
            now=now,
            delay_seconds=delay_seconds,
        )
        self.micro_motion_director.defer(now, minimum_seconds=3.0)
        self.movement.cancel_target()
        if interrupted is not None and self.action_machine.current == PetAction.SLEEPING:
            self._request_action(PetAction.IDLE, reason="activity_interrupted", force=True)

    def say(
        self,
        text: str | None,
        *,
        inner: bool = False,
        from_activity: bool = False,
        preserve_action: bool = False,
    ) -> bool:
        if not from_activity:
            self._interrupt_activity()
        if not text or text == self._last_line:
            return False
        self._last_line = text
        if not preserve_action:
            action = PetAction.THINKING if inner else PetAction.TALKING
            self._request_action(action, reason="inner_voice" if inner else "speech")
        now = time.monotonic()
        display_seconds = min(5.4, max(2.9, 1.9 + len(text) * 0.18))
        self.bubble = Bubble(
            text=f"（{text}）" if inner else text,
            until=now + display_seconds,
            appeared_at=now,
            inner=inner,
            state_name=STATE_NAMES.get(self.action_machine.current, ""),
        )
        self.update()
        return True

    def _schedule_routine_line(self, situation: str, *, delay_ms: int) -> None:
        def speak() -> None:
            line = self.dialogue.pick_routine(
                situation,
                personality=self._personality(),
            )
            self.say(line)

        QTimer.singleShot(max(0, int(delay_ms)), speak)

    def _show_startup_recovery_line(self) -> None:
        if self.recovery_status.safe_mode:
            situation = "safe_mode"
        elif self.recovery_status.unclean_exit:
            situation = "recovered"
        elif self._first_session_today:
            situation = "first_today"
        else:
            line = self.dialogue.pick_relationship(
                self.pet_state.affinity,
                personality=self._personality(),
            )
            self.say(line)
            return
        self.say(self.dialogue.pick_routine(situation, personality=self._personality()))

    def save_snapshot(self) -> None:
        """Atomically persist the small recoverable state during long sessions."""
        self.config.set("x", self.x(), save=False)
        self.config.set("y", self.y(), save=False)
        self.config.save()
        self.state_store.save(self.pet_state)

    # ----- user interaction -----------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._interrupt_activity()
        position = event.globalPosition().toPoint()
        self._caught_throw = self.physics.active
        if self._caught_throw:
            self.physics.cancel()
            self.movement.cancel_target()
            self._request_action(
                PetAction.DRAGGING,
                reason="midair_catch",
                force=True,
                immediate=True,
            )
        self._drag_last_pos = position
        self._drag_offset = None
        self._long_press_handled = False
        self.interaction.press(
            position,
            event.position().x(),
            event.position().y(),
            0.0,
            BUBBLE_HEIGHT + MARGIN,
            self.width(),
            self.current_height,
        )
        if self.interaction.body_region in {"head", "face"}:
            self._hold_timer.start(620)

    def mouseMoveEvent(self, event) -> None:
        if not event.buttons() & Qt.MouseButton.LeftButton:
            return
        position = event.globalPosition().toPoint()
        if not self.interaction.move(position):
            return
        if self._drag_offset is None:
            self._click_timer.stop()
            self._hold_timer.stop()
            self._drag_offset = position - QPoint(self.x(), self.y())
            self.physics.cancel()
            self.surface_tracker.detach()
            self._request_action(
                PetAction.DRAGGING,
                reason="drag_start",
                force=True,
                immediate=True,
            )
        self.move(position - self._drag_offset)
        if self._drag_last_pos is not None:
            delta = position - self._drag_last_pos
            if abs(delta.x()) > 10:
                self._set_direction("left" if delta.x() < 0 else "right")
        self._drag_last_pos = position
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        outcome = self.interaction.release(event.globalPosition().toPoint())
        self._hold_timer.stop()
        caught_throw = self._caught_throw
        self._caught_throw = False
        self._drag_offset = None
        self._drag_last_pos = None
        if outcome is None:
            return
        if outcome.kind == "drag":
            self.pet_state.drag()
            throw_speed = (
                outcome.velocity_x * outcome.velocity_x + outcome.velocity_y * outcome.velocity_y
            ) ** 0.5
            self._launch_throw(
                outcome.velocity_x,
                outcome.velocity_y,
                reason="fast_release" if throw_speed >= 900.0 else "drag_release",
            )
            drag_key = "drag_fast" if throw_speed >= 900.0 else "drag_gentle"
            self.say(
                self.dialogue.pick_interaction(drag_key, personality=self._personality())
                or self.dialogue.pick_interaction("drag", personality=self._personality()),
                preserve_action=True,
            )
            return
        if caught_throw:
            self.pet_state.drag()
            self._launch_throw(0.0, 0.0, reason="caught_release")
            return
        if self._long_press_handled:
            self._long_press_handled = False
            return
        self._pending_click_region = outcome.body_region
        self._click_timer.start(280)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._click_timer.stop()
        self._hold_timer.stop()
        self.food_panel.popup_at(
            self.x() + self.width() / 2,
            self.y() + BUBBLE_HEIGHT,
        )

    def _do_click_reaction(self) -> None:
        region = self._pending_click_region
        personality = self._personality()
        if region == "head":
            self.pet_state.pet_head()
            self._request_action(PetAction.HEAD_PAT, reason="head_pat")
            self.say(
                self.dialogue.pick_interaction("head", personality=personality),
                preserve_action=True,
            )
            return

        now = time.monotonic()
        self._recent_pokes.append(now)
        recent_count = sum(1 for timestamp in self._recent_pokes if now - timestamp <= 5.0)
        intensity = {"face": 1.15, "body": 1.0, "tail": 2.0}.get(region, 1.0)
        self.pet_state.tap(intensity)
        if recent_count >= 3:
            self._request_action(PetAction.ANGRY, reason="repeated_poke")
            self.say(
                self.dialogue.pick_routine("repeated_poke", personality=personality),
                preserve_action=True,
            )
            return
        if region == "tail":
            self._request_action(PetAction.TAIL_REACT, reason="tail_touch")
            self.say(
                self.dialogue.pick_routine("tail_touch", personality=personality),
                preserve_action=True,
            )
            return
        reaction = PetAction.ANGRY if self.pet_state.annoyance >= 0.26 else PetAction.POKE_REACT
        self._request_action(reaction, reason=f"poke_{region}")
        self.say(
            self.dialogue.pick_interaction(region, personality=personality)
            or self.dialogue.pick_interaction("tap", personality=personality),
            preserve_action=True,
        )

    def _do_long_press_reaction(self) -> None:
        if not self.interaction.active or self.interaction.dragging:
            return
        if self.interaction.body_region not in {"head", "face"}:
            return
        self._long_press_handled = True
        self.pet_state.pet_head()
        self._request_action(PetAction.HEAD_PAT, reason="long_head_pat")
        self.say(
            self.dialogue.pick_interaction("head_hold", personality=self._personality())
            or self.dialogue.pick_interaction("head", personality=self._personality()),
            preserve_action=True,
        )

    def on_food(self, _food: str) -> None:
        self._interrupt_activity()
        self.food_panel.hide()
        self.pet_state.feed()
        now = time.monotonic()
        self._recent_feedings.append(now)
        self._request_action(PetAction.EATING, reason="feed")
        recent_count = sum(1 for timestamp in self._recent_feedings if now - timestamp <= 20.0)
        if recent_count >= 3:
            line = self.dialogue.pick_routine("repeated_feed", personality=self._personality())
        else:
            line = self.dialogue.pick_interaction("food", personality=self._personality())
        self.say(line, preserve_action=True)

    # ----- local environment awareness -----------------------------------------

    def _create_awareness(self) -> None:
        classifier = AppClassifier(self.paths.assets_dir / "app_categories.json")
        privacy = PrivacyPolicy(self.paths.assets_dir / "privacy_rules.json")
        self.context_sensor = ContextSensor(classifier, privacy)
        self.awareness_timer = QTimer(self)
        self.awareness_timer.timeout.connect(self._poll_context)
        self.surface_timer = QTimer(self)
        self.surface_timer.timeout.connect(self._poll_surface)
        self._hidden_by_fullscreen = False
        self._rebuild_behavior_components()

    def _rebuild_behavior_components(self) -> None:
        awareness = self.config.section("awareness")
        self.context_scheduler = ContextEventScheduler(
            min_dwell_seconds=float(awareness.get("min_dwell_seconds", 15)),
        )
        self.cooldown = Cooldown(
            float(awareness.get("global_cooldown_seconds", 150)),
            float(awareness.get("context_cooldown_seconds", 900)),
        )
        self.behavior_engine = BehaviorEngine(self.dialogue, self.cooldown)

    def _sync_awareness_timer(self) -> None:
        awareness = self.config.section("awareness")
        if awareness.get("enabled", True):
            interval = max(500, int(awareness.get("poll_interval_ms", 1000)))
            self.awareness_timer.start(interval)
        else:
            self.awareness_timer.stop()

    def _sync_surface_timer(self) -> None:
        if bool(self.config.section("comfort").get("desktop_surfaces", True)):
            self.surface_timer.start(800)
        else:
            self.surface_timer.stop()

    def _poll_surface(self) -> None:
        ignored = {int(self.winId()), int(self.control_panel.winId()), int(self.food_panel.winId())}
        self.surface_tracker.observe_foreground(ignored_handles=ignored)

    def _poll_context(self) -> None:
        awareness = self.config.section("awareness")
        privacy = self.config.section("privacy")
        snapshot = self.context_sensor.capture(
            read_window_title=bool(awareness.get("read_window_title", True)),
            idle_detection=bool(awareness.get("idle_detection", True)),
            custom_private_process_names=privacy.get("custom_process_names", []),
        )
        if snapshot is None:
            return
        self.surface_tracker.observe_window(snapshot.window_handle)
        self.activity_director.observe_context(
            category=snapshot.category,
            idle_seconds=snapshot.idle_seconds,
            private=snapshot.is_private,
            late_night=time.localtime().tm_hour >= 23,
        )
        events = self.context_scheduler.observe(snapshot)
        for event in events:
            if event.type == EventType.FULLSCREEN_ENTER and awareness.get(
                "hide_on_fullscreen", True
            ):
                if self.isVisible():
                    self._hidden_by_fullscreen = True
                    self.control_panel.hide()
                    self.hide()
            elif event.type == EventType.FULLSCREEN_EXIT and self._hidden_by_fullscreen:
                self._hidden_by_fullscreen = False
                self.show()
                self.raise_()

        reaction = self.behavior_engine.react(
            snapshot,
            events,
            personality=self._personality(),
        )
        if reaction is not None:
            self.say(reaction.text, inner=reaction.inner)

    def set_awareness_enabled(self, enabled: bool) -> None:
        self.config.set_nested("awareness", "enabled", bool(enabled))
        self._rebuild_behavior_components()
        self._sync_awareness_timer()
        self._refresh_control_panel()
        if enabled:
            self.say("本地环境感知已开启。")
        else:
            self.say("本地环境感知已暂停。")

    def _set_awareness_flag(self, key: str, enabled: bool) -> None:
        self.config.set_nested("awareness", key, bool(enabled))
        self._refresh_control_panel()

    # ----- menus, tray, and persistence ----------------------------------------

    def contextMenuEvent(self, event) -> None:
        self._interrupt_activity()
        self._refresh_control_panel()
        self.control_panel.popup_near_pet(self.frameGeometry())
        event.accept()

    def _create_tray(self) -> None:
        icon = QIcon(str(self.paths.sprite_dir / "icon.png"))
        self.tray = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()
        tray_menu.addAction("显示/隐藏", self.toggle_visible)
        tray_menu.addAction("打开快速控制", self._open_control_panel_from_tray)
        tray_menu.addAction(
            "暂停/启用环境感知",
            lambda: self.set_awareness_enabled(
                not bool(self.config.section("awareness").get("enabled", True))
            ),
        )
        self.update_action = tray_menu.addAction("检查更新", self._handle_update_action)
        tray_menu.addSeparator()
        tray_menu.addAction("退出", self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _auto_check_updates(self) -> None:
        # Source checkouts remain fully offline unless the developer explicitly
        # chooses the tray action.  Installed/portable frozen builds perform the
        # lightweight daily GitHub Releases check.
        if not getattr(sys, "frozen", False):
            return
        settings = self.config.section("updates")
        if not bool(settings.get("enabled", True)):
            return
        try:
            last_checked = float(settings.get("last_checked_at", 0.0))
        except (TypeError, ValueError):
            last_checked = 0.0
        if time.time() - last_checked >= 24.0 * 3600.0:
            self._check_updates(manual=False)

    def _check_updates(self, *, manual: bool) -> None:
        if self.update_service.check_async(manual=manual):
            self.update_action.setText("正在检查更新…")

    def _handle_update_action(self) -> None:
        if self._downloaded_update is not None and self._available_update is not None:
            self._offer_install_update(self._available_update, self._downloaded_update)
            return
        if self._available_update is not None:
            if self.update_service.download_async(self._available_update):
                self.update_action.setText(f"正在下载 v{self._available_update.version}…")
            return
        self._check_updates(manual=True)

    def _on_update_checked(self, info: object, manual: bool) -> None:
        self.config.set_nested("updates", "last_checked_at", time.time())
        if not isinstance(info, UpdateInfo):
            self.update_action.setText("检查更新")
            if manual:
                QMessageBox.information(self, "检查更新", f"当前已是最新版 v{VERSION}。")
            return
        self._available_update = info
        self.update_action.setText(f"下载更新 v{info.version}")
        self.say(
            self.dialogue.pick_routine("update_available", personality=self._personality())
            or f"发现新版本 v{info.version}，我可以自己准备更新。"
        )
        if self.update_service.download_async(info):
            self.update_action.setText(f"正在下载 v{info.version}…")

    def _on_update_check_failed(self, message: str, manual: bool) -> None:
        self.update_action.setText("检查更新")
        if manual:
            QMessageBox.warning(self, "检查更新", message)

    def _on_update_downloaded(self, info: object, path: object) -> None:
        if not isinstance(info, UpdateInfo) or not isinstance(path, Path):
            return
        self._available_update = info
        self._downloaded_update = path
        self.update_action.setText(f"安装更新 v{info.version}")
        self._offer_install_update(info, path)

    def _on_update_download_failed(self, message: str) -> None:
        version = self._available_update.version if self._available_update else ""
        self.update_action.setText(f"重试下载 v{version}" if version else "检查更新")
        QMessageBox.warning(self, "自动更新", message)

    def _offer_install_update(self, info: UpdateInfo, path: Path) -> None:
        answer = QMessageBox.question(
            self,
            "大肥鱼更新已准备好",
            f"v{info.version} 已下载并通过 SHA-256 校验。\n\n"
            "现在安装并重新启动大肥鱼吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.save_snapshot()
            launch_installer(path)
        except Exception as error:
            QMessageBox.warning(self, "自动更新", f"无法启动安装程序：{error}")
            return
        QTimer.singleShot(500, self.quit_app)

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def _open_control_panel_from_tray(self) -> None:
        self._interrupt_activity()
        self._refresh_control_panel()
        self.control_panel.popup_at(self.pos())

    def set_mode(self, mode: str) -> None:
        self._interrupt_activity(delay_seconds=1.5)
        self.movement.set_mode(mode)
        self.config.set("mode", self.movement.mode)
        self._refresh_control_panel()

    def set_activity_level(self, level: str) -> None:
        level = ActivityDirector._normalized_activity_level(level)
        now = time.monotonic()
        self.activity_director.set_activity_level(level, now=now)
        self.micro_motion_director.set_activity_level(level, now=now)
        self.config.set_nested("comfort", "activity_level", level)
        self._refresh_control_panel()

    def set_walk_speed(self, speed: float) -> None:
        speed = min((64.0, 82.0, 104.0), key=lambda value: abs(value - float(speed)))
        self.movement.set_speed(speed)
        self.config.set_nested("comfort", "walk_speed", speed)
        self._refresh_control_panel()

    def set_reduced_motion(self, enabled: bool) -> None:
        enabled = bool(enabled)
        self.renderer.set_reduced_motion(enabled)
        self.config.set_nested("comfort", "reduced_motion", enabled)
        self._refresh_control_panel()
        self.update()

    def set_hover_pause(self, enabled: bool) -> None:
        self.config.set_nested("comfort", "hover_pause", bool(enabled))
        self._refresh_control_panel()

    def set_desktop_surfaces(self, enabled: bool) -> None:
        dropped = self.surface_tracker.set_enabled(bool(enabled))
        self.config.set_nested("comfort", "desktop_surfaces", bool(enabled))
        self._sync_surface_timer()
        self._refresh_control_panel()
        if dropped and not self.physics.active and not self.interaction.active:
            self._launch_throw(0.0, 0.0, reason="surfaces_disabled")

    def set_size(self, multiplier: float) -> None:
        self.physics.cancel()
        multiplier = self._normalized_size(multiplier)
        self.current_height = self._height_for_size(multiplier)
        self.config.set("size", multiplier)
        self._resize_window()
        self._sync_animation_clip(crossfade=False, immediate=True)
        self.snap_into_screen()

    def snap_into_screen(self) -> None:
        self.physics.cancel()
        self.surface_tracker.detach()
        self.movement.cancel_target()
        screen = (
            QApplication.screenAt(self.frameGeometry().center())
            or self.screen()
            or QApplication.primaryScreen()
        )
        if screen is None:
            return
        geometry = screen.availableGeometry()
        max_x = geometry.right() - self.width() + 1
        max_y = geometry.bottom() - self.height() + 1
        self.move(max(geometry.left(), min(max_x, self.x())), max_y)

    def enterEvent(self, event) -> None:
        self._hovered = True
        if bool(self.config.section("comfort").get("hover_pause", True)):
            self._interrupt_activity(delay_seconds=5.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        super().leaveEvent(event)

    def set_passthrough(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if sys.platform != "win32":
            QMessageBox.information(self, "鼠标穿透", "鼠标穿透目前仅在 Windows 上可用。")
            return
        try:
            user32 = ctypes.windll.user32
            handle = int(self.winId())
            get_style = user32.GetWindowLongPtrW
            set_style = user32.SetWindowLongPtrW
            style = get_style(handle, -20)
            layered = 0x80000
            transparent = 0x20
            new_style = style | layered | (transparent if enabled else 0)
            if not enabled:
                new_style &= ~transparent
            set_style(handle, -20, new_style)
            self.config.set("passthrough", enabled)
            self._refresh_control_panel()
            if enabled:
                self.say("我隐身了！右键托盘图标可以解除。")
        except OSError as error:
            QMessageBox.warning(self, "鼠标穿透", f"设置失败：{error}")

    def set_topmost(self, enabled: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(enabled))
        self.config.set("topmost", bool(enabled))
        self.show()
        self._refresh_control_panel()

    def set_autostart(self, enabled: bool) -> None:
        enabled = bool(enabled)
        startup_dir = Path(
            os.environ.get(
                "APPDATA",
                str(Path.home() / "AppData" / "Roaming"),
            )
        ) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        link = startup_dir / "大肥鱼桌宠.lnk"
        try:
            if enabled:
                pythonw = self.paths.app_dir / ".venv" / "Scripts" / "pythonw.exe"
                interpreter = Path(sys.executable)
                system_pythonw = interpreter.with_name("pythonw.exe")
                target = str(
                    interpreter
                    if getattr(sys, "frozen", False)
                    else (pythonw if pythonw.exists() else system_pythonw if system_pythonw.exists() else interpreter)
                )
                arguments = "" if getattr(sys, "frozen", False) else f'"{self.paths.app_dir / "main.py"}"'
                quote = lambda value: value.replace("'", "''")
                script = (
                    "$shortcut=(New-Object -ComObject WScript.Shell).CreateShortcut('"
                    + quote(str(link))
                    + "');$shortcut.TargetPath='"
                    + quote(target)
                    + "';$shortcut.Arguments='"
                    + quote(arguments)
                    + "';$shortcut.WorkingDirectory='"
                    + quote(str(self.paths.app_dir))
                    + "';$shortcut.Save()"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", script],
                    check=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self.say("已设置开机自启，明天见。")
            elif link.exists():
                link.unlink()
                self.say("已取消开机自启。")
            self.config.set("autostart", enabled)
            self._refresh_control_panel()
        except (OSError, subprocess.CalledProcessError) as error:
            QMessageBox.warning(self, "开机自启", f"设置失败：{error}")

    def toggle_visible(self) -> None:
        if self.isVisible():
            self._hidden_by_fullscreen = False
            self.control_panel.hide()
            self.hide()
        else:
            self.show()
            self.raise_()

    def activate_from_shortcut(self) -> None:
        """Bring the existing pet back when its shortcut is clicked again."""
        self._hidden_by_fullscreen = False
        self.show()
        self.raise_()
        self.activateWindow()

    def _show_privacy_notice(self) -> None:
        QMessageBox.information(
            self,
            "本地隐私规则",
            "环境感知只在本机读取前台进程名、窗口标题、空闲时长和全屏状态。\n\n"
            "开启“窗口落脚”时，只额外读取前台窗口句柄和外框位置，用来判断顶部落点与随动；不会读取窗口内容。\n\n"
            "密码管理器、支付/银行、远程桌面、聊天和邮件应用，以及无痕窗口默认不保留标题，也不会触发台词。"
            "\n\n不会截图、不会读取浏览历史、不会把感知数据发送到网络。",
        )

    def _personality(self) -> str:
        return normalize_personality(self.config.get("personality", "standard"))

    def quit_app(self) -> None:
        self.save_snapshot()
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        self.quit_app()
        event.accept()
