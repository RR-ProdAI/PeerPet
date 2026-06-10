from peerpet.interaction.commands import make_handler, make_host_handler
from peerpet.memory.local import LocalMemory
from peerpet.pet.state import PetState


def test_host_handler_mutates_live_state(tmp_path):
    """The host owns one PetState; the handler must mutate *that* object so the
    next render reflects the command (not a fresh copy from storage)."""
    mem = LocalMemory(db_path=tmp_path / "t.db")
    state = mem.load("alice")
    state.hunger = 40.0
    handler = make_host_handler(state, mem, key="alice")

    reply = handler("feed", {})

    assert reply["ok"] is True
    assert state.hunger > 40.0  # the *same* object was changed
    assert reply["state"]["hunger"] == state.hunger  # reply reflects the live object
    mem.close()


def test_host_handler_persists(tmp_path):
    mem = LocalMemory(db_path=tmp_path / "t.db")
    state = mem.load("bob")
    handler = make_host_handler(state, mem, key="bob")
    handler("play", {})

    reloaded = mem.load("bob")
    assert reloaded.happiness == state.happiness  # saved through
    mem.close()


def test_host_handler_rejects_unknown(tmp_path):
    mem = LocalMemory(db_path=tmp_path / "t.db")
    handler = make_host_handler(PetState(), mem, key="x")
    reply = handler("explode", {})
    assert reply["ok"] is False
    assert "explode" in reply["error"]
    mem.close()


def test_stateless_handler_still_works(tmp_path):
    mem = LocalMemory(db_path=tmp_path / "t.db")
    reply = make_handler(mem)("feed", {"key": "carol"})
    assert reply["ok"] is True
    mem.close()
