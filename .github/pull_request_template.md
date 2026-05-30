## What & why

<!-- One or two sentences. Link any issue: "Closes #12". -->

## How I tested

<!-- What you actually ran / observed. For host/ changes, say how you confirmed
the terminal was left clean on exit and survived a resize. -->

## Checklist

- [ ] `pytest -q` passes locally
- [ ] `ruff format --check .` and `ruff check .` are clean
- [ ] Scoped to one area (didn't sprawl across host/ + pet/ + memory/)
- [ ] Updated `AGENTS.md` if architecture, conventions, or commands changed
- [ ] Product stays **deterministic** — no LLM / network / API keys added
- [ ] If this touches `host/`: considered terminal-clean-on-exit, resize (SIGWINCH),
      and alt-screen (vim/htop) behavior
