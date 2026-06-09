"""Pet behavior — the deterministic state machine.

Two responsibilities:
  - tick(): advance the pet over elapsed wall-clock time (stats decay, mood).
  - apply_command(): react to a user interaction (feed/play/pet).

No LLM, no randomness in the core loop (keep it predictable and testable). This
is the whole brain — the pet is deterministic by design.
"""

from __future__ import annotations

import time

from peerpet.pet.state import Mood, PetState, _clamp

# Per-hour decay rates (stats are 0–100).
HUNGER_DECAY_PER_HOUR = 8.0
ENERGY_DECAY_PER_HOUR = 5.0
HAPPINESS_DECAY_PER_HOUR = 4.0

# Below either threshold the pet is SAD; otherwise HAPPY. Two moods only for now
# (see sprites.py) — the animation reads clearly as happy vs sad.
HUNGER_SAD_THRESHOLD = 30.0
HAPPINESS_SAD_THRESHOLD = 30.0

# How much each interaction gives.
FEED_HUNGER = 25.0
PLAY_HAPPINESS = 20.0
PLAY_ENERGY_COST = 10.0
PET_HAPPINESS = 8.0

XP_PER_INTERACTION = 5
XP_PER_LEVEL = 100


def tick(state: PetState, now: float | None = None) -> PetState:
    """Decay stats based on time since `last_seen`, then recompute mood."""
    now = time.time() if now is None else now
    hours = max(0.0, (now - state.last_seen) / 3600.0)

    state.hunger = _clamp(state.hunger - HUNGER_DECAY_PER_HOUR * hours)
    state.energy = _clamp(state.energy - ENERGY_DECAY_PER_HOUR * hours)
    state.happiness = _clamp(state.happiness - HAPPINESS_DECAY_PER_HOUR * hours)
    state.last_seen = now
    state.mood = _derive_mood(state)
    return state


def apply_command(state: PetState, command: str) -> PetState:
    """Apply an interaction command. Returns the same (mutated) state."""
    tick(state)  # settle to "now" before reacting

    if command == "feed":
        state.hunger = _clamp(state.hunger + FEED_HUNGER)
    elif command == "play":
        state.happiness = _clamp(state.happiness + PLAY_HAPPINESS)
        state.energy = _clamp(state.energy - PLAY_ENERGY_COST)
    elif command == "pet":
        state.happiness = _clamp(state.happiness + PET_HAPPINESS)
    else:
        raise ValueError(f"unknown command: {command!r}")

    _grant_xp(state, XP_PER_INTERACTION)
    state.mood = _derive_mood(state)
    return state


def _grant_xp(state: PetState, amount: int) -> None:
    state.xp += amount
    while state.xp >= XP_PER_LEVEL:
        state.xp -= XP_PER_LEVEL
        state.level += 1


def _derive_mood(state: PetState) -> Mood:
    """Two moods: SAD when hunger or happiness runs low, else HAPPY."""
    if state.hunger < HUNGER_SAD_THRESHOLD or state.happiness < HAPPINESS_SAD_THRESHOLD:
        return Mood.SAD
    return Mood.HAPPY
