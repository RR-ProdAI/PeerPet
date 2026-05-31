"""Terminal scroll-region and cursor primitives.

This is the *only* module allowed to emit raw ANSI escape sequences. Everything
that touches the screen goes through here so cursor accounting lives in one
place (see AGENTS.md). All functions are pure string builders — no I/O — which
makes them trivial to unit-test.

References:
    DECSTBM (set top/bottom margins):  ESC [ <top> ; <bottom> r
    Save / restore cursor (DEC):       ESC 7 / ESC 8
    Cursor position (CUP):             ESC [ <row> ; <col> H
"""

from __future__ import annotations

ESC = "\x1b"
CSI = ESC + "["


def set_scroll_region(top: int, bottom: int) -> str:
    """Confine scrolling to rows [top, bottom] (1-indexed, inclusive)."""
    if top < 1 or bottom < top:
        raise ValueError(f"invalid scroll region: top={top} bottom={bottom}")
    return f"{CSI}{top};{bottom}r"


def reset_scroll_region() -> str:
    """Release the scroll region back to the full screen."""
    return f"{CSI}r"


def save_cursor() -> str:
    return f"{ESC}7"


def restore_cursor() -> str:
    return f"{ESC}8"


def move_cursor(row: int, col: int = 1) -> str:
    """Move the cursor to (row, col), both 1-indexed."""
    if row < 1 or col < 1:
        raise ValueError(f"invalid cursor position: row={row} col={col}")
    return f"{CSI}{row};{col}H"


def clear_line() -> str:
    """Erase the entire line the cursor is on."""
    return f"{CSI}2K"


def draw_at(row: int, text: str, col: int = 1) -> str:
    """Build a sequence that draws `text` at (row, col) without disturbing the
    user's cursor: save, move, clear line, write, restore.

    The whole thing is wrapped in save/restore so the shell's input position is
    exactly where it was before we drew.
    """
    return save_cursor() + move_cursor(row, col) + clear_line() + text + restore_cursor()


def reserve_top(total_rows: int, pet_rows: int) -> str:
    """Reserve the top `pet_rows` rows for the pet, leaving the rest as the
    scrolling shell area below. Returns the escape sequence to apply.

    The pet lives at the top (right-aligned by the renderer); the shell scrolls in
    rows `pet_rows+1 .. total_rows`. Because the scroll region excludes the pet
    rows, ordinary shell output can never scroll into them — only absolute cursor
    moves (`clear`, `ESC[H`) can, which the host re-anchors after.

    Note: the region's top margin is row `pet_rows+1`, not row 1, so most
    terminals do not feed scrolled-off lines into native scrollback while it's
    active. `reserve_bottom` keeps the top margin at row 1 and may preserve
    scrollback on some terminals.
    """
    if pet_rows < 1 or pet_rows >= total_rows:
        raise ValueError(f"pet_rows={pet_rows} out of range for {total_rows} rows")
    return set_scroll_region(pet_rows + 1, total_rows)


def reserve_bottom(total_rows: int, pet_rows: int) -> str:
    """Reserve the bottom `pet_rows` rows for the pet; the shell scrolls in rows
    `1 .. total_rows-pet_rows` above it. Returns the escape sequence to apply.

    The region's top margin stays at row 1, so the shell's own coordinates pass
    through untouched and some terminals still accumulate scrollback.
    """
    if pet_rows < 1 or pet_rows >= total_rows:
        raise ValueError(f"pet_rows={pet_rows} out of range for {total_rows} rows")
    return set_scroll_region(1, total_rows - pet_rows)


def teardown() -> str:
    """Sequence to leave the terminal clean: release the region and restore the
    cursor. Call this on EVERY exit path (atexit, signals, finally).
    """
    return reset_scroll_region() + restore_cursor()
