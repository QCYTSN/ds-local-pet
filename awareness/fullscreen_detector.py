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

    def is_fullscreen(self, handle: int) -> bool:
        if not self._available or not handle:
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
