from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(slots=True)
class PetState:
    """Small, intentionally lightweight state that gives the pet continuity."""

    mood: float = 0.62
    energy: float = 0.78
    boredom: float = 0.28
    affinity: float = 0.42
    annoyance: float = 0.04
    dizziness: float = 0.0
    total_feedings: int = 0
    last_saved_at: float = 0.0

    def advance(self, seconds: float, *, activity: str = "idle") -> None:
        if seconds <= 0:
            return
        bounded_seconds = min(seconds, 24.0 * 3600.0)
        hours = bounded_seconds / 3600.0
        activity = str(activity or "idle").lower()

        if activity == "sleeping":
            # Naps use a compressed desktop-pet rhythm: a visible 30-50 second
            # sleep should restore enough energy to have a readable purpose.
            self.energy = _clamp(self.energy + bounded_seconds * 0.0016)
            self.boredom = _clamp(self.boredom - bounded_seconds * 0.00025)
        else:
            energy_cost = 0.025
            if activity == "walking":
                energy_cost += 0.035
            elif activity == "sweeping":
                energy_cost += 0.050
            self.energy = _clamp(self.energy - hours * energy_cost)
            boredom_rate = 0.10 if activity == "idle" else (0.06 if activity == "thinking" else 0.02)
            self.boredom = _clamp(self.boredom + hours * boredom_rate)
        self.annoyance = _clamp(self.annoyance - hours * 0.035)
        self.dizziness = _clamp(self.dizziness - hours * 0.12)
        self.mood = _clamp(self.mood + (self.affinity - 0.5) * hours * 0.01)

    def finish_activity(self, activity: str) -> None:
        """Apply the small, legible payoff of a completed autonomous activity."""

        activity = str(activity).lower()
        effects = {
            "observe": (0.0, -0.0003, 0.0, 0.0),
            "stroll": (-0.0020, -0.0012, 0.0003, 0.0),
            "tidy": (-0.0030, -0.0020, 0.0007, 0.0),
            "delight": (0.0, -0.0005, 0.0020, 0.0),
            "nap": (0.0100, -0.0008, 0.0005, -0.015),
            "murmur": (0.0, -0.0003, 0.0002, 0.0),
            "withdraw": (-0.0020, -0.0010, -0.0005, -0.040),
        }
        energy, boredom, mood, annoyance = effects.get(activity, (0.0, 0.0, 0.0, 0.0))
        self.energy = _clamp(self.energy + energy)
        self.boredom = _clamp(self.boredom + boredom)
        self.mood = _clamp(self.mood + mood)
        self.annoyance = _clamp(self.annoyance + annoyance)

    def feed(self) -> None:
        self.energy = _clamp(self.energy + 0.12)
        self.mood = _clamp(self.mood + 0.06)
        self.boredom = _clamp(self.boredom - 0.08)
        self.affinity = _clamp(self.affinity + 0.018)
        self.total_feedings += 1

    def pet_head(self) -> None:
        self.mood = _clamp(self.mood + 0.035)
        self.affinity = _clamp(self.affinity + 0.012)
        self.annoyance = _clamp(self.annoyance - 0.025)

    def tap(self) -> None:
        self.boredom = _clamp(self.boredom - 0.018)
        self.annoyance = _clamp(self.annoyance + 0.012)

    def drag(self) -> None:
        self.dizziness = _clamp(self.dizziness + 0.06)
        self.annoyance = _clamp(self.annoyance + 0.018)

    @classmethod
    def from_mapping(cls, raw: object) -> "PetState":
        state = cls()
        if not isinstance(raw, dict):
            return state
        for key in asdict(state):
            value = raw.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                setattr(state, key, float(value) if key != "total_feedings" else int(value))
        for key in ("mood", "energy", "boredom", "affinity", "annoyance", "dizziness"):
            setattr(state, key, _clamp(getattr(state, key)))
        state.total_feedings = max(0, int(state.total_feedings))
        return state


class PetStateStore:
    """Persist a few floats on exit; no window or browsing history is stored."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> PetState:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return PetState()
        state = PetState.from_mapping(raw)
        if state.last_saved_at:
            state.advance(max(0.0, time.time() - state.last_saved_at))
        return state

    def save(self, state: PetState) -> None:
        state.last_saved_at = time.time()
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
