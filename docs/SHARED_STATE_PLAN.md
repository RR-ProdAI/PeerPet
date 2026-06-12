# Shared Pet State — Future Plan (design only, no code yet)

> Status: **deferred**. This documents *how* we will share pet stats between
> users when we get there. The storage/database choice is deliberately not made
> here. Nothing in this plan is implemented; the current product remains fully
> local. Written 2026-06-12.

## Why

PeerPet is shared between users (it's in the name). Eventually a user's pet —
its hunger, happiness, streaks, level — should be visible to their peers:
seeing a teammate's thriving (or neglected) pet is the social hook. That
requires the stats to live somewhere both users can reach, not just in
`~/.local/share/peerpet/peerpet.db`.

## What we already have going for us

All persistence goes through the `memory.Memory` interface (`memory/base.py`),
keyed per user, with SQLite (`memory/local.py`) as the only backend. That
boundary was built exactly so storage could be swapped or extended without
touching the pet. The shared-state work plugs in behind it.

## Constraints to respect (and one to renegotiate)

- AGENTS.md hard constraint #3 says **no network in the product** and #4 says
  memory is local with **no network calls in the hot path**. Sharing stats
  inherently needs a transport. Before any implementation, both authors must
  explicitly amend #3 (e.g. "no network *except the opt-in sync backend*").
  This plan does not override AGENTS.md — it flags the conflict for a human
  decision.
- Whatever we choose, the **hot path stays local**: the host loop and CLI
  always read/write the local store. Sync is asynchronous and best-effort.
- **Opt-in.** A user who never configures sharing gets exactly today's
  behavior: local SQLite, zero network.

## Architecture: local-first with a sync layer

```
 host / cli ──> memory.Memory (unchanged interface)
                   │
                   ├── local.py  (SQLite — always the source the app reads)
                   └── sync.py   (future: pushes/pulls snapshots, off hot path)
                                      │
                                      ▼
                        shared backend — DECIDED LATER
              (candidates: hosted Postgres/Supabase, Redis, a tiny
               HTTP service, or even a shared-filesystem SQLite)
```

- **Local-first:** every read and write lands in local SQLite first; the app
  never blocks on the network. Sync runs on a timer/idle hook and pushes a
  snapshot, pulls peers' snapshots into a separate read-only cache table.
- **Single-writer model:** each pet has exactly one owner; only the owner's
  machine writes that pet's stats. Peers only ever *read* others' pets. This
  sidesteps merge conflicts almost entirely.
- **Multi-device (same user) conflicts:** last-writer-wins on the whole
  snapshot, using `last_seen` (already in `PetState`) as the clock. Stats decay
  deterministically from `last_seen`, so the freshest snapshot is the truth.

## Data model sketch

Snapshot = what `PetState.to_dict()` already produces, plus identity:

| field | notes |
|---|---|
| `user_id` | stable identity — open question (OS user is not globally unique) |
| `pet_name`, `hunger`, `happiness`, `mood`, `last_seen` | as today |
| `updated_at` | server/sync timestamp for last-writer-wins |
| `schema_version` | so old clients don't corrupt new data |

## Work items when we pick this up

1. Amend AGENTS.md constraint #3/#4 (human decision, both authors).
2. Choose the backend (the deferred decision) + a `user_id` scheme.
3. `memory/sync.py` behind the `Memory` interface; config keys in
   `config.toml` (`[share] enabled/backend/...`), default off.
4. `peerpet friends` (or similar) CLI to view peers' pets — read-only render
   of cached peer snapshots, reusing the existing sprite/animation stack.
5. Privacy pass: what's shared (stats only, no command history), how to leave.

## Explicitly out of scope until then

- Realtime interaction between pets, gifting, multiplayer mini-games.
- Accounts/auth beyond the minimum `user_id` scheme.
- Any change to the local-only default experience.
