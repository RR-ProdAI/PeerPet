"""Local SQLite memory backend — the MVP.

Lightweight, per-user, no network. One database under the XDG data dir. Stores
the current pet state as JSON plus an append-only event log.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from peerpet.memory.base import Memory
from peerpet.pet.state import PetState


def default_data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / "peerpet"


class LocalMemory(Memory):
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            data_dir = default_data_dir()
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "peerpet.db"
        self.db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pets (
                key   TEXT PRIMARY KEY,
                state TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                key     TEXT NOT NULL,
                ts      REAL NOT NULL,
                kind    TEXT NOT NULL,
                payload TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_key ON events(key);
            """
        )
        self._conn.commit()

    def load(self, key: str) -> PetState:
        row = self._conn.execute("SELECT state FROM pets WHERE key = ?", (key,)).fetchone()
        if row is None:
            state = PetState()
            self.save(key, state)
            return state
        return PetState.from_dict(json.loads(row["state"]))

    def save(self, key: str, state: PetState) -> None:
        self._conn.execute(
            "INSERT INTO pets(key, state) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET state = excluded.state",
            (key, json.dumps(state.to_dict())),
        )
        self._conn.commit()

    def record_event(self, key: str, kind: str, payload: dict | None = None) -> None:
        self._conn.execute(
            "INSERT INTO events(key, ts, kind, payload) VALUES(?, ?, ?, ?)",
            (key, time.time(), kind, json.dumps(payload) if payload else None),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
