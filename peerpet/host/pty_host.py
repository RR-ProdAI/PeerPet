"""The PTY host — the heart of PeerPet, and the riskiest module.

⚠️  PAIR ON THIS (see AGENTS.md). A stray escape sequence here corrupts the
user's terminal.

How it works (matches ARCHITECTURE.md):
  1. Probe capabilities (sixel? cell size?) while the tty is still quiet, then
     put the real terminal in raw mode and fork the user's shell onto a PTY.
  2. Reserve the bottom `pet_rows` rows (DECSTBM via region.reserve_bottom) and
     size the child PTY to (rows - pet_rows): the shell scrolls only above the
     strip, and its cursor addressing maps 1:1 to real rows — no translation.
  3. select() over [real stdin, pty master, ipc socket]:
       stdin  -> pty master (user input to the shell)
       master -> stdout     (shell output; watched for alt-screen + clears)
       ipc    -> apply feed/play/pet, trigger the reaction animation
  4. On the tick timer: decay the pet, pick the frame, and redraw the strip —
     but only when the image actually changed (no flicker, no idle traffic).
  5. SIGWINCH -> recompute rows, re-reserve the region, resize the child.
  6. ALWAYS tear down (restore termios, reset region, wipe the strip, save the
     pet) via try/finally + atexit + SIGTERM, including on crash.

Known sharp edges, accepted for the MVP:
  - The pet draw wraps in DECSC/DECRC (one slot): a shell that keeps its own
    saved cursor across a pet frame will have it clobbered (same trade-off as
    region.draw_at). Full cursor bookkeeping needs a terminal emulator — out
    of scope (see ARCHITECTURE "not a terminal multiplexer").
  - Erase-below (`CSI J`) from fancy prompts wipes the strip; the tracker
    flags it and the pet repaints on the next tick (≤ tick_interval late).
"""

from __future__ import annotations

import atexit
import fcntl
import os
import pty
import re
import select
import signal
import struct
import sys
import termios
import time
import tty

from peerpet.config import Config
from peerpet.host import region, renderer, sixel, termcaps
from peerpet.interaction.commands import make_handler
from peerpet.interaction.ipc import IpcServer
from peerpet.memory.base import current_memory_key, get_memory
from peerpet.pet import behavior, pixel_sprites, sprites
from peerpet.pet.animation import Animator

# Persist the pet this often (commands also persist immediately via the IPC
# handler); the teardown saves a final time.
SAVE_INTERVAL = 30.0
# Minimum strip height: the pixel pet needs ~2 rows at scale 1; 4 gives scale 2
# on a typical 20px cell. The text mascot needs 3 sprite rows + a status line.
MIN_PET_ROWS = 4
# Below this many total rows the strip is suspended (shell gets everything).
MIN_TOTAL_ROWS = MIN_PET_ROWS + 6


class OutputTracker:
    """Watch the child's output stream for sequences the host must react to:
    alternate-screen enter/leave (DECSET/DECRST 1049/1047/47 — pause the pet so
    we never fight vim/htop) and erase-to-end-of-screen / clear-screen (CSI
    0J/2J/3J — these wipe the strip, so the pet must repaint).

    A few bytes of tail are kept so sequences split across read() chunks still
    match; a sequence inside the tail may be seen twice, which is harmless
    because both flags are idempotent.
    """

    _EVENTS = re.compile(rb"\x1b\[\?(?:1049|1047|47)[hl]|\x1b\[[023]?J")
    _TAIL = 12  # longest matchable sequence is 10 bytes

    def __init__(self) -> None:
        self.alt_active = False
        self.wants_repaint = False
        self._tail = b""

    def feed(self, data: bytes) -> None:
        buf = self._tail + data
        for match in self._EVENTS.finditer(buf):
            seq = match.group()
            if seq.endswith((b"h", b"l")):
                was_active = self.alt_active
                self.alt_active = seq.endswith(b"h")
                if was_active and not self.alt_active:
                    self.wants_repaint = True  # back from vim: strip is stale
            else:
                self.wants_repaint = True
        self._tail = buf[-self._TAIL :]


