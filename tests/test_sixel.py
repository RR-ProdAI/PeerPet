from peerpet.host import sixel

PALETTE = {"R": (255, 0, 0), "G": (0, 255, 0)}


def test_encode_wraps_in_dcs_and_st():
    seq = sixel.encode(["R"], PALETTE)
    assert seq.startswith("\x1bP0;1;0q")
    assert seq.endswith("\x1b\\")


def test_raster_attributes_carry_image_size():
    seq = sixel.encode(["RG", "GR", "RG"], PALETTE)
    assert '"1;1;2;3' in seq


def test_palette_definitions_scaled_to_percent():
    seq = sixel.encode(["RG"], PALETTE)
    # 255 -> 100, 0 -> 0; one definition per used color, indexed from 0.
    assert "#0;2;0;100;0" in seq  # G sorts first
    assert "#1;2;100;0;0" in seq


def test_transparent_pixels_emit_no_color():
    seq = sixel.encode(["."], PALETTE)
    assert "#0" not in seq  # nothing drawn, no palette entry used


def test_single_pixel_sets_bit_zero():
    seq = sixel.encode(["R"], PALETTE)
    # One pixel in the band's top row = sixel value 1 = chr(1 + 63) = "@".
    body = seq.split("q", 1)[1]
    assert "@" in body


def test_scale_multiplies_dimensions():
    seq = sixel.encode(["R"], PALETTE, scale=4)
    assert '"1;1;4;4' in seq


def test_long_runs_are_rle_compressed():
    seq = sixel.encode(["R" * 50], PALETTE)
    assert "!50@" in seq


def test_bands_split_every_six_rows():
    seq = sixel.encode(["R"] * 7, PALETTE)
    # 7 rows = 2 bands; every band (including the last) ends with "-".
    assert seq.split("q", 1)[1].count("-") == 2
