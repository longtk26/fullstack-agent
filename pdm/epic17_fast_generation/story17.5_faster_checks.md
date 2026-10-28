# Story 17.5 — Auto-fix and pre-installed dependencies

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-11, FR-12 · **Depends on:** 6.2, 13.4

## User story

As a user, I want formatting and lint slips fixed mechanically and dependencies ready in the sandbox, so that a
generation does not spend minutes in an engine repair for something a tool fixes in a second.

## Acceptance criteria

- [ ] Before validation, the backend lane runs `ruff check --fix` and `ruff format`, the frontend lane
      `eslint --fix` on engine-written files only; the fixes are committed
      (`node:autofix`). The repair loop starts only for what is left.
- [ ] Overlay-owned files the engine touched are restored before checks (as `.bga/contract.json` already is),
      so a `conventions` failure for an owned file no longer needs an engine repair.
- [ ] `bga-runner-node` ships a pnpm store with the base's dependencies, keyed by the base lock sha;
      `pnpm install --offline` is used when the lock is unchanged. `bga-runner` does the same for the backend
      template's requirements.
- [ ] Status note records the time of `install` and of repairs before and after on the golden projects.

**Status:** open.
