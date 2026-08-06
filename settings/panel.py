"""A compact, pet-adjacent control surface with progressive disclosure."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class PetControlPanel(QWidget):
    """Quick interaction first; secondary settings are explicitly revealed."""

    def __init__(
        self,
        *,
        on_mode: Callable[[str], None],
        on_size: Callable[[float], None],
        on_feed: Callable[[], None],
        on_say: Callable[[], None],
        on_snap: Callable[[], None],
        on_awareness: Callable[[bool], None],
        on_read_window_title: Callable[[bool], None],
        on_idle_detection: Callable[[bool], None],
        on_topmost: Callable[[bool], None],
        on_fullscreen_hide: Callable[[bool], None],
        on_passthrough: Callable[[bool], None],
        on_autostart: Callable[[bool], None],
        on_action: Callable[[str], None],
        on_hide: Callable[[], None],
        on_privacy: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("petControlPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(258)
        self._mode_buttons: dict[str, QToolButton] = {}
        self._size_buttons: dict[float, QToolButton] = {}
        self._mode_group = QButtonGroup(self)
        self._size_group = QButtonGroup(self)
        self._expanded = False
        self._pet_rect: QRect | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 8)
        self._root_layout = root
        surface = QFrame()
        surface.setObjectName("controlSurface")
        shadow = QGraphicsDropShadowEffect(surface)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(3, 19, 37, 130))
        surface.setGraphicsEffect(shadow)
        root.addWidget(surface)

        layout = QVBoxLayout(surface)
        layout.setContentsMargins(14, 13, 14, 13)
        layout.setSpacing(9)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("大肥鱼")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        self.state_label = QLabel("待机")
        self.state_label.setObjectName("stateLabel")
        header.addWidget(self.state_label)
        header.addStretch(1)
        close = QToolButton()
        close.setObjectName("closeButton")
        close.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        close.setToolTip("关闭")
        close.setAccessibleName("关闭")
        close.clicked.connect(self.hide)
        header.addWidget(close)
        layout.addLayout(header)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(5)
        for label, callback in (
            ("投喂", on_feed),
            ("说话", on_say),
            ("开心", lambda: on_action("HAPPY")),
            ("休息", lambda: on_action("SLEEPING")),
        ):
            button = self._quick_button(label)
            button.clicked.connect(callback)
            quick_row.addWidget(button)
        layout.addLayout(quick_row)

        layout.addWidget(self._divider())
        mode_label = QLabel("移动")
        mode_label.setObjectName("compactLabel")
        layout.addWidget(mode_label)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(5)
        for label, value in (("散步", "wander"), ("跟随", "follow"), ("静止", "still")):
            button = self._choice_button(label)
            button.clicked.connect(lambda _checked=False, key=value: on_mode(key))
            self._mode_group.addButton(button)
            self._mode_buttons[value] = button
            mode_row.addWidget(button)
        layout.addLayout(mode_row)

        footer = QHBoxLayout()
        footer.setSpacing(5)
        self.more_button = QToolButton()
        self.more_button.setObjectName("moreButton")
        self.more_button.setText("更多设置")
        self.more_button.clicked.connect(self._toggle_advanced)
        footer.addWidget(self.more_button, 1)
        hide = QToolButton()
        hide.setObjectName("moreButton")
        hide.setText("隐藏")
        hide.clicked.connect(on_hide)
        footer.addWidget(hide)
        layout.addLayout(footer)

        self._advanced = QWidget()
        advanced_layout = QVBoxLayout(self._advanced)
        advanced_layout.setContentsMargins(0, 1, 0, 0)
        advanced_layout.setSpacing(8)
        advanced_layout.addWidget(self._divider())

        size_label = QLabel("大小")
        size_label.setObjectName("compactLabel")
        advanced_layout.addWidget(size_label)
        size_row = QHBoxLayout()
        size_row.setSpacing(5)
        for label, value in (("小", 0.55), ("中", 0.70), ("大", 0.90)):
            button = self._choice_button(label)
            button.clicked.connect(lambda _checked=False, size=value: on_size(size))
            self._size_group.addButton(button)
            self._size_buttons[value] = button
            size_row.addWidget(button)
        advanced_layout.addLayout(size_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(5)
        for label, action in (("发呆", "THINKING"), ("扫地", "SWEEPING")):
            button = self._quick_button(label)
            button.clicked.connect(lambda _checked=False, value=action: on_action(value))
            action_row.addWidget(button)
        action_row.addStretch(1)
        advanced_layout.addLayout(action_row)

        self.awareness = self._toggle("本地感知", on_awareness)
        self.topmost = self._toggle("窗口置顶", on_topmost)
        self.read_window_title = self._toggle("读取标题", on_read_window_title)
        self.fullscreen_hide = self._toggle("全屏隐藏", on_fullscreen_hide)
        self.idle_detection = self._toggle("检测空闲", on_idle_detection)
        self.passthrough = self._toggle("鼠标穿透", on_passthrough)
        self.autostart = self._toggle("开机自启", on_autostart)
        toggle_grid = QGridLayout()
        toggle_grid.setHorizontalSpacing(10)
        toggle_grid.setVerticalSpacing(2)
        for index, toggle in enumerate(
            (
                self.awareness,
                self.topmost,
                self.read_window_title,
                self.fullscreen_hide,
                self.idle_detection,
                self.passthrough,
                self.autostart,
            )
        ):
            toggle_grid.addWidget(toggle, index // 2, index % 2)
        advanced_layout.addLayout(toggle_grid)

        tools = QHBoxLayout()
        tools.setSpacing(5)
        for label, callback, object_name in (
            ("回到屏幕内", on_snap, "utilityButton"),
            ("隐私", on_privacy, "utilityButton"),
            ("退出", on_quit, "dangerButton"),
        ):
            button = QPushButton(label)
            button.setObjectName(object_name)
            button.clicked.connect(callback)
            tools.addWidget(button)
        advanced_layout.addLayout(tools)
        self._advanced.setVisible(False)
        layout.addWidget(self._advanced)

        self.setStyleSheet(
            "#controlSurface{background:#0b2b45;border-radius:14px;}"
            "#panelTitle{color:#f6fbff;font-size:16px;font-weight:700;}"
            "#stateLabel{padding:2px 7px;background:#174767;border-radius:8px;color:#c3e5f7;font-size:10px;font-weight:600;}"
            "QLabel#compactLabel{color:#a8cde4;font-size:10px;font-weight:600;}"
            "QFrame#divider{background:rgba(184,220,240,38);min-height:1px;max-height:1px;}"
            "QToolButton#quickButton{min-height:31px;padding:0 7px;background:#16415f;border:none;border-radius:9px;"
            "color:#e4f3fb;font-size:11px;font-weight:600;}"
            "QToolButton#quickButton:hover{background:#215779;color:#ffffff;}"
            "QToolButton#choiceButton{min-height:29px;padding:0 8px;background:#123750;border:none;border-radius:8px;"
            "color:#cfe8f6;font-size:11px;font-weight:600;}"
            "QToolButton#choiceButton:hover{background:#1b5275;}"
            "QToolButton#choiceButton:checked{background:#56b9e3;color:#06243a;}"
            "QToolButton#moreButton,QToolButton#closeButton{min-height:28px;padding:0 8px;background:transparent;border:none;"
            "border-radius:8px;color:#a9cfe5;font-size:11px;font-weight:600;}"
            "QToolButton#moreButton:hover,QToolButton#closeButton:hover{background:#173f5d;color:#f7fcff;}"
            "QCheckBox{min-height:20px;color:#d9edf8;font-size:11px;spacing:6px;}"
            "QCheckBox::indicator{width:26px;height:14px;border-radius:7px;background:#224b67;}"
            "QCheckBox::indicator:checked{background:#55b9e3;}"
            "QPushButton#utilityButton,QPushButton#dangerButton{min-height:29px;padding:0 8px;border:none;border-radius:8px;"
            "font-size:11px;font-weight:600;}"
            "QPushButton#utilityButton{background:#dff1fb;color:#123750;}"
            "QPushButton#utilityButton:hover{background:#ffffff;}"
            "QPushButton#dangerButton{background:#874457;color:#fff5f6;}"
            "QPushButton#dangerButton:hover{background:#aa566c;}"
        )

    @staticmethod
    def _divider() -> QFrame:
        divider = QFrame()
        divider.setObjectName("divider")
        return divider

    @staticmethod
    def _choice_button(text: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("choiceButton")
        button.setText(text)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        return button

    @staticmethod
    def _quick_button(text: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("quickButton")
        button.setText(text)
        return button

    @staticmethod
    def _toggle(text: str, callback: Callable[[bool], None]) -> QCheckBox:
        checkbox = QCheckBox(text)
        checkbox.clicked.connect(callback)
        return checkbox

    def _toggle_advanced(self) -> None:
        self._expanded = not self._expanded
        self._advanced.setVisible(self._expanded)
        self.more_button.setText("收起设置" if self._expanded else "更多设置")
        # Hiding a child queues a layout recalculation.  Resize on the next Qt
        # turn so the compact hint is already current instead of retaining the
        # expanded tool window's old height.
        QTimer.singleShot(0, self._fit_to_content)

    def _fit_to_content(self) -> None:
        # A top-level transparent Tool window does not reliably shrink from
        # ``adjustSize`` after a child is hidden on Windows.  Re-activate the
        # layout and apply its fresh height explicitly, otherwise the old empty
        # glass area remains below the compact panel.
        self._root_layout.invalidate()
        self._root_layout.activate()
        target_height = self.sizeHint().height()
        # Qt may still hold the expanded layout's minimum height until the next
        # event cycle, so release that stale bound before asking the window to
        # shrink to its current size hint.
        self.setMinimumHeight(0)
        self.resize(self.width(), target_height)
        if self._pet_rect is not None:
            self._move_near_pet(self._pet_rect)

    def sync(
        self,
        *,
        mode: str,
        size: float,
        awareness: bool,
        read_window_title: bool,
        idle_detection: bool,
        topmost: bool,
        fullscreen_hide: bool,
        passthrough: bool,
        autostart: bool,
        state_name: str,
    ) -> None:
        if mode in self._mode_buttons:
            self._mode_buttons[mode].setChecked(True)
        closest_size = min(self._size_buttons, key=lambda value: abs(value - size))
        self._size_buttons[closest_size].setChecked(True)
        self.awareness.setChecked(awareness)
        self.read_window_title.setChecked(read_window_title)
        self.idle_detection.setChecked(idle_detection)
        self.topmost.setChecked(topmost)
        self.fullscreen_hide.setChecked(fullscreen_hide)
        self.passthrough.setChecked(passthrough)
        self.autostart.setChecked(autostart)
        self.state_label.setText(state_name)

    def popup_near_pet(self, pet_rect: QRect) -> None:
        self._pet_rect = QRect(pet_rect)
        self.adjustSize()
        self._move_near_pet(self._pet_rect)
        self.show()
        self.raise_()

    def popup_at(self, point: QPoint) -> None:
        """Fallback used from the tray when there is no visible pet anchor."""

        self._pet_rect = None
        self.adjustSize()
        screen = QApplication.screenAt(point) or QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(self._clamp(QPoint(point.x() + 12, point.y() + 12), area))
        else:
            self.move(point + QPoint(12, 12))
        self.show()
        self.raise_()

    def _move_near_pet(self, pet_rect: QRect) -> None:
        screen = QApplication.screenAt(pet_rect.center()) or QApplication.primaryScreen()
        if screen is None:
            self.move(pet_rect.topRight() + QPoint(14, 8))
            return
        area = screen.availableGeometry()
        gap = 14
        aligned_y = pet_rect.top() + max(0, min(24, pet_rect.height() - self.height()))
        centered_x = pet_rect.center().x() - self.width() // 2
        candidates = (
            QPoint(pet_rect.right() + gap, aligned_y),
            QPoint(pet_rect.left() - self.width() - gap, aligned_y),
            QPoint(centered_x, pet_rect.top() - self.height() - gap),
            QPoint(centered_x, pet_rect.bottom() + gap),
        )
        for candidate in candidates:
            rect = QRect(candidate, self.size())
            if area.contains(rect):
                self.move(candidate)
                return

        # On a very small screen, pick the clamped candidate that hides the
        # least of the pet rather than anchoring blindly over its centre.
        def overlap(candidate: QPoint) -> int:
            rect = QRect(self._clamp(candidate, area), self.size())
            intersection = rect.intersected(pet_rect)
            return intersection.width() * intersection.height()

        self.move(min(candidates, key=overlap))
        self.move(self._clamp(self.pos(), area))

    def _clamp(self, point: QPoint, area: QRect) -> QPoint:
        return QPoint(
            min(max(area.left(), point.x()), area.right() - self.width() + 1),
            min(max(area.top(), point.y()), area.bottom() - self.height() + 1),
        )
