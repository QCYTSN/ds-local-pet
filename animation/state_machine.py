"""Priority-aware action state machine for a small desktop pet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .clip import ActionSpec, PetAction


@dataclass(frozen=True, slots=True)
class StateChange:
    previous: PetAction
    current: PetAction
    reason: str


class ActionStateMachine:
    """Accept high-value interactions without letting idle actions fight them."""

    def __init__(self, specs: Mapping[PetAction, ActionSpec]) -> None:
        self.specs = dict(specs)
        if PetAction.IDLE not in self.specs:
            raise ValueError("IDLE action is required")
        self.current = PetAction.IDLE
        self.entered_at = 0.0
        self.reason = "startup"
        self._queued_after: PetAction | None = None

    @property
    def spec(self) -> ActionSpec:
        return self.specs[self.current]

    def request(
        self,
        target: PetAction | str,
        *,
        now: float,
        reason: str,
        force: bool = False,
    ) -> StateChange | None:
        target = PetAction.coerce(target)
        if target == self.current:
            return None
        candidate = self.specs[target]
        current = self.spec
        if not force:
            if not current.interruptible and candidate.priority <= current.priority:
                return None
            if candidate.priority < current.priority:
                return None
        previous = self.current
        self.current = target
        self.entered_at = now
        self.reason = reason
        self._queued_after = None
        return StateChange(previous, target, reason)

    def queue_after_current(self, target: PetAction | str) -> None:
        self._queued_after = PetAction.coerce(target)

    def update(self, *, now: float) -> StateChange | None:
        spec = self.spec
        if spec.loop or spec.duration_ms is None:
            return None
        if now - self.entered_at < spec.duration_ms / 1000.0:
            return None
        target = self._queued_after or spec.return_state
        previous = self.current
        self.current = target
        self.entered_at = now
        self.reason = f"{previous.value.lower()}_complete"
        self._queued_after = None
        return StateChange(previous, target, self.reason)
