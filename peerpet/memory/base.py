"""The Memory interface — the one persistence seam.

ALL persistence goes through this interface. Never import a concrete backend
(`local.LocalMemory`) outside the `memory` package; depend on `Memory` and let
`get_memory()` pick the backend. Keeping this boundary clean means we can swap
the storage layer (e.g. a different DB) without touching the rest of the pet.

NOTE: this is product persistence only — plain local storage, no LLM, no
external service. Honcho/Hermes are dev-workflow tools, not part of PeerPet.
"""

from __future__ import annotations

import getpass
from abc import ABC, abstractmethod

from peerpet.pet.state import PetState


def current_memory_key() -> str:
    """The per-user identity: lightweight and unique per user (see AGENTS.md).

    This is the OS user — each person gets their own pet, isolated in storage.
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
        powers stats like streaks and play history.
        """

    def close(self) -> None:  # noqa: B027 — optional hook, backends may override
        """Release resources if the backend holds any (no-op by default)."""


def get_memory() -> Memory:
    """Factory: returns the storage backend (local SQLite).

    The single place to branch if we ever add another backend.
    """
    from peerpet.memory.local import LocalMemory

    return LocalMemory()
