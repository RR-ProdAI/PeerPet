from peerpet.memory.local import LocalMemory
from peerpet.pet.state import PetState


def test_load_creates_default(tmp_path):
    mem = LocalMemory(db_path=tmp_path / "t.db")
    state = mem.load("alice")
    assert isinstance(state, PetState)
    mem.close()


def test_save_roundtrip(tmp_path):
    mem = LocalMemory(db_path=tmp_path / "t.db")
    state = mem.load("bob")
    state.name = "Rex"
    state.level = 7
    mem.save("bob", state)
    mem.close()

    mem2 = LocalMemory(db_path=tmp_path / "t.db")
    loaded = mem2.load("bob")
    assert loaded.name == "Rex"
    assert loaded.level == 7
    mem2.close()


def test_users_are_isolated(tmp_path):
    mem = LocalMemory(db_path=tmp_path / "t.db")
    a = mem.load("alice")
    a.name = "Alpha"
    mem.save("alice", a)
    b = mem.load("bob")
    assert b.name != "Alpha"  # per-user, unique
    mem.close()


def test_event_log(tmp_path):
    mem = LocalMemory(db_path=tmp_path / "t.db")
    mem.record_event("alice", "feed", {"src": "test"})
    rows = mem._conn.execute("SELECT kind FROM events WHERE key='alice'").fetchall()
    assert rows[0]["kind"] == "feed"
    mem.close()
