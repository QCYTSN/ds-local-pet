from __future__ import annotations

import ctypes
import os
import random
import subprocess
import sys
import time
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
from awareness.privacy import PrivacyPolicy
from awareness.sensor import ContextSensor
from animation.asset_registry import AssetRegistry
from animation.clip import PetAction
from animation.player import AnimationPlayer
from animation.state_machine import ActionStateMachine
from behavior.behavior_engine import BehaviorEngine
from behavior.classifier import AppClassifier
from behavior.cooldown import Cooldown
from behavior.events import EventType
from behavior.scheduler import ContextEventScheduler
from dialogue.local_rules import DialogueManager
from dialogue.personality import normalize_personality
from pet.interaction import FoodPanel, InteractionController
from pet.movement import MovementController
from pet.renderer import Bubble, PetRenderer
from pet.state import PetStateStore
from settings.config import ConfigManager
from settings.panel import PetControlPanel


BUBBLE_HEIGHT = 66
MARGIN = 4
BASE_SPRITE_HEIGHT = 340
SIZE_LEVELS = {"小": 0.55, "中": 0.70, "大": 0.90}
TICK_MS = 20

STATE_NAMES = {
    PetAction.IDLE: "待机",
    PetAction.THINKING: "发呆",
    PetAction.WALKING: "散步",
    PetAction.HAPPY: "开心",
    PetAction.TALKING: "说话",
    PetAction.ANGRY: "生气",
    PetAction.POKE_REACT: "被戳",
    PetAction.EATING: "吃东西",
    PetAction.SWEEPING: "扫地",
    PetAction.SLEEPING: "睡觉",
    PetAction.DRAGGING: "抓取中",
    PetAction.FALLING: "落下",
    PetAction.DIZZY: "眩晕",
}


