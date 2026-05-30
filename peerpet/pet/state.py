"""The pet's data model.

`PetState` is plain data + (de)serialization. Behavior that *changes* the state
(decay over time, reactions to commands) lives in `pet/behavior.py`, not here —
keep this module free of logic so it stays a stable contract.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum


class Mood(str, Enum):
    HAPPY = "happy"
    CONTENT = "content"
    HUNGRY = "hungry"
    SLEEPY = "sleepy"
    SAD = "sad"


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


@dataclass
class PetState:
    """Everything we persist about one user's pet.

    Stats are 0–100. `last_seen` is a unix timestamp used by behavior.tick() to
    decay stats based on elapsed time, so the pet "lives" even while the host
    isn't running.
    """

    name: str = "Pixel"
    mood: Mood = Mood.CONTENT
    hunger: float = 50.0  # 100 = full, 0 = starving
    energy: float = 80.0  # 100 = rested, 0 = exhausted
    happiness: float = 70.0
    xp: int = 0
    level: int = 1
    last_seen: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.hunger = _clamp(self.hunger)
        self.energy = _clamp(self.energy)
        self.happiness = _clamp(self.happiness)
        if isinstance(self.mood, str):
            self.mood = Mood(self.mood)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["mood"] = self.mood.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> PetState:
        # Ignore unknown keys so older/newer saves don't crash each other.
        fields = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in fields})
