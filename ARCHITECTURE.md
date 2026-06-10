# Architecture

This document explains **why PeerPet is shaped the way it is** — the design and
the decisions behind it. For *how to work on the code* see
[`AGENTS.md`](./AGENTS.md); for *how we ship changes* see
[`CONTRIBUTING.md`](./CONTRIBUTING.md).

## What PeerPet is

A digital pet that lives in the **background of your terminal**. It animates in a
small reserved strip of the screen while your shell stays **fully usable**. You
interact with it through ordinary commands (`peerpet feed`, `peerpet play`) that
never block your prompt.

It is a **simple, deterministic program** — no LLM, no network, no API keys.

## The core idea: a PTY host that reserves a region

The hard part of "a pet that shares the screen with a *usable* shell" is that two
writers (the pet and the shell) can't both control the cursor. PeerPet solves
this the way `tmux` and `script` do — by owning the terminal:

```
            real terminal
        ┌──────────────────────────┐
        │  your shell (scrolls)     │  ← rows 1 .. N-pet_rows  (DECSTBM region)
        │  $ git status             │
        │  $ npm test               │
        ├──────────────────────────┤
        │           (◕ᴥ◕) Pixel·content│ ← reserved pet row(s), bottom, right-aligned
        └──────────────────────────┘
```

1. `peerpet run` launches your real `$SHELL` inside a **pseudo-terminal (PTY)**.
2. The host sets a **DECSTBM scroll region** (`ESC[<top>;<bottom>r`) covering rows
   `1 .. N-pet_rows`, so the shell only ever scrolls *above* the reserved strip;
   the bottom `pet_rows` rows are reserved for the pet.
3. The child PTY is sized to `rows - pet_rows`, and its output occupies the region
   above the strip, so the shell never scrolls into the pet.
4. The host runs a `select()` relay (real stdin → PTY master, PTY master → real
   stdout) and, on its own timer, animates the pet into the reserved rows —
   **right-aligned** so it sits in the bottom-right with room to move — wrapping
   every draw in cursor **save/restore** so your input line is untouched.

This keeps the shell 100% usable and works in any terminal (including WSL2),
which is exactly why we chose it over a floating overlay window (see decisions).

> **Why the bottom, and why a strip (not a free-floating corner sprite)?** A
> reserved DECSTBM region — not a sprite floated over live output — is what keeps
> the pet from being overwritten by scrolling text. We reserve it at the **bottom**
> so the region's top margin stays at row 1: that preserves the terminal's native
> **scrollback** (a top strip moves the top margin to row 2, and most terminals
> then stop saving scrolled-off lines), and the shell's own cursor coordinates pass
> through untouched. A full-screen clear (`ESC[2J`) still wipes the whole screen
> including the pet's rows, so the host repaints the pet after one. The pet can
> also live at the top via `pet_position = "top"`, at the cost of scrollback while
> it runs.

## Components

```
peerpet/
  host/        owns the terminal
    pty_host.py   spawn shell in a PTY, relay IO, handle SIGWINCH, clean teardown
    region.py     DECSTBM scroll-region + cursor primitives (only writer of ANSI)
    renderer.py   compose + draw a pet frame into the reserved rows
  pet/         the (deterministic) brain
    state.py      data model: hunger/energy/happiness/mood/xp/level/last_seen
    behavior.py   tick (time-based decay) + apply_command (feed/play/pet)
    sprites.py    ASCII/Unicode frames per mood (all art lives here)
  interaction/ out-of-band, non-blocking
    ipc.py        unix-socket server (host) + client (cli)
    commands.py   feed/play/pet handlers, bound to a Memory backend
  memory/      persistence boundary
    base.py       Memory interface + per-user key (OS user) + factory
    local.py      SQLite backend at ~/.local/share/peerpet/peerpet.db
  config.py    optional ~/.config/peerpet/config.toml (zero-config defaults)
  cli.py       run / feed / play / pet / status / config
```

## Data flow

- **Render path:** a timer calls `behavior.tick(state)` (decays stats by elapsed
  time, recomputes mood) → `renderer.draw()` paints the frame into the reserved
  region. Runs off the shell's critical path.
- **Interaction path:** `peerpet feed` is a *separate process*. Its `ipc` client
  sends one JSON line over a unix socket to the running host; the host applies it
  via `commands` → updates `state` → the next frame reacts. The shell is never
  blocked because interaction never touches the host's stdin/stdout.
- **Resize:** `SIGWINCH` → recompute the region → resize the child PTY → redraw.
- **Filling the screen with output (e.g. `cat` a long `.log`):** the DECSTBM
  region confines that output to the shell rows, so even a file that scrolls past
  the whole window stays *above* the reserved strip and never overlaps or
  smears the pet — the pet's rows are simply not part of the shell's scroll area.
- **Scrollback:** because the region's top margin is row 1 (bottom strip), the
  terminal keeps feeding scrolled-off lines into its native scrollback, so the
  mouse wheel still works. `pet_position = "top"` gives that up (top margin row 2).
- **Full-screen apps (vim, htop, less):** these switch to the terminal's
  **alternate screen buffer**. The host detects the alt-screen enter/leave
  (DECSET/DECRST `1049`) and **pauses pet drawing** while it's active, then
  repaints on return, so the pet never fights a full-screen TUI.
- **Exit (any path, incl. crash/signal):** reset the scroll region and restore
  the cursor so the terminal is left clean.

## Key decisions

1. **In-terminal reserved region (bottom strip, pet right-aligned), not a floating
   overlay window.** A transparent always-on-top window (Shimeji-style) gives
   richer art but is OS-specific and painful on WSL2. A reserved scroll region
   works in any terminal and keeps the pet truly "in" the terminal. We reserve the
   strip at the **bottom** (pet **right-aligned** → bottom-right) so the scroll
   region's top margin stays at row 1: this **preserves native scrollback** and
   lets the shell's own cursor coordinates pass through untouched. A top strip
   (`pet_position = "top"`) puts the pet top-right but disables scrollback while it
   runs and needs the host to re-anchor the cursor after a screen clear.
2. **PTY host (own the terminal), not shell hooks.** A prompt hook could only
   animate between commands. Owning the PTY lets the pet animate continuously
   while the shell stays fully interactive.
3. **Python.** Fast to build a stdlib-only daemon (`pty`, `select`, `socket`,
   `sqlite3`); good fit for the team. No third-party runtime deps for the MVP.
4. **Deterministic — no AI in the product.** Pet behavior is a plain state
   machine. No LLM, no network, no API keys. This keeps it lightweight, private,
   predictable, and testable.
5. **One ANSI writer.** Only `host/region.py` emits raw escape sequences, so
   cursor accounting lives in one place and is unit-testable as strings.
6. **Memory behind an interface.** All persistence goes through `memory.Memory`;
   `local.py` (SQLite, keyed by OS user) is the implementation. The boundary lets
   us swap storage later without touching the pet — but it stays plain local
   storage, no external service.
7. **Out-of-band interaction.** Commands travel over a unix socket, not the
   shell's stdin, so the prompt is never blocked or intercepted.

## Non-goals

- No GUI / no separate window.
- No LLM, cloud, accounts, or telemetry.
- Not a terminal multiplexer — the PTY host does the minimum to host one shell
  plus the pet, not split panes/sessions. These features are to be worked on later.

## Pointers

- [`AGENTS.md`](./AGENTS.md) — contributor contract: constraints, conventions,
  module ownership, gotchas.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — branch → PR → CI → review → merge.
- [`README.md`](./README.md) — install & usage.
