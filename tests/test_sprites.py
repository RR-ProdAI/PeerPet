"""Guards for the sprite art's fixed-size contract (see sprites.py).

Every frame of every mood and every reaction must be the same number of rows,
and every row the same display width — otherwise the pet jumps/jitters as it
animates (and, when right-aligned in the host strip, shifts column to column).
"""

from peerpet.host.renderer import display_width
from peerpet.pet import sprites


def _all_frames():
    """Every animation frame the pet can ever show: idle loops + reactions."""
    for frames in sprites.FRAMES.values():
        yield from frames
    for frames in sprites.REACTIONS.values():
        yield from frames


def test_every_frame_is_uniform_size():
    widths = set()
    heights = set()
    for frame in _all_frames():
        rows = frame.split("\n")
        heights.add(len(rows))
        row_widths = {display_width(r) for r in rows}
        assert len(row_widths) == 1, f"rows differ in width in frame:\n{frame}"
        widths |= row_widths

    # All frames everywhere share one width and one height, so nothing shifts.
    assert len(widths) == 1, f"frames have varying widths: {sorted(widths)}"
    assert len(heights) == 1, f"frames have varying heights: {sorted(heights)}"
