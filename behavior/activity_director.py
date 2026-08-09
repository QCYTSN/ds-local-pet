"""State-aware activity planning for the desktop pet.

The animation state machine answers "may this pose interrupt the current one?".
This module answers the higher-level question: "what small thing should the pet
do next, and what sequence of poses makes that intention readable?"
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from enum import Enum

from animation.clip import PetAction
from pet.state import PetState


class ActivityKind(str, Enum):
    OBSERVE = "observe"
    STROLL = "stroll"
    TIDY = "tidy"
    DELIGHT = "delight"
    NAP = "nap"
    MURMUR = "murmur"
    WITHDRAW = "withdraw"


class ActivityCueType(str, Enum):
    ACTION = "action"
    WALK = "walk"
    SPEAK = "speak"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class ActivityContext:
    category: str = "unknown"
    user_idle: bool = False
    private: bool = False
    late_night: bool = False


@dataclass(frozen=True, slots=True)
class ActivityCue:
    kind: ActivityCueType
    action: PetAction | None = None
    duration_range: tuple[float, float] = (0.0, 0.0)
    distance_range: tuple[float, float] = (0.0, 0.0)
    away_from_cursor: bool = False


@dataclass(frozen=True, slots=True)
class ActivityPlan:
    kind: ActivityKind
    cues: tuple[ActivityCue, ...]
    cooldown_seconds: float


@dataclass(frozen=True, slots=True)
class ActivityCommand:
    activity: ActivityKind
    cue_type: ActivityCueType
    action: PetAction | None = None
    duration_seconds: float = 0.0
    distance_body_widths: float = 0.0
    away_from_cursor: bool = False
    inner: bool = False


def _action(
    action: PetAction,
    minimum: float,
    maximum: float,
) -> ActivityCue:
    return ActivityCue(
        ActivityCueType.ACTION,
        action=action,
        duration_range=(minimum, maximum),
    )


def _walk(
    minimum_distance: float,
    maximum_distance: float,
    *,
    away_from_cursor: bool = False,
) -> ActivityCue:
    return ActivityCue(
        ActivityCueType.WALK,
        duration_range=(4.0, 12.0),
        distance_range=(minimum_distance, maximum_distance),
        away_from_cursor=away_from_cursor,
    )


ACTIVITY_PLANS: dict[ActivityKind, ActivityPlan] = {
    ActivityKind.OBSERVE: ActivityPlan(
        ActivityKind.OBSERVE,
        (_action(PetAction.THINKING, 2.5, 3.6),),
        cooldown_seconds=48.0,
    ),
    ActivityKind.STROLL: ActivityPlan(
        ActivityKind.STROLL,
        (
            _action(PetAction.THINKING, 0.9, 1.4),
            _walk(0.9, 2.2),
            _action(PetAction.THINKING, 1.5, 2.3),
        ),
        cooldown_seconds=78.0,
    ),
    ActivityKind.TIDY: ActivityPlan(
        ActivityKind.TIDY,
        (
            _action(PetAction.THINKING, 0.8, 1.2),
            _walk(0.7, 1.5),
            _action(PetAction.SWEEPING, 2.8, 3.2),
            _action(PetAction.HAPPY, 1.05, 1.25),
        ),
        cooldown_seconds=240.0,
    ),
    ActivityKind.DELIGHT: ActivityPlan(
        ActivityKind.DELIGHT,
        (_action(PetAction.HAPPY, 1.05, 1.35),),
        cooldown_seconds=110.0,
    ),
    ActivityKind.NAP: ActivityPlan(
        ActivityKind.NAP,
        (
            _action(PetAction.THINKING, 1.5, 2.2),
            _action(PetAction.SLEEPING, 32.0, 58.0),
            _action(PetAction.HAPPY, 1.05, 1.35),
        ),
        cooldown_seconds=600.0,
    ),
    ActivityKind.MURMUR: ActivityPlan(
        ActivityKind.MURMUR,
        (ActivityCue(ActivityCueType.SPEAK, duration_range=(4.0, 5.2)),),
        cooldown_seconds=420.0,
    ),
    ActivityKind.WITHDRAW: ActivityPlan(
        ActivityKind.WITHDRAW,
        (
            _action(PetAction.ANGRY, 1.5, 1.8),
            _walk(0.8, 1.5, away_from_cursor=True),
            _action(PetAction.THINKING, 1.5, 2.2),
        ),
        cooldown_seconds=180.0,
    ),
}


class ActivityDirector:
    """Choose and sequence low-interruption activities with recent-memory."""

    quiet_categories = {"coding", "document", "paper", "video", "game"}

    def __init__(
        self,
        rng: random.Random | None = None,
        *,
        initial_delay_range: tuple[float, float] = (12.0, 28.0),
        decision_delay_range: tuple[float, float] = (42.0, 105.0),
        activity_level: str = "balanced",
    ) -> None:
        self.rng = rng or random.Random()
        self.initial_delay_range = initial_delay_range
        self.decision_delay_range = decision_delay_range
        self.activity_level = self._normalized_activity_level(activity_level)
        self.context = ActivityContext()
        self._current_plan: ActivityPlan | None = None
        self._cue_index = 0
        self._cue_emitted = False
        self._cue_deadline = 0.0
        self._walk_seen = False
        self._next_decision_at: float | None = None
        self._cooldown_until: dict[ActivityKind, float] = {}
        self._recent: deque[ActivityKind] = deque(maxlen=6)

    @staticmethod
    def _normalized_activity_level(value: object) -> str:
        value = str(value or "balanced").lower()
        return value if value in {"calm", "balanced", "lively"} else "balanced"

    def set_activity_level(self, value: object, *, now: float | None = None) -> None:
        """Change pacing without discarding cooldowns or recent-memory."""

        self.activity_level = self._normalized_activity_level(value)
        if now is not None and not self.active:
            self._schedule_next(now)

    @property
    def active(self) -> bool:
        return self._current_plan is not None

    @property
    def current_activity(self) -> ActivityKind | None:
        return self._current_plan.kind if self._current_plan is not None else None

    @property
    def current_cue(self) -> ActivityCue | None:
        if self._current_plan is None or self._cue_index >= len(self._current_plan.cues):
            return None
        return self._current_plan.cues[self._cue_index]

    @property
    def recent(self) -> tuple[ActivityKind, ...]:
        return tuple(self._recent)

    def observe_context(
        self,
        *,
        category: str,
        idle_seconds: float,
        private: bool,
        late_night: bool,
    ) -> None:
        self.context = ActivityContext(
            category=category,
            user_idle=idle_seconds >= 300.0,
            private=private,
            late_night=late_night,
        )

    def scores_for(
        self,
        state: PetState,
        *,
        now: float,
        allow_movement: bool,
    ) -> dict[ActivityKind, float]:
        """Return transparent utility scores; zero means currently ineligible."""

        energy = state.energy
        boredom = state.boredom
        mood = state.mood
        affinity = state.affinity
        annoyance = state.annoyance

        nap_need = max(0.0, 0.62 - energy)
        scores = {
            ActivityKind.OBSERVE: 1.05 + boredom * 1.15,
            ActivityKind.STROLL: 0.62 + boredom * 2.10 + energy * 0.42,
            ActivityKind.TIDY: 0.32 + boredom * 1.60 + mood * 0.24,
            ActivityKind.DELIGHT: 0.24 + mood * 0.90 + affinity * 0.34,
            ActivityKind.NAP: (
                0.28 + nap_need * 8.5
                if nap_need > 0.0 or self.context.late_night
                else 0.0
            ),
            ActivityKind.MURMUR: 0.48 + boredom * 0.72,
            ActivityKind.WITHDRAW: max(0.0, annoyance - 0.18) * 8.0,
        }

        if not allow_movement:
            scores[ActivityKind.STROLL] = 0.0
            scores[ActivityKind.TIDY] = 0.0
            scores[ActivityKind.WITHDRAW] = 0.0
        if energy < 0.35:
            scores[ActivityKind.STROLL] *= 0.15
            scores[ActivityKind.TIDY] *= 0.15
            scores[ActivityKind.NAP] *= 1.8
        if annoyance > 0.18:
            social_factor = max(0.25, 1.0 - annoyance)
            scores[ActivityKind.DELIGHT] *= social_factor
            scores[ActivityKind.MURMUR] *= social_factor
        if self.context.category in self.quiet_categories:
            scores[ActivityKind.OBSERVE] *= 1.18
            scores[ActivityKind.STROLL] *= 0.82
            scores[ActivityKind.DELIGHT] *= 0.72
            scores[ActivityKind.MURMUR] *= 0.42
        if self.context.user_idle:
            scores[ActivityKind.OBSERVE] *= 1.12
            scores[ActivityKind.STROLL] *= 0.58
            scores[ActivityKind.MURMUR] *= 0.45
            scores[ActivityKind.NAP] += 0.8
        if self.context.late_night:
            scores[ActivityKind.NAP] += 0.75
            scores[ActivityKind.DELIGHT] *= 0.65
        if self.context.private:
            scores[ActivityKind.MURMUR] = 0.0

        for kind in ActivityKind:
            if now < self._cooldown_until.get(kind, float("-inf")):
                scores[kind] = 0.0
                continue
            if self._recent and self._recent[-1] == kind:
                scores[kind] = 0.0
                continue
            for distance, recent_kind in enumerate(reversed(self._recent)):
                if recent_kind == kind:
                    scores[kind] *= min(0.82, 0.18 + distance * 0.16)
                    break
            scores[kind] = max(0.0, scores[kind])
        return scores

    def choose_activity(
        self,
        state: PetState,
        *,
        now: float,
        allow_movement: bool,
    ) -> ActivityKind | None:
        scores = self.scores_for(state, now=now, allow_movement=allow_movement)
        total = sum(scores.values())
        if total <= 0.0:
            return None
        pick = self.rng.random() * total
        cumulative = 0.0
        for kind, score in scores.items():
            cumulative += score
            if pick <= cumulative:
                return kind
        return next(reversed(scores))

    def start(self, kind: ActivityKind, *, now: float) -> bool:
        if self._current_plan is not None:
            return False
        self._current_plan = ACTIVITY_PLANS[kind]
        self._cue_index = 0
        self._cue_emitted = False
        self._cue_deadline = now
        self._walk_seen = False
        return True

    def update(
        self,
        *,
        now: float,
        state: PetState,
        can_start: bool,
        is_walking: bool,
        allow_movement: bool,
    ) -> ActivityCommand | None:
        if self._current_plan is None:
            if self._next_decision_at is None:
                self._next_decision_at = now + self.rng.uniform(*self.initial_delay_range)
                return None
            if not can_start or now < self._next_decision_at:
                return None
            selected = self.choose_activity(
                state,
                now=now,
                allow_movement=allow_movement,
            )
            if selected is None:
                self._schedule_next(now)
                return None
            self.start(selected, now=now)

        while self._current_plan is not None:
            cue = self.current_cue
            if cue is None:
                return self._complete(now)
            if not self._cue_emitted:
                return self._emit(cue, now)

            if cue.kind == ActivityCueType.WALK:
                if is_walking:
                    self._walk_seen = True
                walk_finished = self._walk_seen and not is_walking
                if not walk_finished and now < self._cue_deadline:
                    return None
            elif now < self._cue_deadline:
                return None

            self._cue_index += 1
            self._cue_emitted = False
            self._walk_seen = False

        return None

    def skip_walk(self, *, now: float) -> None:
        cue = self.current_cue
        if cue is None or cue.kind != ActivityCueType.WALK or not self._cue_emitted:
            return
        self._walk_seen = True
        self._cue_deadline = now

    def interrupt(self, *, now: float, delay_seconds: float | None = None) -> ActivityKind | None:
        interrupted = self.current_activity
        self._clear_current()
        delay = self.rng.uniform(10.0, 18.0) if delay_seconds is None else max(0.0, delay_seconds)
        self._next_decision_at = now + delay
        return interrupted

    def _emit(self, cue: ActivityCue, now: float) -> ActivityCommand:
        if self._current_plan is None:
            raise RuntimeError("cannot emit a cue without an activity")
        duration = self.rng.uniform(*cue.duration_range)
        self._cue_emitted = True
        self._cue_deadline = now + duration
        if cue.kind == ActivityCueType.WALK:
            distance = self.rng.uniform(*cue.distance_range)
            return ActivityCommand(
                self._current_plan.kind,
                ActivityCueType.WALK,
                duration_seconds=duration,
                distance_body_widths=distance,
                away_from_cursor=cue.away_from_cursor,
            )
        if cue.kind == ActivityCueType.SPEAK:
            return ActivityCommand(
                self._current_plan.kind,
                ActivityCueType.SPEAK,
                duration_seconds=duration,
                inner=self.rng.random() < 0.72,
            )
        return ActivityCommand(
            self._current_plan.kind,
            ActivityCueType.ACTION,
            action=cue.action,
            duration_seconds=duration,
        )

    def _complete(self, now: float) -> ActivityCommand:
        if self._current_plan is None:
            raise RuntimeError("cannot complete an empty activity")
        plan = self._current_plan
        self._recent.append(plan.kind)
        self._cooldown_until[plan.kind] = now + plan.cooldown_seconds
        self._clear_current()
        self._schedule_next(now)
        return ActivityCommand(plan.kind, ActivityCueType.COMPLETE)

    def _schedule_next(self, now: float) -> None:
        minimum, maximum = self.decision_delay_range
        factor = {
            "calm": 1.65,
            "balanced": 1.0,
            "lively": 0.68,
        }[self.activity_level]
        if self.context.category in self.quiet_categories:
            factor *= 1.55
        if self.context.user_idle:
            factor *= 1.35
        self._next_decision_at = now + self.rng.uniform(minimum, maximum) * factor

    def _clear_current(self) -> None:
        self._current_plan = None
        self._cue_index = 0
        self._cue_emitted = False
        self._cue_deadline = 0.0
        self._walk_seen = False


class MicroMotionDirector:
    """Schedule tiny readable gestures independently from full activities."""

    _delay_ranges = {
        "calm": (10.0, 19.0),
        "balanced": (6.0, 14.0),
        "lively": (4.0, 10.0),
    }

    def __init__(
        self,
        rng: random.Random | None = None,
        *,
        activity_level: str = "balanced",
    ) -> None:
        self.rng = rng or random.Random()
        self.activity_level = ActivityDirector._normalized_activity_level(activity_level)
        self._next_at: float | None = None

    def set_activity_level(self, value: object, *, now: float | None = None) -> None:
        self.activity_level = ActivityDirector._normalized_activity_level(value)
        if now is not None:
            self.defer(now, minimum_seconds=2.5)

    def defer(self, now: float, *, minimum_seconds: float = 1.5) -> None:
        minimum, maximum = self._delay_ranges[self.activity_level]
        self._next_at = now + max(minimum_seconds, self.rng.uniform(minimum, maximum))

    def update(
        self,
        *,
        now: float,
        state: PetState,
        can_start: bool,
        reduced_motion: bool,
    ) -> PetAction | None:
        if self._next_at is None:
            self._next_at = now + self.rng.uniform(2.0, 5.0)
            return None
        if not can_start or now < self._next_at:
            return None

        glance_weight = 0.20 + state.boredom * 0.34 + state.affinity * 0.08
        if state.energy < 0.32:
            glance_weight *= 0.42
        if state.annoyance > 0.32:
            glance_weight *= 1.18
        if reduced_motion:
            glance_weight = 0.0
        action = PetAction.GLANCE if self.rng.random() < glance_weight else PetAction.BLINK
        minimum, maximum = self._delay_ranges[self.activity_level]
        delay = self.rng.uniform(minimum, maximum) * (1.7 if reduced_motion else 1.0)
        self._next_at = now + delay
        return action
