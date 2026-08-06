from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    timestamp: float
    process_name: str
    window_title: str
    pid: int
    idle_seconds: float
    is_fullscreen: bool
    category: str
    window_handle: int = 0
    is_private: bool = False

    @property
    def identity(self) -> tuple[str, str, int]:
        """A short-lived in-memory identity used only for dwell detection."""
        title = "" if self.is_private else self.window_title.casefold().strip()
        return (self.process_name.casefold().strip(), title, self.pid)
