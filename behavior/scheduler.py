from __future__ import annotations

import time
from datetime import datetime

from awareness.context_snapshot import ContextSnapshot
from behavior.events import ContextEvent, EventType


class ContextEventScheduler:
    """Turns slow context snapshots into debounced, meaningful events."""

    def __init__(
        self,
        *,
        min_dwell_seconds: float = 15.0,
        idle_after_seconds: float = 300.0,
        late_night_hour: int = 23,
    ) -> None:
        self.min_dwell_seconds = min_dwell_seconds
        self.idle_after_seconds = idle_after_seconds
        self.late_night_hour = late_night_hour
        self._identity: tuple[str, str, int] | None = None
        self._entered_at: float | None = None
        self._stay_announced = False
        self._idle_announced = False
        self._fullscreen = False
        self._late_night_date: str | None = None

    def observe(
        self,
        snapshot: ContextSnapshot,
        *,
        now: float | None = None,
        wall_clock: datetime | None = None,
    ) -> list[ContextEvent]:
        now = time.monotonic() if now is None else now
        wall_clock = datetime.now() if wall_clock is None else wall_clock
        events: list[ContextEvent] = []
        identity = snapshot.identity

        if identity != self._identity:
            self._identity = identity
            self._entered_at = now
            self._stay_announced = False
            events.append(ContextEvent(EventType.APP_ENTER, snapshot, now))
        elif (
            not self._stay_announced
            and self._entered_at is not None
            and now - self._entered_at >= self.min_dwell_seconds
        ):
            self._stay_announced = True
            events.append(ContextEvent(EventType.APP_STAY, snapshot, now))

        is_idle = snapshot.idle_seconds >= self.idle_after_seconds
        if is_idle and not self._idle_announced:
            self._idle_announced = True
            events.append(ContextEvent(EventType.USER_IDLE, snapshot, now))
        elif not is_idle and self._idle_announced:
            self._idle_announced = False
            events.append(ContextEvent(EventType.USER_RETURN, snapshot, now))

        if snapshot.is_fullscreen != self._fullscreen:
            self._fullscreen = snapshot.is_fullscreen
            event_type = EventType.FULLSCREEN_ENTER if self._fullscreen else EventType.FULLSCREEN_EXIT
            events.append(ContextEvent(event_type, snapshot, now))

        day_key = wall_clock.date().isoformat()
        if (
            wall_clock.hour >= self.late_night_hour
            and not is_idle
            and self._late_night_date != day_key
        ):
            self._late_night_date = day_key
            events.append(ContextEvent(EventType.LATE_NIGHT, snapshot, now))
        return events
