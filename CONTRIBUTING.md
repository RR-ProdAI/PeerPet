# Contributing to PeerPet

The day-to-day workflow for Rishi & Ranjeet. The *what/why* of the code lives in
[`AGENTS.md`](./AGENTS.md); this file is *how we ship it*.

## Golden rule

**Never commit to `main` directly.** Every change lands through a pull request
that passes CI and gets one approving review. `main` is protected to enforce this.

## The loop

```bash
# 1. Start from fresh main
git checkout main && git pull

# 2. Branch (see naming below)
git checkout -b feat/idle-animations

# 3. Work in small commits. Before pushing, run the same checks CI runs:
ruff format . && ruff check . && pytest -q

# 4. Push and open a PR
git push -u origin feat/idle-animations
gh pr create --fill          # or open it in the GitHub UI

# 5. Get a review, address comments, merge when CI is green + approved.
```

## Branch naming

`<type>/<short-description>`, kebab-case:

- `feat/` — new functionality
- `fix/` — bug fix
- `chore/` — tooling, deps, CI, config
- `docs/` — docs only
- `refactor/` — no behavior change

Examples: `feat/multiline-sprites`, `fix/region-resize`, `chore/dev-workflow`.

## Commits

Short imperative subject (≤72 chars), body explaining *why* when it isn't obvious.
Co-authored commits are welcome when you pair:

```
Add idle blink animation

Cycles two frames every ~4s when the pet is content so it doesn't look frozen.

Co-Authored-By: Ranjeet <...>
```

## Pull requests

- **Keep them small and single-purpose.** A PR that touches `host/` *and* `pet/`
  *and* `memory/` is hard to review and risks the shared screen code — split it.
- The PR template checklist is not decoration; tick it honestly.
- **`host/` changes get extra scrutiny** (it's the terminal layer). Prefer to
  pair on them, and in review confirm: clean exit, resize handling, alt-screen.
- CI (ruff format + ruff check + pytest on 3.10 & 3.12) must be green to merge.
- One approving review required. Review each other's work — that's the point.

## Reviewing

- Pull the branch and actually run it when it's behavior you can see.
- For `host/`: a stray escape sequence can corrupt the reviewer's terminal —
  read the escape-sequence logic carefully and test in a throwaway terminal.
- Be quick and kind. A two-person project lives or dies on review latency.

## Issues

Use issues to track work and split ownership. Reference them from PRs
(`Closes #N`) so they close on merge.

## Bootstrap note

Until Ranjeet accepts the collaborator invite, only Rishi is an active member, so
the "one approving review" rule can't be satisfied by a second person yet. During
this window `main` protection does **not** enforce on admins, so Rishi can merge
when necessary. Once you're both active, flip on "Include administrators" in the
branch protection settings so the rules apply to everyone equally.
