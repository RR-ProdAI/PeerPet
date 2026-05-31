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
- `peerpet run` now hosts your real `$SHELL` in a PTY with the pet animating in a
  reserved top-right strip: a `select()` relay loop, an animation timer,
  out-of-band `feed`/`play`/`pet` over the unix socket, and clean teardown
  (scroll region reset + termios restored) on every exit path — normal `exit`,
  Ctrl-D, and signals (`SIGTERM`/`pkill`, `SIGHUP`, `SIGINT`).

### Changed
- Pet lives in a reserved strip at the **top** of the terminal, right-aligned
  (previously specified as a bottom strip).
- New `pet_position` config option (`top` | `bottom`). A reserved scroll region
  disables the terminal's native scrollback while the pet runs; `bottom` keeps the
  region's top margin at row 1, which preserves scrollback on some terminals.

[Unreleased]: https://github.com/RR-ProdAI/PeerPet/commits/main
