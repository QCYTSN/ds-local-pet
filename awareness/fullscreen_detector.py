from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _Rect),
        ("rcWork", _Rect),
        ("dwFlags", wintypes.DWORD),
    ]


class FullscreenDetector:
    """Detect a foreground window covering its current monitor."""

    _MONITOR_DEFAULTTONEAREST = 2
    _GWL_STYLE = -16
    _WS_CAPTION = 0x00C00000
    _WS_THICKFRAME = 0x00040000

    def __init__(self, tolerance: int = 2) -> None:
        self.tolerance = tolerance
        self._available = sys.platform == "win32"
        if self._available:
            self._user32 = ctypes.WinDLL("user32", use_last_error=True)
            self._user32.GetWindowRect.argtypes = [
                wintypes.HWND,
                ctypes.POINTER(_Rect),
            ]
            self._user32.GetWindowRect.restype = wintypes.BOOL
            self._user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            self._user32.MonitorFromWindow.restype = wintypes.HANDLE
            self._user32.GetMonitorInfoW.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(_MonitorInfo),
            ]
            self._user32.GetMonitorInfoW.restype = wintypes.BOOL
            self._get_window_style = getattr(
                self._user32,
                "GetWindowLongPtrW",
                self._user32.GetWindowLongW,
            )
            self._get_window_style.argtypes = [wintypes.HWND, ctypes.c_int]
            self._get_window_style.restype = ctypes.c_ssize_t

    def is_fullscreen(self, handle: int) -> bool:
        if not self._available or not handle:
            return False
        style = int(self._get_window_style(handle, self._GWL_STYLE))
        # A standard framed/maximized window can cover monitor bounds due to
        # invisible resize borders, but it is not a fullscreen app or game.
        if style & (self._WS_CAPTION | self._WS_THICKFRAME):
            return False
        rect = _Rect()
        if not self._user32.GetWindowRect(handle, ctypes.byref(rect)):
            return False
        monitor = self._user32.MonitorFromWindow(handle, self._MONITOR_DEFAULTTONEAREST)
        if not monitor:
            return False
        info = _MonitorInfo()
        info.cbSize = ctypes.sizeof(_MonitorInfo)
        if not self._user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return False
        screen = info.rcMonitor
        margin = self.tolerance
        return (
            rect.left <= screen.left + margin
            and rect.top <= screen.top + margin
            and rect.right >= screen.right - margin
            and rect.bottom >= screen.bottom - margin
        )
