"""Window-top surfaces for landing, walking and attachment on Windows."""

from __future__ import annotations

import ctypes
import sys
import time
from dataclasses import dataclass
from ctypes import wintypes
from typing import Protocol

from pet.physics import PhysicsPlatform


@dataclass(frozen=True, slots=True)
class SurfaceRect:
    handle: int
    left: float
    top: float
    right: float
    bottom: float
    observed_at: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @property
    def surface_id(self) -> str:
        return f"window:{self.handle}"


@dataclass(frozen=True, slots=True)
class AttachmentUpdate:
    x: float
    y: float
    lost: bool = False


class WindowRectReader(Protocol):
    def read(self, handle: int) -> tuple[int, int, int, int] | None: ...

    def foreground_handle(self) -> int: ...


class Win32WindowRectReader:
    """Read visible extended window bounds without inspecting window content."""

    DWMWA_EXTENDED_FRAME_BOUNDS = 9

    def __init__(self) -> None:
        self.available = sys.platform == "win32"
        if not self.available:
            return
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsIconic.argtypes = [wintypes.HWND]
        self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self._physical_to_logical = getattr(
            self.user32,
            "PhysicalToLogicalPointForPerMonitorDPI",
            None,
        )
        if self._physical_to_logical is not None:
            self._physical_to_logical.argtypes = [
                wintypes.HWND,
                ctypes.POINTER(wintypes.POINT),
            ]
            self._physical_to_logical.restype = wintypes.BOOL
        self._get_dpi_for_window = getattr(self.user32, "GetDpiForWindow", None)
        if self._get_dpi_for_window is not None:
            self._get_dpi_for_window.argtypes = [wintypes.HWND]
            self._get_dpi_for_window.restype = wintypes.UINT
        try:
            self.dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
            self.dwmapi.DwmGetWindowAttribute.argtypes = [
                wintypes.HWND,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]
        except OSError:
            self.dwmapi = None

    def read(self, handle: int) -> tuple[int, int, int, int] | None:
        if not self.available or not handle:
            return None
        hwnd = wintypes.HWND(int(handle))
        if not self.user32.IsWindow(hwnd):
            return None
        if not self.user32.IsWindowVisible(hwnd) or self.user32.IsIconic(hwnd):
            return None
        rect = wintypes.RECT()
        if self.dwmapi is not None:
            result = self.dwmapi.DwmGetWindowAttribute(
                hwnd,
                self.DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rect),
                ctypes.sizeof(rect),
            )
            if result != 0:
                rect = wintypes.RECT()
        if rect.right <= rect.left or rect.bottom <= rect.top:
            if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return None
        return self._logical_rect(hwnd, rect)

    def foreground_handle(self) -> int:
        if not self.available:
            return 0
        handle = self.user32.GetForegroundWindow()
        return int(ctypes.cast(handle, ctypes.c_void_p).value or 0)

    def _logical_rect(self, hwnd, rect: wintypes.RECT) -> tuple[int, int, int, int]:
        """Convert Win32 physical pixels into the device-independent space Qt uses."""

        # DWM extended bounds are always physical pixels.  Qt's QWidget and
        # QScreen APIs use device-independent coordinates, so the window DPI
        # is the reliable conversion for the per-monitor-aware Qt process.
        if self._get_dpi_for_window is not None:
            dpi = int(self._get_dpi_for_window(hwnd) or 96)
            scale = max(1.0, dpi / 96.0)
            return tuple(round(value / scale) for value in (rect.left, rect.top, rect.right, rect.bottom))
        if self._physical_to_logical is not None:
            top_left = wintypes.POINT(int(rect.left), int(rect.top))
            bottom_right = wintypes.POINT(int(rect.right), int(rect.bottom))
            if self._physical_to_logical(hwnd, ctypes.byref(top_left)) and self._physical_to_logical(
                hwnd, ctypes.byref(bottom_right)
            ):
                return top_left.x, top_left.y, bottom_right.x, bottom_right.y
        return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)


