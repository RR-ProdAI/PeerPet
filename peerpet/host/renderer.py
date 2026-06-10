"""Render the pet into the reserved region.

Composes a status line from the pet state + a *given* sprite, then uses
`region.draw_at` to place it without disturbing the user's cursor. The pet is
**right-aligned** in its reserved row, so it lands in the corner (bottom-right by
default) with headroom to animate.

The sprite is passed in (not chosen here) so the renderer is decoupled from the
animation source — the caller (the host loop, or `peerpet demo`) gets the frame
from `pet.animation.Animator` and hands it over.

`compose()`, `compose_lines()`, and `display_width()` are pure and
unit-testable; `draw()` does the actual write.
"""

from __future__ import annotations

import sys
import unicodedata

from peerpet.host import region
from peerpet.pet.state import PetState


def _status(state: PetState) -> str:
    """The one-line stat readout shown beneath the pet."""
    return (
        f"{state.name} · {state.mood.value} · "
        f"hunger {int(state.hunger)} · happiness {int(state.happiness)}"
    )


def compose(state: PetState, sprite: str) -> str:
    """Single-line composition for the 1-row pet strip: the sprite's *face* row
    + status. For a multi-row mascot the face is the middle row (not row 0, which
    is just the head dome), so the strip still shows eyes/mouth."""
    rows = sprite.split("\n")
    face = rows[len(rows) // 2]
    return f"{face}  {_status(state)}"


def compose_lines(state: PetState, sprite: str) -> list[str]:
    """Multi-row composition: each sprite row, then a status line beneath.

    Returns a list of plain strings (no escape codes); the caller positions and
    draws them. Used by the multi-line demo/host renderers.
    """
    return sprite.split("\n") + [_status(state)]


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


def draw(state: PetState, sprite: str, row: int, cols: int, out=sys.stdout) -> None:
    """Write the composed line right-aligned into the reserved `row` (1-indexed)."""
    line = compose(state, sprite)
    out.write(region.draw_at(row, line, right_aligned_col(line, cols)))
    out.flush()