class PetWindow(QWidget):
    """The transparent desktop pet window and the wiring between its modules."""

    def __init__(self, paths: AppPaths, config: ConfigManager) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if config.get("topmost", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.paths = paths
        self.config = config
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

        self.movement = MovementController(config.get("mode", "wander"))
        self.interaction = InteractionController()
        self.renderer = PetRenderer(BUBBLE_HEIGHT, MARGIN)
        self.bubble = Bubble()
        self._last_line = ""
        self._last_tick_at = time.monotonic()
        self._last_state_update = self._last_tick_at
        self._last_idle_speech_at = float("-inf")
        self._drag_offset: QPoint | None = None
        self._drag_last_pos: QPoint | None = None
        self._pending_click_region = "body"

        self.dialogue = DialogueManager(paths.assets_dir / "dialogue", self.rng)
        self.state_store = PetStateStore(paths.state_path)
        self.pet_state = self.state_store.load()

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._do_click_reaction)
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

        self._restore_position()
        self.show()
        self.snap_into_screen()
        self._sync_awareness_timer()

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

    def paintEvent(self, _event) -> None:
        self.renderer.paint(
            self,
            snapshot=self.player.snapshot(),
            bubble=self.bubble,
        )

    def _set_direction(self, direction: str, facing: int | None = None) -> None:
        if self.movement.set_direction(direction, facing):
            self._sync_animation_clip()

    def _sync_animation_clip(self, *, crossfade: bool = True) -> None:
        clip = self.asset_registry.clip_for(
            self.action_machine.current,
            height=self.current_height,
            direction=self.movement.direction,
        )
        self.player.play(clip, crossfade=crossfade)
        self._refresh_control_panel()

    def _request_action(
        self,
        action: PetAction,
        *,
        now: float | None = None,
        reason: str,
        force: bool = False,
    ) -> bool:
        now = time.monotonic() if now is None else now
        change = self.action_machine.request(action, now=now, reason=reason, force=force)
        if change is None:
            return False
        self._sync_animation_clip()
        return True

    def _refresh_control_panel(self) -> None:
        awareness = self.config.section("awareness")
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
            state_name=STATE_NAMES.get(self.action_machine.current, "待机"),
        )

    def _open_food_panel(self) -> None:
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
        if action == PetAction.SLEEPING:
            self.movement.rest_after_drag()
        self._request_action(action, reason="panel_preview", force=True)

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
        walking = False
        movable_actions = {PetAction.IDLE, PetAction.THINKING, PetAction.WALKING}
        if not self.interaction.dragging and self.action_machine.current in movable_actions:
            walking = self.movement.update(
                self,
                now=now,
                delta_seconds=delta_seconds,
                set_direction=self._set_direction,
            )
        if walking:
            self._request_action(PetAction.WALKING, now=now, reason="movement")
        elif not self.interaction.dragging and self.action_machine.current == PetAction.WALKING:
            self._request_action(PetAction.IDLE, now=now, reason="movement_stop", force=True)
        if not walking and not self.interaction.dragging:
            self._maybe_idle_action(now)
        if now - self._last_state_update >= 5.0:
            self.pet_state.advance(now - self._last_state_update)
            self._last_state_update = now
        self.update()

    def _maybe_idle_action(self, now: float) -> None:
        if self.action_machine.current != PetAction.IDLE or self.rng.random() >= 0.0015:
            return
        pick = self.rng.random()
        if pick < 0.28:
            self._request_action(PetAction.THINKING, now=now, reason="idle_thought")
        elif pick < 0.48:
            self._request_action(PetAction.HAPPY, now=now, reason="idle_delight")
        elif pick < 0.65:
            self._request_action(PetAction.SWEEPING, now=now, reason="idle_chore")
        elif pick < 0.78 and self.pet_state.energy < 0.38:
            self._request_action(PetAction.SLEEPING, now=now, reason="low_energy")
        elif now - self._last_idle_speech_at >= 30.0:
            self._last_idle_speech_at = now
            personality = self._personality()
            if pick < 0.90:
                line = self.dialogue.pick_inner_voice(personality=personality)
                self.say(line, inner=True)
            else:
                self.say(self.dialogue.pick_daily(personality=personality))

    def say(self, text: str | None, *, inner: bool = False) -> bool:
        if not text or text == self._last_line:
            return False
        self._last_line = text
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

    # ----- user interaction -----------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        position = event.globalPosition().toPoint()
        self._drag_last_pos = position
        self._drag_offset = None
        self.interaction.press(
            position,
            event.position().y(),
            BUBBLE_HEIGHT + MARGIN,
            self.current_height,
        )

    def mouseMoveEvent(self, event) -> None:
        if not event.buttons() & Qt.MouseButton.LeftButton:
            return
        position = event.globalPosition().toPoint()
        if not self.interaction.move(position):
            return
        if self._drag_offset is None:
            self._click_timer.stop()
            self._drag_offset = position - QPoint(self.x(), self.y())
            self._request_action(PetAction.DRAGGING, reason="drag_start", force=True)
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
        self._drag_offset = None
        self._drag_last_pos = None
        if outcome is None:
            return
        if outcome.kind == "drag":
            self._set_direction("down")
            self.movement.rest_after_drag()
            self.pet_state.drag()
            throw_speed = (outcome.velocity_x * outcome.velocity_x + outcome.velocity_y * outcome.velocity_y) ** 0.5
            if throw_speed >= 1150.0:
                if self._request_action(PetAction.FALLING, reason="fast_release", force=True):
                    self.action_machine.queue_after_current(PetAction.DIZZY)
            else:
                self._request_action(PetAction.IDLE, reason="drag_release", force=True)
            self.say(self.dialogue.pick_interaction("drag", personality=self._personality()))
            return
        self._pending_click_region = outcome.body_region
        self._click_timer.start(280)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._click_timer.stop()
        self.food_panel.popup_at(
            self.x() + self.width() / 2,
            self.y() + BUBBLE_HEIGHT,
        )

    def _do_click_reaction(self) -> None:
        region = self._pending_click_region
        personality = self._personality()
        if region == "head":
            self.pet_state.pet_head()
            self._request_action(PetAction.HAPPY, reason="head_pat")
            self.say(self.dialogue.pick_interaction("head", personality=personality))
        else:
            self.pet_state.tap()
            reaction = PetAction.ANGRY if self.pet_state.annoyance >= 0.26 else PetAction.POKE_REACT
            self._request_action(reaction, reason="poke")
            self.say(self.dialogue.pick_interaction("tap", personality=personality))

    def on_food(self, _food: str) -> None:
        self.food_panel.hide()
        self.pet_state.feed()
        self._request_action(PetAction.EATING, reason="feed")
        self.say(self.dialogue.pick_interaction("food", personality=self._personality()))

    # ----- local environment awareness -----------------------------------------

    def _create_awareness(self) -> None:
        classifier = AppClassifier(self.paths.assets_dir / "app_categories.json")
        privacy = PrivacyPolicy(self.paths.assets_dir / "privacy_rules.json")
        self.context_sensor = ContextSensor(classifier, privacy)
        self.awareness_timer = QTimer(self)
        self.awareness_timer.timeout.connect(self._poll_context)
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
        self._refresh_control_panel()
        self.control_panel.popup_near_pet(self.frameGeometry())
        event.accept()

    def _create_tray(self) -> None:
        icon = QIcon(str(self.paths.sprite_dir / "icon.png"))
        self.tray = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()
        tray_menu.addAction("显示/隐藏", self.toggle_visible)
        tray_menu.addAction("打开快速控制", lambda: self.control_panel.popup_at(self.pos()))
        tray_menu.addAction(
            "暂停/启用环境感知",
            lambda: self.set_awareness_enabled(
                not bool(self.config.section("awareness").get("enabled", True))
            ),
        )
        tray_menu.addSeparator()
        tray_menu.addAction("退出", self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def set_mode(self, mode: str) -> None:
        self.movement.set_mode(mode)
        self.config.set("mode", self.movement.mode)
        self._refresh_control_panel()

    def set_size(self, multiplier: float) -> None:
        multiplier = self._normalized_size(multiplier)
        self.current_height = self._height_for_size(multiplier)
        self.config.set("size", multiplier)
        self._resize_window()
        self._sync_animation_clip(crossfade=False)
        self.snap_into_screen()

    def snap_into_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        max_x = geometry.right() - self.width() + 1
        max_y = geometry.bottom() - self.height() + 1
        self.move(
            max(geometry.left(), min(max_x, self.x())),
            max(geometry.top(), min(max_y, self.y())),
        )

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
            "密码管理器、支付/银行、远程桌面、聊天和邮件应用，以及无痕窗口默认不保留标题，也不会触发台词。"
            "\n\n不会截图、不会读取浏览历史、不会把感知数据发送到网络。",
        )

    def _personality(self) -> str:
        return normalize_personality(self.config.get("personality", "standard"))

    def quit_app(self) -> None:
        self.config.set("x", self.x(), save=False)
        self.config.set("y", self.y(), save=False)
        self.config.save()
        self.state_store.save(self.pet_state)
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        self.quit_app()
        event.accept()
