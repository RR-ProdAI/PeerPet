"""The PTY host — the heart of PeerPet, and the riskiest module.

⚠️  PAIR ON THIS (see AGENTS.md). A stray escape sequence here corrupts the
user's terminal. This file is an intentional skeleton: the control flow and the
exit-safety scaffolding are in place; the core relay loop is marked TODO.

Design:
  1. Save terminal state; put the real terminal in raw mode.
  2. openpty(); fork the user's shell as the child, attached to the pty slave.
  3. Reserve the bottom `pet_rows` rows (region.reserve_bottom) and size the
     child pty to (rows - pet_rows) so the shell never scrolls into the pet.
  4. select() over [real stdin, pty master, ipc socket]:
       - stdin  -> pty master (user input to the shell)
       - master -> stdout     (shell output, scrolls in the top region)
       - ipc    -> apply command, mark pet dirty
  5. On a timer, advance the animation and renderer.draw() into the pet rows.
  6. SIGWINCH -> recompute rows, re-reserve region, resize child pty.
  7. ALWAYS teardown (region.teardown + restore termios) via try/finally +
     atexit + signal handlers, including on crash.

Implementation notes for whoever builds this:
  - Use os.openpty(), os.fork(), os.setsid(), os.dup2() for the child; or
    `pty.fork()` for a simpler start.
  - termios + tty.setraw() on the real stdin; restore with tcsetattr in finally.
  - Child pty size via fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize_struct).
  - Pause pet drawing while the shell is on the ALTERNATE screen buffer
    (detect DECSET 1049 in the shell's output stream) so we don't fight vim/htop.
"""

from __future__ import annotations

import atexit
import signal
import sys

from peerpet.config import Config
from peerpet.host import region
from peerpet.interaction.commands import make_handler
from peerpet.interaction.ipc import IpcServer
from peerpet.memory.base import current_memory_key, get_memory


def run(config: Config | None = None) -> int:
    """Launch the wrapped shell with the pet. Returns the child's exit code.

    TODO(host pair): implement the select relay loop + animation timer described
    in the module docstring. The scaffolding below establishes exit-safety so
    that no matter how the loop is built, the terminal is left clean.
    """
    config = config or Config.load()
    memory = get_memory()
    key = current_memory_key()
    state = memory.load(key)

    ipc = IpcServer(make_handler(memory))

    def cleanup() -> None:
        sys.stdout.write(region.teardown())
        sys.stdout.flush()
        ipc.close()
        memory.save(key, state)
        memory.close()

    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    raise NotImplementedError(
        "pty_host.run() relay loop not implemented yet — see module docstring. "
        "This is the host-pair's task; cleanup scaffolding is already wired."
    )
