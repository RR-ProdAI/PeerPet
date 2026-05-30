# PeerPet 🐾

A digital pet that lives in the **background of your terminal**. It animates in a
reserved strip of the screen while your shell stays **fully usable** — you
interact with it through out-of-band commands that never block your prompt.

> Architecture, conventions, and the collaboration model live in
> [`AGENTS.md`](./AGENTS.md). Read that first.

## Quick start

```bash
git clone <repo-url> PeerPet
cd PeerPet

# Recommended: uv (https://docs.astral.sh/uv/)
uv venv && uv pip install -e ".[dev]"

# Or plain stdlib venv + pip
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Try it
peerpet status        # prints pet state as JSON (works without a TTY)
peerpet run           # launches a shell with the pet (work in progress)
pytest                # run tests
ruff format . && ruff check .
```

## How it works (one paragraph)

`peerpet run` launches your real shell inside a **pseudo-terminal**, reserves the
bottom rows of the screen with a DECSTBM scroll region, and animates the pet
there independently of the shell. Interaction (`peerpet feed`, `peerpet play`)
goes over a unix socket to the running host, so your prompt is never blocked.
Memory is per-OS-user and stored locally (SQLite). The pet is **fully
deterministic — no LLM, no network, no API keys**.

## Status

MVP in progress. See the roadmap and module ownership in [`AGENTS.md`](./AGENTS.md).
