"""Sprite frames per mood. Keep ALL art here, never inline in logic.

The pet is a small multi-line "alien mascot" — a rounded head with two eyes, a
mouth, and little arms. Emotion is carried by the **mouth + arms** (the body
outline never changes), which keeps frames the same width/height so the pet
never jitters or jumps as it animates.

Design rules if you edit the art:
  - Every frame of every mood/reaction must be the SAME number of rows and the
    SAME visual width per row, or the pet will visibly jump. (Here: 3 rows, 7
    columns. Trailing spaces in the rows are intentional padding.)
  - Idle animation should be *mostly still*: the frame list is padded with the
    rest pose and blinks only occasionally (see FRAMES below).
  - Preview any change instantly with `peerpet demo` — no PTY host needed.
"""

from __future__ import annotations

from peerpet.pet.state import Mood

# --- building blocks -------------------------------------------------------
# Top (head dome) and bottom (body) rows are shared by every idle/blink frame.
_TOP = " ╭─◠─╮ "
_BOT = " ╰───╯ "


def _face(arms: str, eye_l: str, mouth: str, eye_r: str) -> str:
    """Compose one 3-row frame from a middle (face+arms) row."""
    a, b = arms  # left arm, right arm
    return "\n".join([_TOP, f"{a}({eye_l}{mouth}{eye_r}){b}", _BOT])


# Happy: arms up (ᕦ ᕤ), smiling mouth (‿). Blink closes the eyes (- -).
HAPPY_REST = _face("ᕦᕤ", "◕", "‿", "◕")
HAPPY_BLINK = _face("ᕦᕤ", "-", "‿", "-")
# Sad: arms drooped (ᕥ ᕥ), small frown (‸), downcast eyes (◔).
SAD_REST = _face("ᕥᕥ", "◔", "‸", "◔")
SAD_BLINK = _face("ᕥᕥ", "-", "‸", "-")

# Idle loops: mostly the rest pose, with one blink near the end. At ~0.5s per
# step that's a quick blink roughly every ~4s — alive, but not twitchy.
_HAPPY_IDLE = [HAPPY_REST] * 7 + [HAPPY_BLINK]
_SAD_IDLE = [SAD_REST] * 7 + [SAD_BLINK]

# Only two moods drive animation for now (see behavior._derive_mood): the pet is
# SAD when hunger is low, otherwise HAPPY. The other Mood values still map to art
# so nothing crashes if some other code path derives them.
FRAMES: dict[Mood, list[str]] = {
    Mood.HAPPY: _HAPPY_IDLE,
    Mood.CONTENT: _HAPPY_IDLE,
    Mood.SAD: _SAD_IDLE,
    Mood.HUNGRY: _SAD_IDLE,
    Mood.SLEEPY: _SAD_IDLE,
}

# One-shot reactions when a command lands — same body, so height never changes.
REACTIONS: dict[str, list[str]] = {
    # munch: mouth opens (o) → chews (ω) → satisfied smile (‿)
    "feed": [
        _face("ᕦᕤ", "◕", "o", "◕"),
        _face("ᕦᕤ", "◕", "ω", "◕"),
        _face("ᕦᕤ", "^", "ω", "^"),
        _face("ᕦᕤ", "◕", "‿", "◕"),
    ],
    # wave: arms swing up (ᕗ ᕖ) and back to rest. Must stay 7 cols wide like
    # every other frame — earlier `ヽ`/`ﾉ` were 2-col/1-col and made the pet jump.
    "play": [
        _face("ᕗᕖ", "◕", "‿", "◕"),
        HAPPY_REST,
        _face("ᕗᕖ", "◕", "ᴗ", "◕"),
        HAPPY_REST,
    ],
    # affection: hearts pop above the head
    "pet": [
        "\n".join([" ♡   ♡ ", "ᕦ(◕‿◕)ᕤ", _BOT]),
        "\n".join(["  ♥ ♥  ", "ᕦ(◕ᴗ◕)ᕤ", _BOT]),
        "\n".join([" ♡   ♡ ", "ᕦ(◕‿◕)ᕤ", _BOT]),
    ],
}


def frame_for(mood: Mood, tick: int) -> str:
    """Return the sprite frame for a mood at animation step `tick`."""
    frames = FRAMES.get(mood, FRAMES[Mood.HAPPY])
    return frames[tick % len(frames)]


def reaction_frames(command: str) -> list[str]:
    """Return the reaction sequence for a command, or [] if there isn't one.

    Returning an empty list (rather than raising) keeps callers simple: an
    unknown command just means "no reaction, stay on the idle animation".
    """
    return REACTIONS.get(command, [])
