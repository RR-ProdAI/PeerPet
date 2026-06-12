from peerpet.pet import pixel_sprites as px
from peerpet.pet.state import Mood


def _all_frames():
    for frames in px.FRAMES.values():
        yield from frames
    for frames in px.REACTIONS.values():
        yield from frames


def test_every_frame_is_standard_size():
    # The no-jitter rule: every frame of every mood/reaction is WIDTH x HEIGHT.
    for frame in _all_frames():
        assert len(frame) == px.HEIGHT
        assert all(len(row) == px.WIDTH for row in frame)


def test_every_pixel_key_is_in_palette():
    for frame in _all_frames():
        for row in frame:
            for key in row:
                assert key == "." or key in px.PALETTE


def test_idle_loop_is_mostly_still_with_motion():
    for mood in (Mood.HAPPY, Mood.SAD):
        frames = px.FRAMES[mood]
        rest = frames[0]
        # Mostly the rest pose, but at least a bob and a blink appear.
        assert frames.count(rest) >= len(frames) // 3
        assert len({tuple(f) for f in frames}) >= 3


def test_moods_look_different():
    assert px.FRAMES[Mood.HAPPY][0] != px.FRAMES[Mood.SAD][0]


def test_reaction_frames_contract():
    for command in ("feed", "play", "pet"):
        assert px.reaction_frames(command), command
    assert px.reaction_frames("explode") == []


def test_frame_for_wraps_ticks():
    frames = px.FRAMES[Mood.HAPPY]
    assert px.frame_for(Mood.HAPPY, 0) == frames[0]
    assert px.frame_for(Mood.HAPPY, len(frames)) == frames[0]


def test_hud_shape_and_fill_scales_with_stats():
    full = px.hud(100, 100)
    empty = px.hud(0, 0)
    assert len(full) == len(empty)
    assert all(len(row) == px.WIDTH for row in full + empty)
    # A full bar carries more colored fill than an empty one, which is all "D".
    assert sum(row.count("R") for row in full) > sum(row.count("R") for row in empty)
    assert any("D" in row for row in empty)


def test_hud_clamps_out_of_range_values():
    assert px.hud(-50, 0) == px.hud(0, 0)
    assert px.hud(150, 100) == px.hud(100, 100)
