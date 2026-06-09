"""Render the pet into the reserved region.

Composes a status line from the pet state + a *given* sprite, then uses
`region.draw_at` to place it without disturbing the user's cursor. Pure-ish:
`compose()` returns a string and is unit-testable; `draw()` does the actual
write.

The sprite is passed in (not chosen here) so the renderer is decoupled from the
animation source — the caller (the host loop, or `peerpet demo`) gets the frame
from `pet.animation.Animator` and hands it over.
"""

from __future__ import annotations

import sys

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


def draw(state: PetState, sprite: str, row: int, out=sys.stdout) -> None:
    """Write the composed line into the reserved `row` (1-indexed)."""
    out.write(region.draw_at(row, compose(state, sprite)))
    out.flush()
