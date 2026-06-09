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
