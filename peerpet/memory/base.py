"""The Memory interface — the one seam we must not let leak.

ALL persistence goes through this interface. Never import a concrete backend
(`local.LocalMemory`, future `honcho_backend`) outside the `memory` package;
depend on `Memory` and let `get_memory()` pick the backend. This is what makes
the Honcho upgrade a drop-in: the per-user `memory_key` maps 1:1 to a Honcho
peer.
"""

from __future__ import annotations

import getpass
from abc import ABC, abstractmethod

from peerpet.pet.state import PetState


def current_memory_key() -> str:
    """The per-user identity. Lightweight and unique per user (see AGENTS.md).

    Today this is the OS user. When the Honcho backend lands, this same string
    becomes the Honcho peer id — no other code needs to change.
    """
    return getpass.getuser()


class Memory(ABC):
    """Persistence boundary for a single user's pet."""

    @abstractmethod
    def load(self, key: str) -> PetState:
        """Return the user's pet, creating a fresh default one if none exists."""

    @abstractmethod
    def save(self, key: str, state: PetState) -> None:
        """Persist the user's pet."""

    @abstractmethod
    def record_event(self, key: str, kind: str, payload: dict | None = None) -> None:
        """Append an interaction event (feed/play/...). Cheap append-only log;
        later powers stats and feeds the Honcho memory backend.
        """

    def close(self) -> None:  # noqa: B027 — optional hook, backends may override
        """Release resources if the backend holds any (no-op by default)."""


def get_memory() -> Memory:
    """Factory: returns the configured backend.

    MVP always returns the local SQLite backend. When Honcho is enabled via
    config, this is the single place that will branch.
    """
    from peerpet.memory.local import LocalMemory

    return LocalMemory()