class DesktopSurfaceTracker:
    """Keep only geometry needed to make a foreground window a pet surface."""

    def __init__(
        self,
        reader: WindowRectReader | None = None,
        *,
        enabled: bool = True,
    ) -> None:
        self.reader = reader or Win32WindowRectReader()
        self.enabled = bool(enabled)
        self._surfaces: dict[int, SurfaceRect] = {}
        self._candidate_handle: int | None = None
        self._attached_handle: int | None = None
        self._relative_center = 0.5
        self._next_attachment_refresh = 0.0

    @property
    def attached(self) -> bool:
        return self.enabled and self._attached_handle is not None

    def set_enabled(self, enabled: bool) -> bool:
        was_attached = self.attached
        self.enabled = bool(enabled)
        if not self.enabled:
            self.detach()
        return was_attached and not self.enabled

    def observe_window(self, handle: int, *, now: float | None = None) -> bool:
        if not self.enabled or not handle:
            return False
        now = time.monotonic() if now is None else now
        surface = self._read_surface(handle, now)
        if surface is None:
            return False
        self._surfaces[handle] = surface
        self._candidate_handle = handle
        return True

    def observe_foreground(
        self,
        *,
        ignored_handles: set[int] | None = None,
        now: float | None = None,
    ) -> bool:
        foreground = getattr(self.reader, "foreground_handle", None)
        handle = int(foreground()) if callable(foreground) else 0
        if not handle or handle in (ignored_handles or set()):
            return False
        return self.observe_window(handle, now=now)

    def physics_platforms(
        self,
        *,
        work_area_top: float,
        widget_height: float,
        now: float | None = None,
    ) -> tuple[PhysicsPlatform, ...]:
        if not self.enabled:
            return ()
        now = time.monotonic() if now is None else now
        handles = {self._candidate_handle, self._attached_handle}
        platforms: list[PhysicsPlatform] = []
        for handle in handles:
            if handle is None:
                continue
            surface = self._surfaces.get(handle)
            if surface is None:
                continue
            if handle != self._attached_handle and now - surface.observed_at > 30.0:
                continue
            if surface.width < 180.0 or surface.height < 120.0:
                continue
            if surface.top - widget_height < work_area_top:
                continue
            platforms.append(
                PhysicsPlatform(
                    left=surface.left + 8.0,
                    right=surface.right - 8.0,
                    top=surface.top,
                    surface_id=surface.surface_id,
                )
            )
        return tuple(platforms)

    def attach(
        self,
        surface_id: str | None,
        *,
        widget_x: float,
        widget_width: float,
    ) -> bool:
        handle = self._handle_from_id(surface_id)
        surface = self._surfaces.get(handle) if handle is not None else None
        if not self.enabled or surface is None or surface.width <= 0.0:
            self.detach()
            return False
        center = widget_x + widget_width / 2.0
        self._relative_center = max(0.0, min(1.0, (center - surface.left) / surface.width))
        self._attached_handle = handle
        self._next_attachment_refresh = 0.0
        return True

    def detach(self) -> None:
        self._attached_handle = None
        self._relative_center = 0.5
        self._next_attachment_refresh = 0.0

    def follow_attachment(
        self,
        *,
        now: float,
        widget_x: float,
        widget_width: float,
        widget_height: float,
    ) -> AttachmentUpdate | None:
        if not self.attached or self._attached_handle is None:
            return None
        if now < self._next_attachment_refresh:
            return None
        self._next_attachment_refresh = now + 0.08
        surface = self._read_surface(self._attached_handle, now)
        if surface is None:
            self.detach()
            return AttachmentUpdate(widget_x, 0.0, lost=True)
        self._surfaces[surface.handle] = surface
        target_center = surface.left + surface.width * self._relative_center
        target_x = target_center - widget_width / 2.0
        lower, upper = self._movement_bounds_for(surface, widget_width)
        target_x = max(lower, min(upper, target_x))
        return AttachmentUpdate(target_x, surface.top - widget_height)

    def record_pet_position(self, *, widget_x: float, widget_width: float) -> None:
        if not self.attached or self._attached_handle is None:
            return
        surface = self._surfaces.get(self._attached_handle)
        if surface is None or surface.width <= 0.0:
            return
        center = widget_x + widget_width / 2.0
        self._relative_center = max(0.0, min(1.0, (center - surface.left) / surface.width))

    def movement_bounds(self, *, widget_width: float) -> tuple[float, float] | None:
        if not self.attached or self._attached_handle is None:
            return None
        surface = self._surfaces.get(self._attached_handle)
        if surface is None:
            return None
        return self._movement_bounds_for(surface, widget_width)

    @staticmethod
    def _movement_bounds_for(surface: SurfaceRect, widget_width: float) -> tuple[float, float]:
        foot_margin = min(38.0, max(18.0, surface.width * 0.055))
        lower = surface.left + foot_margin - widget_width / 2.0
        upper = surface.right - foot_margin - widget_width / 2.0
        return lower, max(lower, upper)

    def _read_surface(self, handle: int, now: float) -> SurfaceRect | None:
        rect = self.reader.read(handle)
        if rect is None:
            return None
        left, top, right, bottom = rect
        surface = SurfaceRect(handle, float(left), float(top), float(right), float(bottom), now)
        if surface.width < 180.0 or surface.height < 120.0:
            return None
        return surface

    @staticmethod
    def _handle_from_id(surface_id: str | None) -> int | None:
        if not surface_id or not surface_id.startswith("window:"):
            return None
        try:
            return int(surface_id.partition(":")[2])
        except ValueError:
            return None
