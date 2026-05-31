import pytest

from peerpet.host import region


def test_set_scroll_region():
    assert region.set_scroll_region(1, 23) == "\x1b[1;23r"


def test_reset_scroll_region():
    assert region.reset_scroll_region() == "\x1b[r"


def test_reserve_top_leaves_pet_rows():
    # 24-row terminal, 1 pet row -> pet on row 1, shell scrolls in rows 2..24
    assert region.reserve_top(24, 1) == "\x1b[2;24r"


def test_reserve_top_multiple_pet_rows():
    # 2 pet rows -> shell scrolls in rows 3..24
    assert region.reserve_top(24, 2) == "\x1b[3;24r"


def test_reserve_bottom_leaves_pet_rows():
    # 24-row terminal, 1 pet row -> shell scrolls in rows 1..23, pet on row 24
    assert region.reserve_bottom(24, 1) == "\x1b[1;23r"


def test_draw_at_wraps_in_save_restore():
    seq = region.draw_at(24, "hi")
    assert seq.startswith(region.save_cursor())
    assert seq.endswith(region.restore_cursor())
    assert region.move_cursor(24, 1) in seq
    assert "hi" in seq


def test_teardown_restores_full_screen():
    seq = region.teardown()
    assert region.reset_scroll_region() in seq


@pytest.mark.parametrize("top,bottom", [(0, 5), (5, 4)])
def test_invalid_region_raises(top, bottom):
    with pytest.raises(ValueError):
        region.set_scroll_region(top, bottom)


def test_reserve_top_validates():
    with pytest.raises(ValueError):
        region.reserve_top(5, 5)  # no room left for the shell


def test_reserve_bottom_validates():
    with pytest.raises(ValueError):
        region.reserve_bottom(5, 5)  # no room left for the shell