def pixel_layout(cell: tuple[int, int], pet_rows: int, grid: list[str]) -> tuple[int, int, int]:
    """Pick the largest integer scale whose image fits inside the strip, so a
    sixel draw can never overflow the bottom of the screen (which would scroll).

    Returns (scale, image_rows, image_cols) — the terminal rows/cols the scaled
    image occupies. scale is at least 1; callers guarantee the strip is tall
    enough for scale 1 via MIN_PET_ROWS.
    """
    cell_w, cell_h = cell
    grid_h, grid_w = len(grid), len(grid[0])
    scale = max(1, (pet_rows * cell_h) // grid_h)
    image_rows = -(-grid_h * scale // cell_h)
    image_cols = -(-grid_w * scale // cell_w)
    return scale, image_rows, image_cols


def _set_child_winsize(master_fd: int, rows: int, cols: int) -> None:
    """Resize the child PTY (the kernel delivers SIGWINCH to the shell)."""
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _wipe_strip(top_row: int, pet_rows: int) -> str:
    """Clear every row of the strip (transparent sixel pixels don't overwrite,
    so stale pixels must be erased before a redraw)."""
    return "".join(
        region.move_cursor(top_row + i, 1) + region.clear_line() for i in range(pet_rows)
    )


def run(config: Config | None = None) -> int:
    """Launch the wrapped shell with the pet. Returns the shell's exit code."""
    if os.environ.get("PEERPET_HOSTED"):
        print("peerpet: refusing to nest — this shell is already hosted", file=sys.stderr)
        return 1
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("peerpet run: needs a real terminal", file=sys.stderr)
        return 1

    config = config or Config.load()
    memory = get_memory()
    key = current_memory_key()
    state = behavior.tick(memory.load(key))

    # Probe the terminal BEFORE raw mode / fork, while replies are clean.
    pixels = termcaps.supports_sixel()
    cell = termcaps.cell_pixel_size()
    pet_rows = max(config.pet_rows, MIN_PET_ROWS)
    if pixels:
        animator = Animator(library=pixel_sprites)
        sample = renderer.compose_pixel(state, animator.current_sprite(state.mood))
        scale, _, image_cols = pixel_layout(cell, pet_rows, sample)
    else:
        animator = Animator(library=sprites)
        scale = image_cols = 0  # unused on the text path

    # IPC: the stock handler persists the command; the wrapper queues it so the
    # host loop can trigger the matching reaction animation.
    pending: list[str] = []
    base_handler = make_handler(memory)

    def handler(command: str, payload: dict) -> dict:
        reply = base_handler(command, payload)
        if reply.get("ok"):
            pending.append(command)
        return reply

    ipc = IpcServer(handler)
    ipc_sock = ipc.start()

    stdin_fd = sys.stdin.fileno()
    stdout_fd = sys.stdout.fileno()
    size = os.get_terminal_size(stdout_fd)
    rows, cols = size.lines, size.columns

    shell = config.resolved_shell
    pid, master = pty.fork()
    if pid == 0:  # child: become the user's shell
        os.environ["PEERPET_HOSTED"] = "1"
        try:
            os.execvp(shell, [shell])
        except OSError:
            os._exit(127)

    old_attrs = termios.tcgetattr(stdin_fd)
    tracker = OutputTracker()
    strip_active = False
    cleaned = False

    def cleanup() -> None:
        """Idempotent: runs from finally, atexit, and SIGTERM."""
        nonlocal cleaned
        if cleaned:
            return
        cleaned = True
        try:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_attrs)
        except termios.error:
            pass
        out = region.teardown() + region.show_cursor()
        if strip_active:
            out += _wipe_strip(rows - pet_rows + 1, pet_rows)
            out += region.move_cursor(max(1, rows - pet_rows), 1) + "\r\n"
        try:
            os.write(stdout_fd, out.encode())
        except OSError:
            pass
        ipc.close()
        memory.save(key, state)
        memory.close()

    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    resized = [True]  # start dirty: first pass sets up the region + child size
    signal.signal(signal.SIGWINCH, lambda *_: resized.__setitem__(0, True))

    last_image: str | None = None
    next_save = time.monotonic() + SAVE_INTERVAL
    exit_code = 0
    try:
        tty.setraw(stdin_fd)
        while True:
            if resized[0]:
                resized[0] = False
                size = os.get_terminal_size(stdout_fd)
                rows, cols = size.lines, size.columns
                if rows >= MIN_TOTAL_ROWS:
                    strip_active = True
                    _set_child_winsize(master, rows - pet_rows, cols)
                    os.write(stdout_fd, region.reserve_bottom(rows, pet_rows).encode())
                else:  # too short for a strip: give the shell everything
                    strip_active = False
                    _set_child_winsize(master, rows, cols)
                    os.write(stdout_fd, region.reset_scroll_region().encode())
                last_image = None  # force a repaint at the new geometry

            readable, _, _ = select.select([stdin_fd, master, ipc_sock], [], [], 0.1)

            if stdin_fd in readable:
                data = os.read(stdin_fd, 65536)
                if data:
                    os.write(master, data)
            if master in readable:
                try:
                    data = os.read(master, 65536)
                except OSError:  # EIO: the shell exited
                    break
                if not data:
                    break
                tracker.feed(data)
                os.write(stdout_fd, data)
            if ipc_sock in readable:
                conn, _ = ipc_sock.accept()
                ipc.handle_connection(conn)
                if pending:
                    # The handler persisted the authoritative state; adopt it.
                    state = memory.load(key)
                while pending:
                    animator.trigger(pending.pop(0))

            behavior.tick(state)
            if tracker.wants_repaint:
                tracker.wants_repaint = False
                last_image = None
            if strip_active and not tracker.alt_active:
                top = rows - pet_rows + 1
                frame = animator.current_sprite(state.mood)
                if pixels:
                    grid = renderer.compose_pixel(state, frame)
                    col = max(1, cols - image_cols)
                    image = region.move_cursor(top, col) + sixel.encode(
                        grid, pixel_sprites.PALETTE, scale
                    )
                else:
                    lines = renderer.compose_lines(state, frame)[:pet_rows]
                    width = max(len(line) for line in lines)
                    col = max(1, cols - width)
                    image = "".join(
                        region.move_cursor(top + i, col) + line for i, line in enumerate(lines)
                    )
                if image != last_image:
                    draw = region.save_cursor() + _wipe_strip(top, pet_rows)
                    draw += image + region.restore_cursor()
                    os.write(stdout_fd, draw.encode())
                    last_image = image

            now = time.monotonic()
            if now >= next_save:
                memory.save(key, state)
                next_save = now + SAVE_INTERVAL

        _, status = os.waitpid(pid, 0)
        code = os.waitstatus_to_exitcode(status)
        exit_code = code if code >= 0 else 128 - code  # signal -> shell-style code
    finally:
        cleanup()
    return exit_code
