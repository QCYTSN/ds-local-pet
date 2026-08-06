from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes


class _LastInputInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD),
    ]


class IdleDetector:
    """Return seconds since the user's last keyboard or mouse input."""

    def __init__(self) -> None:
        self._available = sys.platform == "win32"
        if self._available:
            self._user32 = ctypes.WinDLL("user32", use_last_error=True)
            self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._user32.GetLastInputInfo.argtypes = [ctypes.POINTER(_LastInputInfo)]
            self._user32.GetLastInputInfo.restype = wintypes.BOOL
            self._kernel32.GetTickCount.restype = wintypes.DWORD

    def seconds(self) -> float:
        if not self._available:
            return 0.0
        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(_LastInputInfo)
        if not self._user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        current_tick = self._kernel32.GetTickCount()
        elapsed_ms = (int(current_tick) - int(info.dwTime)) & 0xFFFFFFFF
        return elapsed_ms / 1000.0
