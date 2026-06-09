"""`peerpet demo` — a safe, standalone animation preview.

This drives the animation engine in the *current* terminal **without** the PTY
host: no DECSTBM scroll region, no raw-mode stdin, no forked shell. The pet is a
few rows tall, so each frame repaints that block in place (move the cursor back
up, clear + rewrite each row). The only escape codes used are the cursor
move/hide/show + clear-line builders from `host.region`.

It is non-interactive on purpose (the pet's expression follows its mood, which
follows its stats). To make moods actually change within seconds, the demo runs
on an *accelerated* clock — each frame simulates a chunk of pet-time — and fires
scripted feed/play/pet commands so you can watch the one-shot reactions resolve
back into the idle mood animation. Ctrl-C exits and leaves the terminal clean.
"""

from __future__ import annotations

import sys
import time

from peerpet.host import region, renderer
from peerpet.pet import behavior
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


def _paint(out, lines: list[str], first: bool) -> None:
    """Repaint the pet block in place. On every frame after the first, step the
    cursor back up to the top of the block, then clear+rewrite each row, leaving
    the cursor parked back at the top for the next frame."""
    if not first:
        out.write(region.cursor_up(len(lines) - 1))
    parts = []
    for i, ln in enumerate(lines):
        parts.append("\r" + region.clear_line() + ln)
        if i != len(lines) - 1:
            parts.append("\n")
    out.write("".join(parts))
    out.flush()


def run(out=sys.stdout) -> int:
    # In-memory only — never touches the saved pet. Start hunger near the
    # threshold so the demo visibly crosses between sad and happy.
    state = PetState(name="Pixel", hunger=28.0)
    animator = Animator()

    # No live terminal (piped/redirected): the in-place repaint loop would spin
    # forever spewing escape codes. Print one static frame and bail.
    if hasattr(out, "isatty") and not out.isatty():
        behavior.tick(state)  # settle mood so the sprite + status line agree
        for line in renderer.compose_lines(state, animator.current_sprite(state.mood)):
            out.write(line + "\n")
        return 0

    out.write("PeerPet animation demo — the pet's mood follows its stats.\n")
    out.write("Hunger/happiness decay (fast); feed/play/pet reactions loop.\n")
    out.write("Press Ctrl-C to quit.\n\n")
    out.flush()

    frame = 0
    try:
        # Hide the cursor *inside* the try so the finally always restores it,
        # even if a signal lands between here and the loop.
        out.write(region.hide_cursor())
        out.flush()
        while True:
            _advance(state, SIM_HOURS_PER_FRAME)

            if frame and frame % COMMAND_EVERY == 0:
                # -1 so the first command fired (at frame == COMMAND_EVERY) is
                # SCRIPT[0] = "feed", then play, then pet, repeating.
                command = SCRIPT[(frame // COMMAND_EVERY - 1) % len(SCRIPT)]
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
