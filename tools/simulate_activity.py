"""Run a deterministic virtual hour through ActivityDirector for tuning."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from behavior.activity_director import ActivityCueType, ActivityDirector, MicroMotionDirector
from pet.state import PetState


def simulate(minutes: float, seed: int) -> dict[str, object]:
    step = 0.25
    total_seconds = max(60.0, minutes * 60.0)
    total_ticks = int(total_seconds / step)
    director = ActivityDirector(
        random.Random(seed),
        initial_delay_range=(0.0, 0.0),
    )
    micro_director = MicroMotionDirector(random.Random(seed + 101))
    state = PetState()
    walk_until = -1.0
    completed: Counter[str] = Counter()
    occupancy: Counter[str] = Counter()
    sequence: list[str] = []
    micro_motions: Counter[str] = Counter()

    for index in range(total_ticks):
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

        current = director.current_activity
        occupancy[current.value if current is not None else "idle"] += 1
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
            name = command.activity.value
            completed[name] += 1
            sequence.append(name)
            state.finish_activity(name)
        micro_action = micro_director.update(
            now=now,
            state=state,
            can_start=not director.active and not is_walking,
            reduced_motion=False,
        )
        if micro_action is not None:
            micro_motions[micro_action.value.lower()] += 1

    repeated_neighbors = sum(
        left == right for left, right in zip(sequence, sequence[1:])
    )
    occupancy_percent = {
        name: round(ticks / total_ticks * 100.0, 1)
        for name, ticks in sorted(occupancy.items())
    }
    return {
        "minutes": round(total_seconds / 60.0, 1),
        "seed": seed,
        "completed_activities": sum(completed.values()),
        "activity_counts": dict(sorted(completed.items())),
        "micro_motion_counts": dict(sorted(micro_motions.items())),
        "occupancy_percent": occupancy_percent,
        "consecutive_repeats": repeated_neighbors,
        "final_state": {
            "energy": round(state.energy, 3),
            "boredom": round(state.boredom, 3),
            "mood": round(state.mood, 3),
            "annoyance": round(state.annoyance, 3),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=11)
    arguments = parser.parse_args()
    print(json.dumps(simulate(arguments.minutes, arguments.seed), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
