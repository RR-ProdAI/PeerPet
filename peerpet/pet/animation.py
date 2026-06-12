"""The animation engine — picks which sprite to show, frame by frame.

This is intentionally pure logic with an *injectable clock* (same style as
`behavior.tick(now=...)`), so it can be unit-tested without sleeping and without
a terminal. It knows nothing about ANSI codes or how the frame gets drawn.

Two layers of animation:
  - **idle:** a steady loop of the current mood's frames (a slow "blink").
  - **reaction:** a one-shot sequence played when a command lands (feed/play/
    pet). While a reaction is active it overrides the idle frames; once it runs
    out, the pet settles back to the idle mood animation.

The host loop (and the standalone `peerpet demo`) call `current_sprite(mood)` on
every render tick to get the string to draw.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from peerpet.pet import sprites
from peerpet.pet.state import Mood

# Seconds each idle frame is held before advancing (a slow blink).
IDLE_FRAME_INTERVAL = 0.5
# Seconds each reaction frame is held (snappier than idle).
REACTION_FRAME_INTERVAL = 0.25


# A frame is whatever the sprite library yields: a string of text-art rows
# (`pet.sprites`) or a list of pixel rows (`pet.pixel_sprites`).
Frame = str | list[str]


class Animator:
    """Stateful frame picker for one pet.

    Holds only animation timing state (when the current reaction started); the
    pet's mood is passed in on each call so this never duplicates the pet model.
    The timing logic is sprite-format agnostic: `library` is any module/object
    with `frame_for(mood, tick)` and `reaction_frames(command)` — text art by
    default, `pet.pixel_sprites` for the sixel pet.
    """

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        library=sprites,
    ) -> None:
        self._clock = clock
        self._library = library
        self._start = clock()
        self._reaction: list[Frame] = []
        self._reaction_start: float | None = None

    def _now(self, now: float | None) -> float:
        return self._clock() if now is None else now

    def trigger(self, command: str, now: float | None = None) -> None:
        """Start a one-shot reaction for `command`. Unknown commands are ignored
        (no frames), leaving the pet on its idle animation."""
        frames = self._library.reaction_frames(command)
        if not frames:
            return
        self._reaction = frames
        self._reaction_start = self._now(now)

    def is_reacting(self, now: float | None = None) -> bool:
        """True while a triggered reaction is still playing."""
        if self._reaction_start is None:
            return False
        elapsed = self._now(now) - self._reaction_start
        return elapsed < len(self._reaction) * REACTION_FRAME_INTERVAL

    def current_sprite(self, mood: Mood, now: float | None = None) -> Frame:
        """The sprite string to draw right now.

        A live reaction overrides the idle loop; otherwise the mood's idle
        frames cycle on IDLE_FRAME_INTERVAL.
        """
        now = self._now(now)
        if self._reaction_start is not None:
            elapsed = now - self._reaction_start
            index = int(elapsed / REACTION_FRAME_INTERVAL)
            if index < len(self._reaction):
                return self._reaction[index]
            # Reaction finished — clear it and fall through to idle.
            self._reaction = []
            self._reaction_start = None

        idle_tick = int((now - self._start) / IDLE_FRAME_INTERVAL)
        return self._library.frame_for(mood, idle_tick)
