# Project State — PeerPet

> **What:** A deterministic digital pet that lives in the background of your terminal, animating in a reserved strip of the screen while your shell stays fully usable.
>
> **Scope:** No AI, no LLM, no network, no API keys. Pure Python with stdlib dependencies only (pty, socket, sqlite3, tomli). Per-user, local storage only.
>
> **Version:** 0.1.0 (pre-release)
>
> **Repository:** [`https://github.com/RR-ProdAI/PeerPet`](https://github.com/RR-ProdAI/PeerPet)

---

## 📁 Repository Structure

```
peerpet/
├── __main__.py      # Entry point: `python -m peerpet`
├── cli.py           # CLI: run / feed / play / pet / status / config
├── config.py        # TOML config from ~/.config/peerpet/config.toml
│
├── host/            # PTY host — owns the terminal
│   ├── __init__.py
│   ├── pty_host.py # spawns shell in PTY, relays IO, handles SIGWINCH, cleanup
│   ├── region.py   # DECSTBM scroll-region + cursor primitives (only ANSI writer)
│   └── renderer.py # draws pet frame into reserved rows, right-aligned
│
├── pet/             # The deterministic brain
│   ├── __init__.py
│   ├── state.py    # PetState data model (hunger, energy, happiness, mood, xp, level)
│   ├── behavior.py # tick() (decay over time) + apply_command() (feed/./pet)
│   └── sprites.py  # ASCII/Unicode frames per mood — all art lives here
│
├── interaction/     # Out-of-band IPC (unix socket)
│   ├── __init__.py
│   ├── ipc.py      # socket server + client protocol (newline-delimited JSON)
│   └── commands.py # handlers: make_handler() | make_host_handler()
│
├── memory/          # Persistence abstraction
│   ├── __init__.py
│   ├── base.py     # Memory interface (load/save/record_event), factory getMemory()
│   └── local.py    # SQLite backend at ~/.local/share/peerpet/<user>.db
│
└── tests/           # pytest
```

---

## 🏗️ Architecture Overview

### Core Design: The PTY Host Owns the Terminal

PeerPet uses a **pseudo-terminal (PTY) host** to "own" the screen. This keeps the pet and shell from fighting over the cursor.

1. `peerpet run` spawns your `$SHELL` inside a PTY (slave). You're the shell process.
2. The host (parent) owns the PTY master.
3. The host sets a **DECSTBM scroll region** (`ESC[<top>;<bottom>r`) covering rows `1 .. rows - pet_rows`. The shell scrolls only above the pet strip.
4. The child PTY is sized to `rows - pet_rows`. The shell never scrolls into the pet.
5. The host runs a `select()` loop over `[stdin, pty_master, ipc_socket]` and ticks animation on a timer.
6. Every render wraps cursor save/restore to keep the shell's input line untouched.

**Why the bottom strip, not top?**  
Bottom (`pet_position = "bottom"`) keeps the DECSTBM region's top margin at row 1, preserving native terminal scrollback. Top puts the pet top-right but disables scrollback.

### Data Flow

| Flow | Path |
| -----| -----|
| **Render** | `behavior.tick(state)` → `renderer.draw()` → writes to pet row (timer-driven, off-shell critical path) |
| **Interaction** | CLI (`peerpet feed`) → `ipc.send()` → `IpcServer` (host-side) → `apply_command()` → next tick reacts |
| **Resize** | `SIGWINCH` → recompute region → resize PTY → redraw |
| **Exit/Crash** | `atexit` + signal handlers → reset DECSTBM, restore cursor, save state |

### Memory Abstraction

All persistence goes through `memory/Memory`. The concrete backend is `local.py` (SQLite, `~/.local/share/peerpet/<user>.db`), keyed by OS user. The `Memory` interface ensures the backend can be swapped without touching the pet.

---

## 📂 Important Files

| File | Role | Notes |
| -----| -----| -----|
| `AGENTS.md` | Contributor contract, constraints, conventions, module ownership | Keep this accurate — it's load-bearing |
| `CONTRIBUTING.md` | Branch → PR → CI → review → merge workflow | |
| `ARCHITECTURE.md` | Design decisions, why choices were made | Cross-reference `AGENTS.md` for "how to work" |
| `README.md` | Install/usage for end users | |
| `pyproject.toml` | Hatch builds, dev deps (pytest, ruff) | |
| `peerpet/__init__.py` | `__version__ = "0.1.0"` — single source of truth for versions | |
| `peerpet/cli.py` | Subcommand entry points | |
| `peerpet/host/pty_host.py` | **Highest-risk module** — strays corrupt user's terminal | Pair on this, test in throwaway terminal |
| `peerpet/host/region.py` | **Only ANSI writer** — pure string builders, unit-testable | |
| `peerpet/host/renderer.py` | Compose + draw frame | |
| `peerpet/pet/` | Deterministic state machine, no randomness | |
| `peerpet/interaction/` | IPC protocol (JSON, newline-delimited) | |
| `peerpet/memory/base.py` | Persistence interface boundary | Never import `LocalMemory` outside `memory/` |
| `peerpet/memory/local.py` | SQLite backend | |
| `tests/` | pytest, covers `pet/`, `memory/`, `region/` | `host/` hard to unit-test |

---

## 🚀 How to Run

### Development Setup

```bash
cd /home/rishi/projects/PeerPet

# Option 1: uv (recommended)
uv venv && uv pip install -e ".[dev]"

# Option 2: stdlib venv
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

### Commands

| Command | Description |
| -------| -------|
| `peerpet run` | Launch `$SHELL` with the pet (PTY host) |
| `peerpet feed` | Feed the pet (separate process, sends via IPC) |
| `peerpet play` | Play with it |
| `peerpet pet` | Pet the pet |
| `peerpet status` | Print state as JSON (no host / TTY needed) |
| `peerpet config` | Print resolved config + paths |
| `pytest` | Run tests |
| `ruff format . && ruff check .` | Pre-commit checks |

### Running Tests

```bash
pytest
# or
pytest tests/ -v
```

---

## ⚠️ Hard Constraints (Never Violate)

1. **Terminal must stay fully usable.** Typing, scrolling, full-screen apps (vim) must not be blocked.
2. **Leave terminal clean on exit.** Reset DECSTBM, clear pet rows, restore cursor in *all* paths (exit, signal, crash).
3. **No AI, no network.** Deterministic Python, stdlib only.
4. **Memory is per-user/local.** Local SQLite, no network calls in hot path.

---

## 📋 Current TODOs (from AGENTS.md, roadmap)

### MVP ✅ (mostly done)

- [x] PTY host + reserved-region renderer
- [x] One pet with hunger/mood/energy/happiness
- [x] `feed`, `play`, `pet` over IPC
- [x] SQLite per-user memory
- [x] Clean exit + resize handling
- [x] Zero runtime deps (stdlib only)

### Next Priority

- [ ] **Richer animations & moods** (idle blink cycles, multi-frame sprites)
- [ ] **Configuration** (pet name, colors, position via `~/.config/peerpet/config.toml`) — already partially done, but not persisted
- [ ] **Streaks / level persistence** — tracks interactions, not static in `PetState`
- [ ] **Resize handling (#11)** — `SIGWINCH` recompute + resize child PTY (commented in `pty_host.py` TODO #19)
- [ ] **Alt-screen detection (#12)** — pause drawing while vim/htop uses alternate buffer

### Later (non-MVP)

- [ ] More pets / species
- [ ] Mini-interactions in parallel
- [ ] Themes

---

## 🔍 Key Implementation Details

### State Decay (per hour)

| Stat | Decay |
| -----| -----|
| Hunger | 8.0 per hour (100 → 0: starving) |
| Energy | 5.0 per hour (100 → 0: exhausted) |
| Happiness | 4.0 per hour (100 → 0: bored) |

### Mood Logic (_derive_mood_)

- `HUNGRY`: hunger < 25
- `SLEEPY`: energy < 25
- `SAD`: happiness < 30
- `HAPPY`: happiness > 75 AND hunger > 50
- `CONTENT` (default): elsewhere

### Interaction Effects

| Command | Hunger | Energy | Happiness | XP per command |
| -------| -----| ------| ---------| --------------|
| `feed` | +25 | +0 | +0 | +5 |
| `play` | 0 | −10 | +20 | +5 |
| `pet` | 0 | 0 | +8 | +5 |

---

## 🧪 Testing & Quality

- **Tests:** pytest, targets `pet/`, `memory/`, `region/`
- **Lint:** `ruff format` + `ruff check` (E, F, I, UP, B)
- **CI:** `.github/workflows/ci.yml`, Python 3.10 & 3.12

**Known limitation:** `host/pty_host.py` is hard to unit-test (PTY, TTY, escape sequences). Test outside a real terminal when possible.

---

## 📊 Task Recommendations (Prioritized)

### High Priority

1. **Add SIGWINCH resize handling (#11)**  
   - Detect `SIGWINCH` → recompute region → resize PTY → redraw  
   - Impact: pet disappears on screen resize, janky UX

2. **Add alt-screen detection (#12)**  
   - Detect `DECSET 1049` / `DECRST 1049` → pause drawing when vim/htop active → resume on return  
   - Impact: pet smears over TUI apps

3. **Persist config.toml (#29ish)**  
   - Save/restore `pet_name`, `pet_rows`, `tick_interval` on startup  
   - Impact: user config resets every run

### Medium Priority

4. **Idle animations (blink cycles)**  
   - Cycle sprites every ~4s when mood is stable (not frozen)  
   - Impact: pet looks alive, not static

5. **Level / streak tracking**  
   - Add `level` decay + XP events beyond `behavior.tick`  
   - Impact: pet growth over time, engagement

### Low Priority

6. **More sprites per mood**  
   - Expand `sprites.py` with 3–5 frames per mood  
   - Impact: richer visual variety

7. **Config UI / validation**  
   - CLI `peerpet config validate | repair`  
   - Impact: catch TOML typos before run

---

## 🛠️ Dev Workflows & Tools (Outside Product)

- **Hermes** reads `AGENTS.md` as the shared convention.
- **Honcho** is optional shared memory for Rishi/Ranjeet's Hermes sessions — *never* imported by product code.
- CI pipeline: `ruff format . && ruff check . && pytest -q`

---

## 🔗 Points of Interest

| Ref | Doc |
| ----| ----|
| [`AGENTS.md`](./AGENTS.md) | Contributor contract, constraints, module ownership |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | branch → PR → review → merge workflow |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Design decisions & "why" |
| [`README.md`](./README.md) | Install / usage for end users |

---

*This file auto-generates from project context, keep it tight. Do not modify code yet.*
