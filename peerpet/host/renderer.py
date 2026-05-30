"""Render the pet into the reserved region.

Composes a status line from the pet state + sprite, then uses `region.draw_at`
to place it without disturbing the user's cursor. The pet sits in the top strip,
**right-aligned**, so it lands in the top-right with headroom to animate.

`compose()` and `display_width()` are pure and unit-testable; `draw()` does the
actual write.
"""

from __future__ import annotations

import sys
import unicodedata

from peerpet.host import region
from peerpet.pet import sprites
from peerpet.pet.state import PetState


def compose(state: PetState, tick: int) -> str:
    """Build the one-line status string for the pet (no escape codes)."""
    sprite = sprites.frame_for(state.mood, tick)
    return (
        f"{sprite}  {state.name} · lvl {state.level} · "
        f"{state.mood.value} · hunger {int(state.hunger)} "
        f"· energy {int(state.energy)}"
    )


def display_width(text: str) -> int:
    """Terminal column width of `text`, counting East-Asian wide/full chars as 2.

    The kaomoji sprites use full-width glyphs, so a naive `len()` would
    right-align them too far left. Zero-width combining marks count as 0.
    """
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def right_aligned_col(text: str, cols: int) -> int:
    """1-indexed column so `text` ends flush with the right edge of `cols`."""
    return max(1, cols - display_width(text) + 1)


def draw(state: PetState, tick: int, row: int, cols: int, out=sys.stdout) -> None:
    """Write the composed line right-aligned into the reserved `row` (1-indexed)."""
    line = compose(state, tick)
    out.write(region.draw_at(row, line, right_aligned_col(line, cols)))
    out.flush()
