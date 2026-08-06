from __future__ import annotations

import ctypes
import os
import random
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
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
from behavior.behavior_engine import BehaviorEngine
from behavior.classifier import AppClassifier
from behavior.cooldown import Cooldown
from behavior.events import EventType
from behavior.scheduler import ContextEventScheduler
from dialogue.local_rules import DialogueManager
from dialogue.personality import normalize_personality
from pet.animation import AnimationController
from pet.interaction import FoodPanel, InteractionController
from pet.movement import MovementController
from pet.renderer import Bubble, PetRenderer
from pet.state import PetStateStore
from settings.config import ConfigManager


BUBBLE_HEIGHT = 56
MARGIN = 4
BASE_SPRITE_HEIGHT = 340
SIZE_LEVELS = {"小": 0.55, "中": 0.70, "大": 0.90}
TICK_MS = 20


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
        self.sprites = self._load_sprites()
        self._resize_window()

        self.movement = MovementController(config.get("mode", "wander"))
        self.animation = AnimationController()
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
        self._create_tray()

        self._create_awareness()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

        self._restore_position()
        self.show()
        self.snap_into_screen()
        self._sync_awareness_timer()

    # ----- window and rendering -------------------------------------------------

    def _load_sprites(self) -> dict[tuple[str, int, int], QPixmap]:
        sprites: dict[tuple[str, int, int], QPixmap] = {}
        for multiplier in SIZE_LEVELS.values():
            height = self._height_for_size(multiplier)
            for name in ("正面", "侧面", "背面"):
                sized_path = self.paths.sprite_dir / f"{name}_{height}.png"
                source_path = self.paths.sprite_dir / f"{name}.png"
                path = sized_path if sized_path.exists() else source_path
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    raise RuntimeError(f"无法加载角色资源：{path}")
                sprites[(name, height, 1)] = pixmap
                sprites[(name, height, -1)] = pixmap
        return sprites

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
        widths = [
            pixmap.width()
            for (_, height, _), pixmap in self.sprites.items()
            if height == self.current_height
        ]
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
            sprites=self.sprites,
            current_key=self._current_sprite_key(),
            animation=self.animation,
            walking=self.movement.is_walking and not self.interaction.dragging,
            bubble=self.bubble,
        )

    def _current_sprite_key(self) -> tuple[str, int, int]:
        name = {
            "left": "侧面",
            "right": "侧面",
            "up": "背面",
            "down": "正面",
        }[self.movement.direction]
        facing = self.movement.facing if self.movement.direction in {"left", "right"} else 1
        return name, self.current_height, facing

    def _set_direction(self, direction: str, facing: int | None = None) -> None:
        previous_key = self._current_sprite_key()
        if self.movement.set_direction(direction, facing):
            self.animation.start_crossfade(previous_key)

    # ----- main animation loop --------------------------------------------------

    def tick(self) -> None:
        now = time.monotonic()
        delta_seconds = min(0.10, max(0.001, now - self._last_tick_at))
        self._last_tick_at = now
        self.animation.tick(delta_seconds)
        walking = False
        if not self.interaction.dragging:
            walking = self.movement.update(
                self,
                now=now,
                delta_seconds=delta_seconds,
                set_direction=self._set_direction,
            )
        if walking and self.rng.random() < 0.002:
            self.animation.start_jump(0.48)
        if not walking and not self.interaction.dragging:
            self._maybe_idle_action(now)
        if now - self._last_state_update >= 5.0:
            self.pet_state.advance(now - self._last_state_update)
            self._last_state_update = now
        self.update()

    def _maybe_idle_action(self, now: float) -> None:
        if self.rng.random() >= 0.0015:
            return
        pick = self.rng.random()
        if pick < 0.34:
            self.animation.start_jump()
        elif pick < 0.62:
            self.animation.start_idle_action("sway")
        elif pick < 0.84:
            self.animation.start_idle_action("stretch")
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
        self.bubble = Bubble(
            text=f"（{text}）" if inner else text,
            until=time.monotonic() + 2.8,
            inner=inner,
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
            self.say(self.dialogue.pick_interaction("head", personality=personality))
            self.animation.start_idle_action("sway")
        else:
            self.pet_state.tap()
            if self.rng.random() < 0.72:
                self.animation.start_jump()
            self.say(self.dialogue.pick_interaction("tap", personality=personality))

    def on_food(self, _food: str) -> None:
        self.food_panel.hide()
        self.pet_state.feed()
        self.animation.start_eating()
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
        if enabled:
            self.say("本地环境感知已开启。")
        else:
            self.say("本地环境感知已暂停。")

    def _set_awareness_flag(self, key: str, enabled: bool) -> None:
        self.config.set_nested("awareness", key, bool(enabled))

    # ----- menus, tray, and persistence ----------------------------------------

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        mode_menu = menu.addMenu("模式")
        for label, key in (
            ("自由散步", "wander"),
            ("跟随鼠标", "follow"),
            ("原地待着", "still"),
        ):
            action = mode_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.movement.mode == key)
            action.triggered.connect(lambda _, value=key: self.set_mode(value))

        size_menu = menu.addMenu("大小")
        for label, multiplier in SIZE_LEVELS.items():
            action = size_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(abs(self.current_height - self._height_for_size(multiplier)) < 2)
            action.triggered.connect(lambda _, value=multiplier: self.set_size(value))

        menu.addAction(
            "喂食",
            lambda: self.food_panel.popup_at(
                self.x() + self.width() / 2,
                self.y() + BUBBLE_HEIGHT,
            ),
        )
        menu.addAction(
            "说句话",
            lambda: self.say(self.dialogue.pick_daily(personality=self._personality())),
        )

        awareness_menu = menu.addMenu("环境感知")
        awareness = self.config.section("awareness")
        enabled_action = awareness_menu.addAction("启用本地环境感知")
        enabled_action.setCheckable(True)
        enabled_action.setChecked(bool(awareness.get("enabled", True)))
        enabled_action.triggered.connect(self.set_awareness_enabled)
        title_action = awareness_menu.addAction("读取窗口标题")
        title_action.setCheckable(True)
        title_action.setChecked(bool(awareness.get("read_window_title", True)))
        title_action.triggered.connect(
            lambda on: self._set_awareness_flag("read_window_title", on)
        )
        idle_action = awareness_menu.addAction("检测用户空闲")
        idle_action.setCheckable(True)
        idle_action.setChecked(bool(awareness.get("idle_detection", True)))
        idle_action.triggered.connect(
            lambda on: self._set_awareness_flag("idle_detection", on)
        )
        fullscreen_action = awareness_menu.addAction("全屏时自动隐藏")
        fullscreen_action.setCheckable(True)
        fullscreen_action.setChecked(bool(awareness.get("hide_on_fullscreen", True)))
        fullscreen_action.triggered.connect(
            lambda on: self._set_awareness_flag("hide_on_fullscreen", on)
        )
        awareness_menu.addSeparator()
        awareness_menu.addAction("查看隐私规则", self._show_privacy_notice)

        menu.addSeparator()
        menu.addAction("隐藏到托盘", self.hide)
        menu.addAction("回到屏幕内", self.snap_into_screen)
        passthrough_action = menu.addAction("鼠标穿透（点不到它）")
        passthrough_action.setCheckable(True)
        passthrough_action.setChecked(bool(self.config.get("passthrough", False)))
        passthrough_action.triggered.connect(self.set_passthrough)
        topmost_action = menu.addAction("窗口置顶")
        topmost_action.setCheckable(True)
        topmost_action.setChecked(bool(self.config.get("topmost", True)))
        topmost_action.triggered.connect(self.set_topmost)
        autostart_action = menu.addAction("开机自启")
        autostart_action.setCheckable(True)
        autostart_action.setChecked(bool(self.config.get("autostart", False)))
        autostart_action.triggered.connect(self.set_autostart)
        menu.addSeparator()
        menu.addAction("退出", self.quit_app)
        menu.exec(event.globalPos())

    def _create_tray(self) -> None:
        icon = QIcon(str(self.paths.sprite_dir / "icon.png"))
        self.tray = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()
        tray_menu.addAction("显示/隐藏", self.toggle_visible)
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

    def set_size(self, multiplier: float) -> None:
        multiplier = self._normalized_size(multiplier)
        self.current_height = self._height_for_size(multiplier)
        self.config.set("size", multiplier)
        self.animation.crossfade = 0.0
        self.animation.previous_sprite_key = None
        self._resize_window()
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
            if enabled:
                self.say("我隐身了！右键托盘图标可以解除。")
        except OSError as error:
            QMessageBox.warning(self, "鼠标穿透", f"设置失败：{error}")

    def set_topmost(self, enabled: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(enabled))
        self.config.set("topmost", bool(enabled))
        self.show()

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
        except (OSError, subprocess.CalledProcessError) as error:
            QMessageBox.warning(self, "开机自启", f"设置失败：{error}")

    def toggle_visible(self) -> None:
        if self.isVisible():
            self._hidden_by_fullscreen = False
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
