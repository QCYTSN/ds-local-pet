from __future__ import annotations

import random
import unittest
from collections import Counter

from animation.clip import PetAction
from behavior.activity_director import (
    ActivityCueType,
    ActivityDirector,
    ActivityKind,
)
from pet.state import PetState


class ActivityDirectorTests(unittest.TestCase):
    def test_low_energy_makes_nap_the_strongest_need(self) -> None:
        director = ActivityDirector(random.Random(3))
        state = PetState(energy=0.20, boredom=0.45, mood=0.55)

        scores = director.scores_for(state, now=100.0, allow_movement=True)

        self.assertEqual(max(scores, key=scores.get), ActivityKind.NAP)
        self.assertGreater(scores[ActivityKind.NAP], scores[ActivityKind.OBSERVE] * 2)

    def test_private_context_suppresses_autonomous_speech(self) -> None:
        director = ActivityDirector(random.Random(4))
        director.observe_context(
            category="document",
            idle_seconds=0.0,
            private=True,
            late_night=False,
        )

        scores = director.scores_for(PetState(), now=50.0, allow_movement=True)

        self.assertEqual(scores[ActivityKind.MURMUR], 0.0)

    def test_completed_activity_enters_cooldown(self) -> None:
        director = ActivityDirector(random.Random(5))
        state = PetState()
        self.assertTrue(director.start(ActivityKind.OBSERVE, now=0.0))
        first = director.update(
            now=0.0,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )
        completed = director.update(
            now=10.0,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )

        self.assertEqual(first.cue_type, ActivityCueType.ACTION)
        self.assertEqual(completed.cue_type, ActivityCueType.COMPLETE)
        scores = director.scores_for(state, now=10.0, allow_movement=True)
        self.assertEqual(scores[ActivityKind.OBSERVE], 0.0)

    def test_stroll_waits_until_the_scheduled_walk_finishes(self) -> None:
        director = ActivityDirector(random.Random(6))
        state = PetState()
        director.start(ActivityKind.STROLL, now=0.0)
        director.update(
            now=0.0,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )
        walk = director.update(
            now=5.0,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )

        self.assertEqual(walk.cue_type, ActivityCueType.WALK)
        self.assertIsNone(
            director.update(
                now=5.1,
                state=state,
                can_start=True,
                is_walking=False,
                allow_movement=True,
            )
        )
        self.assertIsNone(
            director.update(
                now=5.2,
                state=state,
                can_start=True,
                is_walking=True,
                allow_movement=True,
            )
        )
        after_walk = director.update(
            now=5.3,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )
        self.assertEqual(after_walk.cue_type, ActivityCueType.ACTION)
        self.assertEqual(after_walk.action, PetAction.THINKING)

    def test_nap_sequence_always_has_a_wake_action(self) -> None:
        director = ActivityDirector(random.Random(7))
        state = PetState(energy=0.25)
        director.start(ActivityKind.NAP, now=0.0)

        sleepy = director.update(
            now=0.0,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )
        sleeping = director.update(
            now=10.0,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )
        waking = director.update(
            now=100.0,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )
        completed = director.update(
            now=110.0,
            state=state,
            can_start=True,
            is_walking=False,
            allow_movement=True,
        )

        self.assertEqual(sleepy.action, PetAction.THINKING)
        self.assertEqual(sleeping.action, PetAction.SLEEPING)
        self.assertEqual(waking.action, PetAction.HAPPY)
        self.assertEqual(completed.cue_type, ActivityCueType.COMPLETE)

    def test_one_hour_simulation_stays_varied_and_not_mostly_static(self) -> None:
        director = ActivityDirector(
            random.Random(11),
            initial_delay_range=(0.0, 0.0),
            decision_delay_range=(4.0, 9.0),
        )
        state = PetState()
        completed: list[ActivityKind] = []
        active_ticks = 0
        walk_until = -1.0
        step = 0.25

        for index in range(int(3600.0 / step)):
            now = index * step
            is_walking = now < walk_until
            cue = director.current_cue
            if is_walking:
                state_activity = "walking"
            elif cue is not None and cue.action is not None:
                state_activity = cue.action.value.lower()
            else:
                state_activity = "idle"
            state.advance(step, activity=state_activity)
            command = director.update(
                now=now,
                state=state,
                can_start=not is_walking,
                is_walking=is_walking,
                allow_movement=True,
            )
            if command is not None and command.cue_type == ActivityCueType.WALK:
                walk_until = now + max(1.0, command.distance_body_widths * 1.6)
            elif command is not None and command.cue_type == ActivityCueType.COMPLETE:
                completed.append(command.activity)
                state.finish_activity(command.activity.value)
            if director.active or is_walking:
                active_ticks += 1

        counts = Counter(completed)
        active_share = active_ticks / int(3600.0 / step)
        self.assertGreaterEqual(len(counts), 5)
        self.assertGreater(len(completed), 80)
        self.assertGreater(active_share, 0.30)
        self.assertLess(active_share, 0.72)
        self.assertTrue(all(left != right for left, right in zip(completed, completed[1:])))
        self.assertLess(max(counts.values()) / len(completed), 0.45)


class PetActivityStateTests(unittest.TestCase):
    def test_sleep_recovers_energy_and_completed_stroll_reduces_boredom(self) -> None:
        state = PetState(energy=0.30, boredom=0.70)

        state.advance(30.0, activity="sleeping")
        after_sleep = state.energy
        state.finish_activity("stroll")

        self.assertGreater(after_sleep, 0.30)
        self.assertLess(state.boredom, 0.70)


if __name__ == "__main__":
    unittest.main()
