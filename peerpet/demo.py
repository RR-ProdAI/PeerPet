"""`peerpet demo` — a safe, standalone animation preview.

This drives the animation engine in the *current* terminal **without** the PTY
host: no DECSTBM scroll region, no raw-mode stdin, no forked shell. On a sixel
terminal (Windows Terminal >= 1.22, xterm, foot, ...) the pet renders as real
pixel art with stat bars; elsewhere it falls back to the Unicode mascot. Both
paths repaint a small block in place using only the cursor/clear builders from
`host.region` (plus the sixel image string from `host.sixel`).

It is non-interactive on purpose (the pet's expression follows its mood, which
follows its stats). To make moods actually change within seconds, the demo runs
on an *accelerated* clock — each frame simulates a chunk of pet-time — and fires
scripted feed/play/pet commands so you can watch the one-shot reactions resolve
back into the idle mood animation. Ctrl-C exits and leaves the terminal clean.
"""

from __future__ import annotations

import sys
import time

from peerpet.host import region, renderer, sixel, termcaps
from peerpet.pet import behavior, pixel_sprites
from peerpet.pet.animation import Animator
from peerpet.pet.state import PetState

# Real seconds between rendered frames. Kept at/under the reaction frame
# interval so every reaction frame gets shown.
FRAME_INTERVAL = 0.25
# Pet-hours of decay simulated per rendered frame (accelerates mood changes so
# the demo is interesting within seconds instead of hours). Tuned with the
# script below so stats oscillate around the sad/happy threshold — you see the
# pet dip into sad and bounce back to happy, rather than spiralling one way.
SIM_HOURS_PER_FRAME = 0.105
# Fire a scripted command every N frames, cycling through this script. One feed
# per cycle ≈ matches the hunger lost per cycle, so hunger sawtooths around the
# sad/happy threshold (play/pet keep happiness high, so hunger drives the mood).
COMMAND_EVERY = 10
SCRIPT = ["feed", "play", "pet"]
# Integer zoom for the pixel pet (logical sprite pixels -> screen pixels).
PIXEL_SCALE = 4


def _advance(state: PetState, sim_hours: float) -> None:
    """Decay the pet by `sim_hours` of pet-time using the real behavior.tick.

    We rewind `last_seen` by the simulated span and tick to "now", so tick
    applies exactly `sim_hours` of decay and resets last_seen to now. This keeps
    us on the public behavior API (no duplicated decay math) while running on a
    fast clock.
    """
    now = time.time()
    state.last_seen = now - sim_hours * 3600.0
    behavior.tick(state, now=now)


def _scripted_command(frame: int) -> str | None:
    """The feed/play/pet command to fire at this frame number, if any. The -1
    makes the first command fired (at frame == COMMAND_EVERY) be SCRIPT[0]."""
    if frame and frame % COMMAND_EVERY == 0:
        return SCRIPT[(frame // COMMAND_EVERY - 1) % len(SCRIPT)]
    return None


def _paint(out, lines: list[str], first: bool) -> None:
    """Repaint the text pet block in place. On every frame after the first,
    step the cursor back up to the top of the block, then clear+rewrite each
    row, leaving the cursor parked back at the top for the next frame."""
    if not first:
        out.write(region.cursor_up(len(lines) - 1))
    parts = []
    for i, ln in enumerate(lines):
        parts.append("\r" + region.clear_line() + ln)
        if i != len(lines) - 1:
            parts.append("\n")
    out.write("".join(parts))
    out.flush()


def _run_text(state: PetState, out) -> int:
    """The Unicode-art fallback loop (terminals without sixel)."""
    animator = Animator()
    frame = 0
    try:
        # Hide the cursor *inside* the try so the finally always restores it,
        # even if a signal lands between here and the loop.
        out.write(region.hide_cursor())
        out.flush()
        while True:
            _advance(state, SIM_HOURS_PER_FRAME)
            command = _scripted_command(frame)
            if command:
                behavior.apply_command(state, command)
                animator.trigger(command)

            sprite = animator.current_sprite(state.mood)
            lines = renderer.compose_lines(state, sprite)
            _paint(out, lines, first=(frame == 0))

            frame += 1
            time.sleep(FRAME_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        # After the last paint the cursor sits on the bottom row of the block;
        # one newline drops the shell prompt cleanly below the pet.
        out.write("\r" + region.show_cursor() + "\n")
        out.flush()
    return 0


def _pixel_frame(state: PetState, animator: Animator) -> list[str]:
    """One full pixel grid for this tick: sprite + spacer + stat bars."""
    return renderer.compose_pixel(state, animator.current_sprite(state.mood))


def _run_sixel(state: PetState, out) -> int:
    """The pixel-art loop. The cursor invariant: between paints it always sits
    on the FIRST row of the pet block, so each repaint is clear-down/come-back/
    redraw with no absolute positions needed."""
    animator = Animator(library=pixel_sprites)
    _, cell_h = termcaps.cell_pixel_size()
    grid_h = len(_pixel_frame(state, animator)) * PIXEL_SCALE
    rows = -(-grid_h // cell_h)  # ceil: terminal rows the image occupies

    frame = 0
    last_grid: list[str] | None = None
    try:
        out.write(region.hide_cursor())
        # Open up `rows` blank lines (scrolling if at the bottom of the
        # screen), then park the cursor on the block's first row.
        out.write("\n" * rows + region.cursor_up(rows))
        out.flush()
        while True:
            _advance(state, SIM_HOURS_PER_FRAME)
            command = _scripted_command(frame)
            if command:
                behavior.apply_command(state, command)
                animator.trigger(command)

            grid = _pixel_frame(state, animator)
            if grid != last_grid:
                # Clear the block (transparent sixel pixels don't overwrite,
                # so stale pixels must go), return to the top, then draw the
                # image inside save/restore so the cursor lands back on top.
                clear = (region.clear_line() + region.cursor_down(1)) * (rows - 1)
                clear += region.clear_line() + region.cursor_up(rows - 1) + "\r"
                image = sixel.encode(grid, pixel_sprites.PALETTE, PIXEL_SCALE)
                out.write(clear + region.save_cursor() + image + region.restore_cursor())
                out.flush()
                last_grid = grid

            frame += 1
            time.sleep(FRAME_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        # Drop below the pet block and restore the cursor for the prompt.
        out.write(region.cursor_down(rows - 1) + "\r" + region.show_cursor() + "\n")
        out.flush()
    return 0


def run(out=sys.stdout) -> int:
    # In-memory only — never touches the saved pet. Start hunger near the
    # threshold so the demo visibly crosses between sad and happy.
    state = PetState(name="Pixel", hunger=28.0)

    # No live terminal (piped/redirected): the in-place repaint loop would spin
    # forever spewing escape codes. Print one static frame and bail.
    if hasattr(out, "isatty") and not out.isatty():
        behavior.tick(state)  # settle mood so the sprite + status line agree
        animator = Animator()
        for line in renderer.compose_lines(state, animator.current_sprite(state.mood)):
            out.write(line + "\n")
        return 0

    pixels = termcaps.supports_sixel()
    out.write("PeerPet animation demo — the pet's mood follows its stats.\n")
    out.write("Hunger/happiness decay (fast); feed/play/pet reactions loop.\n")
    if not pixels:
        out.write("(no sixel support detected — showing the text mascot)\n")
    out.write("Press Ctrl-C to quit.\n\n")
    out.flush()

    if pixels:
        return _run_sixel(state, out)
    return _run_text(state, out)
