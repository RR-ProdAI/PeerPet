"""Terminal capability detection: does this terminal draw sixel pixels?

Queries go to the controlling tty (`/dev/tty`), not stdout, so they work even
when output is wrapped. Every probe is best-effort with a short timeout — on
any failure (no tty, no reply, weird reply) we report "no sixel" and callers
fall back to the Unicode-art pet. Nothing here may hang or raise.

    DA1  (`CSI c`)   -> `CSI ? <attr> ; ... c`; attribute 4 = sixel support.
    XTWINOPS 16      -> `CSI 6 ; <cell_h> ; <cell_w> t`; cell size in pixels.

`PEERPET_SIXEL=always|never` overrides detection (useful for testing and for
terminals that lie about their capabilities).
"""

from __future__ import annotations

import os
import re
import select

_REPLY_TIMEOUT = 0.3
_REPLY_LIMIT = 64  # longest sane reply; guards against a chatty tty
FALLBACK_CELL = (10, 20)  # (width, height) px — typical monospace cell


def _query(payload: str, terminator: str) -> str | None:
    """Write `payload` to the controlling tty in raw mode and read the reply up
    to `terminator`. None on any failure or timeout."""
    try:
        import termios
        import tty as tty_mod

        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        return None
    try:
        old = termios.tcgetattr(fd)
    except termios.error:
        os.close(fd)
        return None
    try:
        tty_mod.setraw(fd)
        os.write(fd, payload.encode())
        reply = ""
        while len(reply) < _REPLY_LIMIT:
            ready, _, _ = select.select([fd], [], [], _REPLY_TIMEOUT)
            if not ready:
                return None
            reply += os.read(fd, 1).decode("ascii", errors="replace")
            if reply.endswith(terminator):
                return reply
        return None
    except OSError:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        os.close(fd)


def supports_sixel() -> bool:
    """True if the terminal advertises sixel graphics (DA1 attribute 4)."""
    override = os.environ.get("PEERPET_SIXEL", "").lower()
    if override in ("always", "1"):
        return True
    if override in ("never", "0"):
        return False
    reply = _query("\x1b[c", "c")
    if not reply:
        return False
    match = re.search(r"\[\?([\d;]+)c", reply)
    return match is not None and "4" in match.group(1).split(";")


def cell_pixel_size() -> tuple[int, int]:
    """(width, height) of one character cell in pixels, for converting image
    sizes into row/column counts. Falls back to a typical cell on silence."""
    reply = _query("\x1b[16t", "t")
    if reply:
        match = re.search(r"\[6;(\d+);(\d+)t", reply)
        if match:
            height, width = int(match.group(1)), int(match.group(2))
            if width > 0 and height > 0:
                return (width, height)
    return FALLBACK_CELL
