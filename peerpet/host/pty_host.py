"""The PTY host — the heart of PeerPet, and the riskiest module.

⚠️  PAIR ON THIS (see AGENTS.md). A stray escape sequence here corrupts the
user's terminal. Verify behavior in a *throwaway* terminal.

Design:
  1. Save terminal state; put the real terminal in raw mode.
  2. pty.fork() the user's shell as the child, attached to the pty slave.
  3. Reserve `pet_rows` rows for the pet and size the child pty to (rows -
     pet_rows) so the shell never scrolls into the pet. The strip defaults to the
     bottom (`pet_position`): a bottom strip keeps the scroll region's top margin
     at row 1, which preserves the terminal's native scrollback and lets the
     shell's cursor coordinates pass through; a top strip puts the pet top-right
     but disables scrollback and needs the shell re-anchored below the strip.
  4. select() over [real stdin, pty master, ipc socket]:
       - stdin  -> pty master (user input to the shell)
       - master -> stdout     (shell output, scrolls in the shell rows)
       - ipc    -> apply command to the live state, redraw
  5. On a timer, advance the animation and renderer.draw() into the pet row,
     right-aligned.
  6. ALWAYS teardown (region.teardown + restore termios) via try/finally +
     atexit + signal handlers, including on crash.

The scroll region keeps ordinary shell output out of the pet rows. The one thing
it can't stop is an *absolute* screen wipe — `clear` / `reset` / Ctrl-L emit
`ESC[2J` / `ESC c`. We detect those in the shell's output, re-assert the region
(re-anchoring the shell for a top strip), and repaint the pet.

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
import signal
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
from peerpet.pet.animation import Animator

# Sequences that move into / wipe the whole screen (incl. the pet strip).
_CLEAR_SEQUENCES = (b"\x1b[2J", b"\x1b[3J", b"\x1bc")

# Signals that should end the host *cleanly* (reset the terminal). SIGINT is
# normally swallowed by raw mode (Ctrl-C goes to the child shell), so this mainly
# catches `pkill`/SIGTERM, a closed window (SIGHUP), and an explicit `kill -INT`.
# SIGKILL is uncatchable — recover from that with `reset`.
_EXIT_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)


class _Terminated(Exception):
    """Raised from a signal handler to unwind into the host's cleanup path."""


def _raise_terminated(signum, frame):
    raise _Terminated(signum)


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
    animator = Animator()

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

    # Wrap the state handler so a landed command also fires its one-shot
    # animation (feed/play/pet); the next render tick picks up the reaction.
    _apply_command = make_host_handler(state, memory, key)

    def handle_command(command: str, payload: dict) -> dict:
        reply = _apply_command(command, payload)
        if reply.get("ok"):
            animator.trigger(command)
        return reply

    ipc = IpcServer(handle_command)
    ipc_sock = ipc.start()

    rows, cols = _terminal_size(stdin_fd)

    # Where the strip lives. "bottom" (default) keeps the scroll region's top
    # margin at row 1, which on some terminals preserves native scrollback; "top"
    # places the pet top-right but needs re-anchoring after a screen clear.
    position = config.pet_position if config.pet_position in ("top", "bottom") else "bottom"
    if position == "bottom":
        pet_row = rows
        shell_top_row = 1

        def reserve() -> str:
            return region.reserve_bottom(rows, pet_rows)
    else:
        pet_row = 1
        shell_top_row = pet_rows + 1

        def reserve() -> str:
            return region.reserve_top(rows, pet_rows)

    def out(seq: str) -> None:
        os.write(stdout_fd, seq.encode())

    def draw_pet() -> None:
        sprite = animator.current_sprite(state.mood)
        buf = io.StringIO()
        renderer.draw(state, sprite, pet_row, cols, out=buf)
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

    def terminate_child() -> None:
        """Hang up the shell so it exits, then it gets reaped below."""
        try:
            os.kill(pid, signal.SIGHUP)
        except ProcessLookupError:
            pass

    try:
        tty.setraw(stdin_fd)
        # Catch signals so we always reset the terminal (hard-constraint #2).
        for sig in _EXIT_SIGNALS:
            signal.signal(sig, _raise_terminated)
        _set_pty_size(master_fd, rows - pet_rows, cols)
        # TODO(#19): shift existing screen content out of the strip so it's carved
        # cleanly on startup; today the pet overlaps prior content until a clear.
        out(reserve())
        out(region.move_cursor(shell_top_row, 1))  # anchor shell in its area
        draw_pet()
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
                    # A full-screen clear wiped the strip (and, for a top strip,
                    # homed the cursor into it). Re-assert the region, re-anchor
                    # the shell if needed, and repaint the pet.
                    out(reserve())
                    if position == "top":
                        out(region.move_cursor(shell_top_row, 1))
                    draw_pet()

            if stdin_fd in readable:
                data = os.read(stdin_fd, 65536)
                if data:
                    os.write(master_fd, data)

            if ipc_sock in readable:
                conn, _ = ipc_sock.accept()
                ipc.handle_connection(conn)
                draw_pet()  # reflect feed/play/pet immediately

            if time.monotonic() >= next_frame:
                behavior.tick(state)
                draw_pet()
                next_frame = time.monotonic() + interval
    except _Terminated:
        pass  # signal received — fall through to clean teardown
    finally:
        cleanup()
        terminate_child()

    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)
