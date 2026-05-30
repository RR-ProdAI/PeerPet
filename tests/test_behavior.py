import time

from peerpet.pet import behavior
from peerpet.pet.state import Mood, PetState


def test_tick_decays_stats_over_time():
    now = time.time()
    state = PetState(hunger=100, energy=100, happiness=100, last_seen=now - 3600)
    behavior.tick(state, now=now)
    assert state.hunger < 100
    assert state.energy < 100
    assert state.happiness < 100
    assert state.last_seen == now


def test_feed_increases_hunger():
    state = PetState(hunger=10)
    behavior.apply_command(state, "feed")
    assert state.hunger > 10


def test_play_trades_energy_for_happiness():
    state = PetState(happiness=10, energy=80)
    behavior.apply_command(state, "play")
    assert state.happiness > 10
    assert state.energy < 80


def test_xp_levels_up():
    state = PetState(xp=behavior.XP_PER_LEVEL - 1, level=1)
    behavior.apply_command(state, "pet")
    assert state.level == 2


def test_low_hunger_makes_pet_hungry():
    state = PetState(hunger=5, energy=80, happiness=80)
    behavior.tick(state)
    assert state.mood == Mood.HUNGRY


def test_unknown_command_raises():
    import pytest

    with pytest.raises(ValueError):
        behavior.apply_command(PetState(), "explode")
