"""Command handlers: glue between an interaction request and pet state.

Used host-side as the IpcServer handler. Loads the user's pet, applies the
behavior, persists, and returns a reply. Pure of any terminal concerns.
"""

from __future__ import annotations

from peerpet.memory.base import Memory, current_memory_key
from peerpet.pet import behavior

VALID_COMMANDS = {"feed", "play", "pet"}


def make_handler(memory: Memory):
    """Build an IpcServer-compatible handler bound to a Memory backend."""

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
