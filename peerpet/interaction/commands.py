"""Command handlers: glue between an interaction request and pet state.

Used host-side as the IpcServer handler. Loads the user's pet, applies the
behavior, persists, and returns a reply. Pure of any terminal concerns.
"""

from __future__ import annotations

from peerpet.memory.base import Memory, current_memory_key
from peerpet.pet import behavior
from peerpet.pet.state import PetState

VALID_COMMANDS = {"feed", "play", "pet"}


def make_handler(memory: Memory):
    """Build an IpcServer-compatible handler bound to a Memory backend.

    Stateless: loads the user's pet fresh per request. Used by paths that don't
    hold a live pet in memory (e.g. tests). The running host uses
    `make_host_handler` instead so commands hit the pet it's actually rendering.
    """

    def handler(command: str, payload: dict) -> dict:
        key = payload.get("key") or current_memory_key()
        if command not in VALID_COMMANDS:
            return {"ok": False, "error": f"unknown command: {command!r}"}
        state = memory.load(key)
        behavior.apply_command(state, command)
        memory.save(key, state)
        memory.record_event(key, command, payload or None)
        return {"ok": True, "state": state.to_dict()}

    return handler


def make_host_handler(state: PetState, memory: Memory, key: str | None = None):
    """Build a handler that mutates the host's **live** `state` in place.

    The host owns one `PetState` it ticks and renders every frame. The handler
    must apply commands to *that* object (not a fresh copy from storage), so a
    `feed` shows up on the very next render tick; we persist afterward.
    """
    key = key or current_memory_key()

    def handler(command: str, payload: dict) -> dict:
        if command not in VALID_COMMANDS:
            return {"ok": False, "error": f"unknown command: {command!r}"}
        behavior.apply_command(state, command)
        memory.save(key, state)
        memory.record_event(key, command, payload or None)
        return {"ok": True, "state": state.to_dict()}

    return handler
