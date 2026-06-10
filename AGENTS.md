# AGENTS.md — PeerPet

> Shared contract for the two co-authors (Rishi & Ranjeet) and any AI coding
> assistant working on this repo. These assistants read this file automatically
> — keep it accurate, it is load-bearing.

# Agent instructions for this repo

You are dedicated to this repository only.

## What we're building

PeerPet is a **digital pet that lives in the background of your terminal**. It
animates in a reserved strip of the screen while your shell stays **fully
usable**. You interact with it through out-of-band commands (`peerpet feed`,
`peerpet play`) that never block your prompt.

**North star:** the pet is delightful and *invisible when you need the terminal*.
If a feature makes the shell feel laggy, janky, or "taken over," it's wrong.

**Scope (read this):** PeerPet the product is a **simple, deterministic pet — no
LLM, no AI, no external services, no network.** Don't add AI to the product.

## Hard constraints (do not violate)

1. **The terminal must stay fully usable.** Typing, scrolling, resizing, running
   full-screen apps (vim, htop) must all work. The pet yields to the shell, never
   the other way around.
2. **Leave the terminal clean on exit.** Reset the DECSTBM scroll region and
   clear the pet rows in *all* exit paths, including signals and crashes.
3. **No AI, no network, no keys in the product.** Pet behavior is deterministic
   Python. No LLM calls, no API keys, no external services — ever.
4. **Memory is per-user and lightweight.** Local store keyed by OS user. No
   network calls in the hot path.

## Architecture

A **PTY host** owns the screen. It spawns the user's real shell inside a
pseudo-terminal (like `tmux`/`script`), reserves the bottom N rows with a
DECSTBM scroll region (`ESC[<top>;<bottom>r`), and animates the pet in those
rows (right-aligned, bottom-right) independently of the shell — saving/restoring the
cursor (`ESC7`/`ESC8`) around every draw so the user's input line is never disturbed.
The strip defaults to the bottom so the region's top margin stays at row 1, which
preserves the terminal's native scrollback; `pet_position = "top"` is also supported.

The full component map, data flow, and the reasoning behind each design choice
live in [`ARCHITECTURE.md`](./ARCHITECTURE.md). Keep it in sync when you change
the shape of the code.

## Conventions

- **Python ≥ 3.10.** `uv` recommended but optional (works with stdlib venv +
  pip). MVP is **zero runtime deps**. Type hints required on public functions.
- **Format/lint:** `ruff format` + `ruff check`. Run before every commit.
- **No global mutable state** except the single host instance. Pass `state`
  explicitly.
- **Terminal writes go through `host/region.py` only.** Nothing else writes raw
  escape codes — this keeps cursor accounting in one place.
- **All persistence goes through the `memory.Memory` interface.** Never import a
  concrete backend outside `memory/`; storage stays swappable and local-only.
- **Keep sprites in `sprites.py`,** not inline in logic. One dict: mood → frames.
- **Tests:** `pytest`. The terminal layer is hard to unit-test; cover `pet/` and
  `memory/` well, and test `region.py` escape-sequence output as strings.

## How to run

```bash
# Setup (pick one)
uv venv && uv pip install -e ".[dev]"          # recommended
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"

peerpet status          # print pet state as JSON (no host / TTY needed)
peerpet run             # launch a shell with the pet (MVP target, WIP)
peerpet feed            # interact from another pane/window
pytest                  # tests
ruff format . && ruff check .
```

## Collaboration model (Rishi & Ranjeet)

**Process lives in [`CONTRIBUTING.md`](./CONTRIBUTING.md): branch → PR → green CI
→ one review → merge. Never commit to `main` directly** (it's protected).

- **Ownership (initial):** keep PRs scoped to one area to avoid stepping on the
  shared screen code.
  - `host/` + `region.py` — the terminal/PTY layer (highest-risk, pair on it).
  - `pet/` + `interaction/` — behavior, sprites, commands.
  - `memory/` — storage interface + local backend.
- **Update this file in the same PR** whenever you change architecture,
  conventions, or run commands. An out-of-date AGENTS.md is a bug.
- Both authors use Claude Code (Claude Pro). This file is the shared brief — if
  you find yourself re-explaining context to the assistant, put it here instead.

## For AI assistants

Everything in [`CONTRIBUTING.md`](./CONTRIBUTING.md) applies to you. A few rules
matter more for an autonomous agent than for a human — partly because you lack a
human's instincts, and partly because `main` protection does **NOT** enforce on
admins ("Include administrators" is OFF). If you run under Rishi's or Ranjeet's
account, git will *let* you do things you must never do:

- **Never push or merge to `main`** — even though admin override makes it
  technically possible. That escape hatch is for a human to invoke consciously;
  it is never yours. Stop after opening the PR.
- **Never merge your own PR.** Open it, then hand off for human review.
- **Never run destructive commands without explicit approval:** `git push -f`
  / `--force`, `git reset --hard`, `git clean -fd`, branch deletion, or anything
  that rewrites published history or discards uncommitted work.
- **Run `git diff --staged` before each commit;** never commit secrets, `.env`,
  keys, or the local memory DB (under `~/.local/share/peerpet/`).
- **When done,** run the same checks CI runs locally
  (`ruff format . && ruff check . && pytest -q`), then report the branch name,
  the PR link, and a plain-language summary. Don't call a task finished before
  that.

If a destructive or irreversible action seems necessary, describe it and ask
first.

## Roadmap (product)

- **MVP:** PTY host + reserved-region renderer; one pet with hunger/mood; `feed`
  and `play` over IPC; SQLite per-user memory; clean exit + resize handling.
- **Next:** richer animations & moods, idle behaviors, config (pet name, colors,
  position), persistence of streaks/level.
- **Later:** more pets/species, mini-interactions, themes — all still pure,
  deterministic, offline.

## Gotchas

- Test inside **and** outside `tmux` — both manipulate scroll regions; they can
  conflict.
- Always restore terminal state in a `finally`/`atexit`/signal handler. A crash
  that leaves DECSTBM set makes the user's terminal unusable.
- WSL2: no transparent overlay windows — the reserved-region approach is
  deliberate, don't "upgrade" to a floating window.
- Full-screen apps (vim) use the alternate screen buffer; detect and pause pet
  drawing while the alt-screen is active so we don't fight them.
