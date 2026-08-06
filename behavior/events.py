from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from awareness.context_snapshot import ContextSnapshot


class EventType(str, Enum):
    APP_ENTER = "APP_ENTER"
    APP_STAY = "APP_STAY"
    USER_IDLE = "USER_IDLE"
    USER_RETURN = "USER_RETURN"
    FULLSCREEN_ENTER = "FULLSCREEN_ENTER"
    FULLSCREEN_EXIT = "FULLSCREEN_EXIT"
    LATE_NIGHT = "LATE_NIGHT"


@dataclass(frozen=True, slots=True)
class ContextEvent:
    type: EventType
    snapshot: ContextSnapshot
    occurred_at: float
