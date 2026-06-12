from peerpet.pet import pixel_sprites, sprites
from peerpet.pet.animation import (
    IDLE_FRAME_INTERVAL,
    REACTION_FRAME_INTERVAL,
    Animator,
)
from peerpet.pet.state import Mood


class FakeClock:
    """Manually advanced clock so animation timing is deterministic."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def test_idle_holds_rest_then_blinks():
    clock = FakeClock()
    anim = Animator(clock=clock)
    rest = anim.current_sprite(Mood.HAPPY)
    # The rest pose is held across the next step (mostly still, not twitchy).
    clock.t += IDLE_FRAME_INTERVAL
    assert anim.current_sprite(Mood.HAPPY) == rest
    # Across a full loop we see the rest pose AND at least one different (blink)
    # frame — so it animates, but only occasionally.
    seen = set()
    for i in range(len(sprites.FRAMES[Mood.HAPPY])):
        clock.t = i * IDLE_FRAME_INTERVAL
        seen.add(anim.current_sprite(Mood.HAPPY))
    assert rest in seen
    assert len(seen) >= 2


def test_trigger_plays_reaction_frames():
    clock = FakeClock()
    anim = Animator(clock=clock)
    anim.trigger("feed")
    assert anim.is_reacting()
    frames = sprites.reaction_frames("feed")
    for i, expected in enumerate(frames):
        clock.t = i * REACTION_FRAME_INTERVAL
        assert anim.current_sprite(Mood.HAPPY) == expected


def test_reaction_expires_back_to_idle():
    clock = FakeClock()
    anim = Animator(clock=clock)
    anim.trigger("feed")
    # Jump past the whole reaction window.
    clock.t = len(sprites.reaction_frames("feed")) * REACTION_FRAME_INTERVAL
    assert not anim.is_reacting()
    sprite = anim.current_sprite(Mood.SAD)
    assert sprite in sprites.FRAMES[Mood.SAD]


def test_unknown_command_does_not_react():
    anim = Animator(clock=FakeClock())
    anim.trigger("explode")
    assert not anim.is_reacting()
    assert anim.current_sprite(Mood.CONTENT) in sprites.FRAMES[Mood.CONTENT]


def test_animator_drives_pixel_sprite_library():
    # Same timing engine, different sprite format: frames come from the
    # injected library, not the default text art.
    clock = FakeClock()
    anim = Animator(clock=clock, library=pixel_sprites)
    assert anim.current_sprite(Mood.HAPPY) in pixel_sprites.FRAMES[Mood.HAPPY]
    anim.trigger("feed")
    assert anim.current_sprite(Mood.HAPPY) == pixel_sprites.reaction_frames("feed")[0]
    clock.t = len(pixel_sprites.reaction_frames("feed")) * REACTION_FRAME_INTERVAL
    assert not anim.is_reacting()
    assert anim.current_sprite(Mood.SAD) in pixel_sprites.FRAMES[Mood.SAD]
