"""Sprite frames per mood. Keep ALL art here, never inline in logic.

Each mood maps to a list of frames; cycle through frames for idle animation.
Frames should be single-line for the MVP (pet_rows defaults to 1). Add
multi-line frames later by making the renderer join rows.
"""

from __future__ import annotations

from peerpet.pet.state import Mood

FRAMES: dict[Mood, list[str]] = {
    Mood.HAPPY: ["(=^･ω･^=)", "(=^･ｪ･^=)"],
    Mood.CONTENT: ["(･ω･)", "(･ｪ･)"],
    Mood.HUNGRY: ["(；ω；)", "( ｡ω｡)"],
    Mood.SLEEPY: ["(-ω-) zzZ", "(_ω_) zzZ"],
    Mood.SAD: ["(╥﹏╥)", "(；﹏；)"],
}


def frame_for(mood: Mood, tick: int) -> str:
    """Return the sprite frame for a mood at animation step `tick`."""
    frames = FRAMES.get(mood, FRAMES[Mood.CONTENT])
    return frames[tick % len(frames)]
