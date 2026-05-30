# AGENTS.md — PeerPet

> Shared contract for the two co-authors (Rishi & Ranjeet) and any AI coding
> assistant working on this repo. Claude Code and Hermes both read this file
> automatically — keep it accurate, it is load-bearing.

## What we're building

PeerPet is a **digital pet that lives in the background of your terminal**. It
animates in a reserved strip of the screen while your shell stays **fully
usable**. You interact with it through out-of-band commands (`peerpet feed`,
`peerpet play`) that never block your prompt.

**North star:** the pet is delightful and *invisible when you need the terminal*.
If a feature makes the shell feel laggy, janky, or "taken over," it's wrong.

**Scope (read this):** PeerPet the product is a **simple, deterministic pet — no
LLM, no AI, no external services, no network.** Honcho and Hermes are
**dev-workflow tools for us, the authors** (see "Dev workflow & tooling"); they
are NOT dependencies of the shipped pet. Don't add AI to the product.

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
pseudo-terminal (like `tmux`/`script`), reserves the top N rows with a
DECSTBM scroll region (`ESC[<top>;<bottom>r`), and animates the pet in those
rows (right-aligned, top-right) independently of the shell — saving/restoring the
cursor (`ESC7`/`ESC8`) around every draw so the user's input line is never disturbed.

```
peerpet/
  __main__.py        entrypoint: `peerpet` launches the wrapped shell
  cli.py             subcommands: run / feed / play / status / config
  host/
    pty_host.py      spawn shell in pty, relay stdin/stdout, handle SIGWINCH
    region.py        DECSTBM scroll-region mgmt + cursor save/restore
    renderer.py      render the current frame into the reserved rows
  pet/
    state.py         pet model: hunger, mood, energy, xp, last_seen
    behavior.py      tick loop, mood transitions, idle animations
    sprites.py       ASCII / Unicode frames per mood & animation
  interaction/
    ipc.py           unix-socket server (host side) + client (cli side)
    commands.py      feed / play / pet handlers
  memory/
    base.py          Memory interface (get/set per-user state + events)
    local.py         SQLite backend at ~/.local/share/peerpet/<user>.db
  config.py          loads ~/.config/peerpet/config.toml
```

### Data flow
- **Render path:** `behavior.tick()` → updates `state` → `renderer` draws the
  frame for the current mood into the reserved region. Runs on a timer, off the
  shell's critical path.
- **Interaction path:** `peerpet feed` (a separate process) → `ipc` client sends
  a message over the unix socket → host applies it to `state` → next tick reacts.
- **Resize:** `SIGWINCH` → recompute region → resize child PTY to
  `rows - PET_ROWS` → redraw.

### Memory abstraction (important)
All persistence goes through `memory/base.py:Memory`. The implementation is
`local.py` (SQLite, one row per OS user). **Never** import a concrete backend
outside `memory/`; depend on the interface. This boundary stays clean so we can
swap storage later without touching the pet — but it's plain local storage, no
external service.

## Conventions

- **Python ≥ 3.10.** `uv` recommended but optional (works with stdlib venv +
  pip). MVP is **zero runtime deps**. Type hints required on public functions.
- **Format/lint:** `ruff format` + `ruff check`. Run before every commit.
- **No global mutable state** except the single host instance. Pass `state`
  explicitly.
- **Terminal writes go through `host/region.py` only.** Nothing else writes raw
  escape codes — this keeps cursor accounting in one place.
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

## Dev workflow & tooling (NOT part of the product)

These help *us build* PeerPet; they never ship inside it and add no runtime deps.

- **Hermes** → this `AGENTS.md` convention. It's the shared contract our coding
  assistants (Claude Code / Hermes) read. Keep it accurate; that's its whole job.
- **Honcho** → *optional* shared memory for our coding assistants, so context and
  preferences can sync between Rishi's and Ranjeet's sessions. Lives in dev
  tooling, outside the package — **never** imported by `peerpet/`.

If you ever feel tempted to give the *pet* an LLM or call Honcho/Hermes from
product code: don't. That's a different project. The pet stays deterministic.

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
