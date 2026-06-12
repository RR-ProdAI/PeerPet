from peerpet.host.pty_host import OutputTracker, pixel_layout


def test_tracker_alt_screen_enter_and_leave():
    t = OutputTracker()
    t.feed(b"hello \x1b[?1049h vim content")
    assert t.alt_active
    t.feed(b"\x1b[?1049l back to shell")
    assert not t.alt_active
    # Leaving the alt screen means the strip may be stale.
    assert t.wants_repaint


def test_tracker_legacy_alt_screen_codes():
    t = OutputTracker()
    t.feed(b"\x1b[?47h")
    assert t.alt_active
    t.feed(b"\x1b[?1047l")
    assert not t.alt_active


def test_tracker_sequence_split_across_chunks():
    t = OutputTracker()
    t.feed(b"output \x1b[?10")
    assert not t.alt_active
    t.feed(b"49h more")
    assert t.alt_active


def test_tracker_clear_screen_requests_repaint():
    for seq in (b"\x1b[2J", b"\x1b[J", b"\x1b[0J", b"\x1b[3J"):
        t = OutputTracker()
        t.feed(b"prompt " + seq)
        assert t.wants_repaint, seq
        assert not t.alt_active


def test_tracker_plain_output_changes_nothing():
    t = OutputTracker()
    t.feed(b"ls -la\r\ntotal 42\r\n\x1b[31mred text\x1b[0m")
    assert not t.alt_active
    assert not t.wants_repaint


def test_pixel_layout_fits_strip():
    grid = ["." * 36] * 38  # the composed sprite+HUD grid shape
    # 4 rows of 20px = 80px budget; 38px grid -> scale 2 (76px), 4 rows used.
    scale, rows, cols = pixel_layout((10, 20), 4, grid)
    assert scale == 2
    assert rows <= 4
    assert cols == -(-36 * 2 // 10)


def test_pixel_layout_never_scales_below_one():
    grid = ["." * 36] * 38
    scale, rows, _ = pixel_layout((10, 20), 1, grid)  # strip too small
    assert scale == 1
    assert rows == 2  # caller guarantees >= MIN_PET_ROWS, so this still fits


def test_pixel_layout_scale_grows_with_strip():
    grid = ["." * 36] * 38
    scale_small, _, _ = pixel_layout((10, 20), 4, grid)
    scale_big, rows_big, _ = pixel_layout((10, 20), 8, grid)
    assert scale_big > scale_small
    assert rows_big <= 8
