# Changelog

All notable changes to PeerPet are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While we're pre-1.0 (`0.x`), minor versions may include breaking changes; patch
versions are bug fixes.

Add a bullet under **[Unreleased]** in the PR that makes the change. When cutting a
release, rename `[Unreleased]` to the new version with the date and start a fresh
`[Unreleased]` section (see CONTRIBUTING.md → "Cutting a release").

## [Unreleased]

### Added
- **`peerpet run` is implemented** (`host/pty_host.py`): launches your real
  shell in a PTY with the pet animating in a reserved bottom strip
  (right-aligned, sixel pixel art with text fallback). The shell stays fully
  usable: DECSTBM keeps output above the strip, `feed`/`play`/`pet` arrive over
  the IPC socket and trigger reactions live, the pet pauses while full-screen
  apps hold the alternate screen and repaints after clears, SIGWINCH resizes
  the child and re-reserves the strip (suspending it entirely on very short
  terminals), and every exit path restores the terminal and persists the pet.
- **Pixel-art pet over sixel graphics**: on terminals that support sixel
  (Windows Terminal ≥ 1.22, xterm, foot…), `peerpet demo` now renders a real
  Tamagotchi-style pixel creature — composed body with shading/outline, big
  glinting eyes, blush, idle bob + blink, feed/play/pet reaction scenes (snack,
  bouncing ball, hearts) — plus pixel stat bars for happiness and hunger. New
  modules: `pet/pixel_sprites.py` (art + palette + HUD), `host/sixel.py`
  (stdlib sixel encoder), `host/termcaps.py` (runtime sixel/cell-size
  detection). Terminals without sixel keep the Unicode mascot; non-TTY output
  keeps the static frame. `Animator` now accepts a pluggable sprite library.
- Dev preview tool `tools/preview_frames.py`: renders every animation frame to
  a PNG contact sheet (stdlib PNG writer) for iterating on pixel art without a
  sixel terminal.
- `docs/SHARED_STATE_PLAN.md`: future design for sharing pet stats between
  users (local-first sync behind the `memory.Memory` boundary; backend/database
  choice explicitly deferred).
- Versioning & release system: single-sourced version (`peerpet/__init__.py`),
  this changelog, and a tag-triggered GitHub Release workflow.
- Pet animation engine (`pet/animation.py`): an `Animator` that picks each frame
  — a *mostly-still* idle loop that blinks occasionally (not a constant twitch),
  with one-shot **reactions** (feed/play/pet) that override the idle then settle
  back. Pure logic with an injectable clock, unit-tested.
- New multi-line **alien mascot** sprite (`pet/sprites.py`): a rounded head with
  eyes, mouth, and arms; per-mood idle frames + reaction sequences (munch / wave
  / hearts). All frames are equal size to prevent jitter.
- `peerpet demo` command (`demo.py`): a safe, standalone preview of the
  animation in the current terminal — no PTY host, no scroll region. Runs on an
  accelerated, balanced clock so the pet visibly swings happy↔sad and fires
  reactions; restores the cursor and exits cleanly on Ctrl-C. No-ops to a single
  static frame when output isn't a TTY.
- Renderer multi-row support (`host/renderer.py` `compose_lines`) and cursor
  primitives (`host/region.py` `cursor_up`/`cursor_down`/`hide_cursor`/
  `show_cursor`).

### Changed
- Pet lives in a reserved strip at the **top** of the terminal, right-aligned
  (previously specified as a bottom strip).
- Mood is now two states (`behavior._derive_mood`): **sad** when hunger *or*
  happiness is below 30, otherwise **happy** — so the animation reads clearly.
  The status line now shows happiness (was energy/level).

[Unreleased]: https://github.com/RR-ProdAI/PeerPet/commits/main
