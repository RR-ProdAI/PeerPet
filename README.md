# PeerPet 🐾

A digital pet that lives in the **background of your terminal** — it animates in a
reserved strip at the bottom of the screen while your shell stays **fully usable**.
Feed it, play with it, and watch its mood change, all without interrupting your work.

PeerPet is a **simple, deterministic program**: no LLM, no network, no API keys,
no accounts. Your pet lives entirely on your machine.

> 🎬 _Demo coming soon._ <!-- TODO: add an asciinema/GIF once `peerpet run` lands -->

## Highlights

- Lives **in** the terminal, not a separate window — works anywhere, including WSL2.
- Your shell stays 100% usable; the pet never blocks your prompt.
- Interact from any pane with plain commands (`peerpet feed`, `peerpet play`).
- Per-user, offline, and private — state is stored locally in SQLite.

## Install

> Pre-release: not on PyPI yet, so install from GitHub.

**End users — recommended via [pipx](https://pipx.pypa.io):**

```bash
pipx install git+https://github.com/RR-ProdAI/PeerPet.git
```

**From source / for development:**

```bash
git clone https://github.com/RR-ProdAI/PeerPet.git
cd PeerPet
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # or: uv venv && uv pip install -e ".[dev]"
```

Requires Python ≥ 3.10. No other runtime dependencies.

## Usage

| Command | What it does |
|---|---|
| `peerpet run` | Launch your shell with the pet living at the bottom |
| `peerpet feed` | Feed the pet (raises hunger) |
| `peerpet play` | Play with it (happiness up, energy down) |
| `peerpet pet` | Give it a pet (small happiness boost) |
| `peerpet status` | Print the pet's current state as JSON |
| `peerpet config` | Print resolved configuration and paths |

`run` hosts your real `$SHELL`, so just use your terminal normally — the pet
animates below. Interact from the same or another pane: `peerpet feed`.

## Configuration

Optional — PeerPet works with zero config. To customize, create
`~/.config/peerpet/config.toml`:

```toml
pet_name = "Pixel"      # what to call your pet
pet_rows = 1            # rows reserved at the bottom for the pet
tick_interval = 0.5     # seconds between animation frames
# shell = "/bin/zsh"    # defaults to $SHELL
```

See what's currently in effect with `peerpet config`.

## How it works

`peerpet run` launches your shell inside a pseudo-terminal and reserves the bottom
row(s) with a terminal scroll region, animating the pet there independently of your
shell. Interaction travels over a local unix socket, so your prompt is never
blocked. Full design in [`ARCHITECTURE.md`](./ARCHITECTURE.md).

## Status

Early development. Today `status` and `config` work; the live pet (`run`, and the
`feed` / `play` / `pet` interactions that drive it) is under active development —
follow [#3](https://github.com/RR-ProdAI/PeerPet/issues/3) for Phase 1 progress.

## Contributing

Contributions from the team are welcome — see [`CONTRIBUTING.md`](./CONTRIBUTING.md)
for the branch → PR → review → merge workflow, and [`AGENTS.md`](./AGENTS.md) for
architecture conventions and module ownership.

## License

To be finalized (MIT proposed) — see the release-readiness work.
