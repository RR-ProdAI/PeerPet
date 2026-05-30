"""Render the pet into the reserved region.

Composes a status line from the pet state + sprite, then uses `region.draw_at`
to place it without disturbing the user's cursor. Pure-ish: `compose()` returns
a string and is unit-testable; `draw()` does the actual write.
"""

from __future__ import annotations

import sys

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


def draw(state: PetState, tick: int, row: int, out=sys.stdout) -> None:
    """Write the composed line into the reserved `row` (1-indexed)."""
    out.write(region.draw_at(row, compose(state, tick)))
    out.flush()
