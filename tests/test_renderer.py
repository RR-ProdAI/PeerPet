import io

from peerpet.host import region, renderer
from peerpet.pet import sprites
from peerpet.pet.state import Mood, PetState


def test_display_width_counts_wide_chars():
    assert renderer.display_width("ab") == 2
    assert renderer.display_width("（）") == 4  # full-width parens are 2 cols each
    # combining marks add no width
    assert renderer.display_width("é") == 1


def test_right_aligned_col_flushes_right():
    # "hi" (width 2) in an 80-col terminal ends at col 80 -> starts at col 79
    assert renderer.right_aligned_col("hi", 80) == 79


def test_right_aligned_col_never_negative():
    # text wider than the terminal clamps to col 1
    assert renderer.right_aligned_col("x" * 200, 80) == 1


def test_compose_mentions_name_and_mood():
    state = PetState(name="Rex", mood=Mood.HAPPY)
    sprite = sprites.frame_for(state.mood, 0)
    line = renderer.compose(state, sprite)
    assert "Rex" in line
    assert "happy" in line


def test_draw_wraps_in_save_restore_and_targets_row():
    state = PetState(name="Rex")
    sprite = sprites.frame_for(state.mood, 0)
    buf = io.StringIO()
    renderer.draw(state, sprite, row=1, cols=80, out=buf)
    seq = buf.getvalue()
    assert seq.startswith(region.save_cursor())
    assert seq.endswith(region.restore_cursor())
    assert "Rex" in seq
