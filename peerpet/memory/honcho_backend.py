"""Honcho memory backend — PLANNED, not part of the MVP.

This is the "cool feature later". It implements the same `Memory` interface as
`local.LocalMemory`, mapping each per-user `memory_key` to a Honcho *peer*. Pet
state is mirrored to Honcho so the pet can build a longer-term, personalized
representation of its owner (and, later, optionally drive personality).

Requires the `honcho` extra (`pip install -e ".[honcho]"`) and an API key /
self-hosted Honcho instance. Enable via config `use_honcho = true`; the only
wiring point is `memory.base.get_memory()`.

Left as a stub on purpose so the MVP needs no keys and no network.
"""

from __future__ import annotations

from peerpet.memory.base import Memory
from peerpet.pet.state import PetState


class HonchoMemory(Memory):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "Honcho backend is a post-MVP feature. See module docstring. "
            "Map memory_key -> Honcho peer; mirror PetState + events."
        )

    def load(self, key: str) -> PetState:  # pragma: no cover
        raise NotImplementedError

    def save(self, key: str, state: PetState) -> None:  # pragma: no cover
        raise NotImplementedError

    def record_event(
        self, key: str, kind: str, payload: dict | None = None
    ) -> None:  # pragma: no cover
        raise NotImplementedError
