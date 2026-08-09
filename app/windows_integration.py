"""Tiny Windows-only integration helpers."""

from __future__ import annotations

import ctypes
import sys


def register_application_restart() -> bool:
    """Allow Restart Manager to reopen the pet after an installer update."""
    if sys.platform != "win32":
        return False
    try:
        # Do not request automatic recovery after crashes or hangs.  Updates
        # remain restartable, which is exactly what Inno Setup needs.
        result = ctypes.windll.kernel32.RegisterApplicationRestart(None, 0x1 | 0x2)
    except (AttributeError, OSError):
        return False
    return int(result) == 0
