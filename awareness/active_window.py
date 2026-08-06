from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass

try:
    import psutil
except ImportError:  # pragma: no cover - dependency is installed in production
    psutil = None


@dataclass(frozen=True, slots=True)
class ActiveWindow:
    handle: int
    pid: int
    title: str
    process_name: str


class ActiveWindowReader:
    """Read foreground-window metadata through Win32 without a polling service."""

    def __init__(self) -> None:
        self._available = sys.platform == "win32"
        if self._available:
            self._user32 = ctypes.WinDLL("user32", use_last_error=True)
            self._user32.GetForegroundWindow.restype = wintypes.HWND
            self._user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
            self._user32.GetWindowTextLengthW.restype = ctypes.c_int
            self._user32.GetWindowTextW.argtypes = [
                wintypes.HWND,
                wintypes.LPWSTR,
                ctypes.c_int,
            ]
            self._user32.GetWindowThreadProcessId.argtypes = [
                wintypes.HWND,
                ctypes.POINTER(wintypes.DWORD),
            ]

    def read(self) -> ActiveWindow | None:
        if not self._available:
            return None
        handle = self._user32.GetForegroundWindow()
        if not handle:
            return None
        handle_value = ctypes.cast(handle, ctypes.c_void_p).value
        if not handle_value:
            return None
        length = self._user32.GetWindowTextLengthW(handle)
        buffer = ctypes.create_unicode_buffer(max(1, length + 1))
        self._user32.GetWindowTextW(handle, buffer, len(buffer))
        pid = wintypes.DWORD()
        self._user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        process_name = self._process_name(pid.value)
        return ActiveWindow(
            handle=int(handle_value),
            pid=int(pid.value),
            title=buffer.value.strip(),
            process_name=process_name,
        )

    @staticmethod
    def _process_name(pid: int) -> str:
        if not pid or psutil is None:
            return ""
        try:
            return psutil.Process(pid).name()
        except (psutil.Error, OSError):
            return ""
