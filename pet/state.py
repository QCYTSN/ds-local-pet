from __future__ import annotations

import json
import time
from datetime import date
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
    total_head_pats: int = 0
    total_pokes: int = 0
    total_drags: int = 0
    sessions: int = 0
    last_session_date: str = ""
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
        self.total_head_pats += 1

    def tap(self, intensity: float = 1.0) -> None:
        intensity = max(0.25, min(3.0, float(intensity)))
        self.boredom = _clamp(self.boredom - 0.018)
        self.annoyance = _clamp(self.annoyance + 0.012 * intensity)
        self.total_pokes += 1

    def drag(self) -> None:
        self.dizziness = _clamp(self.dizziness + 0.06)
        self.annoyance = _clamp(self.annoyance + 0.018)
        self.total_drags += 1

    def begin_session(self, today: str | None = None) -> bool:
        """Return True for the first launch seen on this calendar day."""
        current = today or date.today().isoformat()
        first_today = self.last_session_date != current
        self.last_session_date = current
        self.sessions += 1
        return first_today

    def visible_condition(self) -> str:
        """Return a small presentation state instead of exposing raw meters."""

        if self.energy < 0.30:
            return "tired"
        if self.annoyance >= 0.34:
            return "annoyed"
        if self.boredom >= 0.70:
            return "restless"
        if self.mood >= 0.78 and self.affinity >= 0.58:
            return "cheerful"
        if self.affinity >= 0.76:
            return "affectionate"
        return "steady"

    @classmethod
    def from_mapping(cls, raw: object) -> "PetState":
        state = cls()
        if not isinstance(raw, dict):
            return state
        integer_fields = {
            "total_feedings",
            "total_head_pats",
            "total_pokes",
            "total_drags",
            "sessions",
        }
        for key in asdict(state):
            value = raw.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                setattr(state, key, int(value) if key in integer_fields else float(value))
        if isinstance(raw.get("last_session_date"), str):
            state.last_session_date = str(raw["last_session_date"])
        for key in ("mood", "energy", "boredom", "affinity", "annoyance", "dizziness"):
            setattr(state, key, _clamp(getattr(state, key)))
        for key in integer_fields:
            setattr(state, key, max(0, int(getattr(state, key))))
        return state


class PetStateStore:
    """Persist a few floats on exit; no window or browsing history is stored."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> PetState:
        raw = self._read_mapping(self.path)
        if not raw:
            raw = self._read_mapping(self.path.with_suffix(self.path.suffix + ".bak"))
        if not raw:
            return PetState()
        state = PetState.from_mapping(raw)
        if state.last_saved_at:
            state.advance(max(0.0, time.time() - state.last_saved_at))
        return state

    def save(self, state: PetState) -> None:
        state.last_saved_at = time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        backup = self.path.with_suffix(self.path.suffix + ".bak")
        if self.path.is_file() and self._read_mapping(self.path):
            try:
                backup.write_bytes(self.path.read_bytes())
            except OSError:
                pass
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _read_mapping(path: Path) -> dict[str, object]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        return value if isinstance(value, dict) else {}
