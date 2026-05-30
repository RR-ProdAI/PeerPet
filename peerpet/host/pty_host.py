"""The PTY host — the heart of PeerPet, and the riskiest module.

⚠️  PAIR ON THIS (see AGENTS.md). A stray escape sequence here corrupts the
user's terminal. Verify behavior in a *throwaway* terminal.

Design:
  1. Save terminal state; put the real terminal in raw mode.
  2. pty.fork() the user's shell as the child, attached to the pty slave.
  3. Reserve the top `pet_rows` rows (region.reserve_top) and size the child pty
     to (rows - pet_rows) so the shell never scrolls into the pet. Anchor the
     shell's cursor below the strip.
  4. select() over [real stdin, pty master, ipc socket]:
       - stdin  -> pty master (user input to the shell)
       - master -> stdout     (shell output, scrolls below the strip)
       - ipc    -> apply command to the live state, redraw
  5. On a timer, advance the animation and renderer.draw() into the pet row,
     right-aligned (top-right).
  6. ALWAYS teardown (region.teardown + restore termios) via try/finally +
     atexit, including on crash.

The scroll region keeps ordinary shell output out of the pet rows. The one thing
it can't stop is an *absolute* move into row 1 — `clear` / `reset` / Ctrl-L emit
`ESC[2J` / `ESC[H` / `ESC c`. We detect those in the shell's output and re-anchor
the cursor below the strip, then repaint the pet.

Not yet handled here (separate issues): SIGWINCH resize (#11) and pausing while
the shell is on the alternate screen — vim/htop (#12).
"""

from __future__ import annotations

import atexit
import errno
import fcntl
import io
import os
import pty
import select
import struct
import termios
import time
import tty

from peerpet.config import Config
from peerpet.host import region, renderer
from peerpet.interaction.commands import make_host_handler
from peerpet.interaction.ipc import IpcServer
from peerpet.memory.base import current_memory_key, get_memory
from peerpet.pet import behavior

# Sequences that move into / wipe the whole screen (incl. the pet strip).
_CLEAR_SEQUENCES = (b"\x1b[2J", b"\x1b[3J", b"\x1bc")
PET_ROW = 1  # the pet lives on the first reserved row


def _terminal_size(fd: int) -> tuple[int, int]:
    try:
        size = os.get_terminal_size(fd)
        return size.lines, size.columns
    except OSError:
        return 24, 80


def _set_pty_size(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def run(config: Config | None = None) -> int:
    """Launch the wrapped shell with the pet. Returns the child's exit code."""
    config = config or Config.load()

    stdin_fd = 0
    stdout_fd = 1
    if not os.isatty(stdin_fd):
        raise SystemExit("peerpet run: not a terminal (need an interactive TTY)")

    memory = get_memory()
    key = current_memory_key()
    state = memory.load(key)
    behavior.tick(state)  # settle stats to "now" before we start drawing

    pet_rows = config.pet_rows
    interval = config.tick_interval

    pid, master_fd = pty.fork()
    if pid == 0:
        # Child: become the user's shell. On success this never returns.
        shell = config.resolved_shell
        os.execvp(shell, [os.path.basename(shell)])
        os._exit(127)  # exec failed

    # --- Parent: the host ---
    old_termios = termios.tcgetattr(stdin_fd)
    ipc = IpcServer(make_host_handler(state, memory, key))
    ipc_sock = ipc.start()

    rows, cols = _terminal_size(stdin_fd)

    def out(seq: str) -> None:
        os.write(stdout_fd, seq.encode())

    def draw_pet(tick: int) -> None:
        buf = io.StringIO()
        renderer.draw(state, tick, PET_ROW, cols, out=buf)
        out(buf.getvalue())

    _cleaned = False

    def cleanup() -> None:
        nonlocal _cleaned
        if _cleaned:
            return
        _cleaned = True
        try:
            out(region.teardown())
        except OSError:
            pass
        try:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_termios)
        except (termios.error, OSError):
            pass
        ipc.close()
        try:
            memory.save(key, state)
        finally:
            memory.close()

    atexit.register(cleanup)

    tick = 0
    try:
        tty.setraw(stdin_fd)
        _set_pty_size(master_fd, rows - pet_rows, cols)
        # TODO(#19): shift existing screen content down by pet_rows so the strip
        # is carved cleanly on startup; today the pet overlaps prior content
        # until the first clear.
        out(region.reserve_top(rows, pet_rows))
        out(region.move_cursor(pet_rows + 1, 1))  # anchor shell below the strip
        draw_pet(tick)
        next_frame = time.monotonic() + interval

        while True:
            timeout = max(0.0, next_frame - time.monotonic())
            try:
                readable, _, _ = select.select([stdin_fd, master_fd, ipc_sock], [], [], timeout)
            except OSError as e:
                if e.errno == errno.EINTR:
                    continue
                raise

            if master_fd in readable:
                try:
                    data = os.read(master_fd, 65536)
                except OSError:
                    data = b""
                if not data:
                    break  # shell exited
                os.write(stdout_fd, data)
                if any(seq in data for seq in _CLEAR_SEQUENCES):
                    # A full-screen clear wiped the strip and homed into it;
                    # put the shell back below the strip and repaint the pet.
                    out(region.reserve_top(rows, pet_rows))
                    out(region.move_cursor(pet_rows + 1, 1))
                    draw_pet(tick)

            if stdin_fd in readable:
                data = os.read(stdin_fd, 65536)
                if data:
                    os.write(master_fd, data)

            if ipc_sock in readable:
                conn, _ = ipc_sock.accept()
                ipc.handle_connection(conn)
                draw_pet(tick)  # reflect feed/play/pet immediately

            if time.monotonic() >= next_frame:
                tick += 1
                behavior.tick(state)
                draw_pet(tick)
                next_frame = time.monotonic() + interval
    finally:
        cleanup()

    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)
