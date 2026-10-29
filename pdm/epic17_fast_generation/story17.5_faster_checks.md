# Story 17.5 — Auto-fix and pre-installed dependencies

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-11, FR-12 · **Depends on:** 6.2, 13.4

## User story

As a user, I want formatting and lint slips fixed mechanically and dependencies ready in the sandbox, so that a
generation does not spend minutes in an engine repair for something a tool fixes in a second.

## Acceptance criteria

- [x] Before validation, the backend lane runs `ruff check --fix` and `ruff format`, the frontend lane
      `eslint --fix` on engine-written files only; the fixes are committed
      (`node:autofix`). The repair loop starts only for what is left.
- [x] Overlay-owned files the engine touched are restored before checks (as `.bga/contract.json` already is),
      so a `conventions` failure for an owned file no longer needs an engine repair.
- [x] `bga-runner-node` ships a pnpm store with the base's dependencies, keyed by the base lock sha;
      `pnpm install --offline` is used when the lock is unchanged. `bga-runner` does the same for the backend
      template's requirements.
- [x] Status note records the time of `install` and of repairs before and after on the golden projects.

**Status (2026-10-29):** done.

- **Auto-fix** (`src/orchestrator/autofix.py`), the first step of `run_validation` and `validate_frontend`:
  generator-owned files whose hash differs from `.bga/owned.json` are checked out from the scaffold commit
  (`node:scaffold` / `node:scaffold_frontend`), only when that commit holds exactly the recorded version; then
  `ruff check --fix --exit-zero` + `ruff format` (backend, every `.py` outside owned files and tool folders) or
  `eslint --fix` (frontend, `src/` only, outside owned files) runs in the sandbox. Changes are committed as
  `node:autofix attempt:<n>` and announced as `validation.autofix` (`fixed`, `restored`, `durationMs`); the node
  summary gets `autofixed` / `restoredOwned`. The UI log shows it ("Auto-fix before checks: …").
- **Deviation, owned files:** only *changed or deleted* owned files are restored. Files the engine *added* under an
  owned folder (e.g. `src/libs/extra.py`) stay and the `conventions` check reports them as before: deleting engine
  work is a decision for the repair, not for a tool.
- **Deviation, dependencies:** the pre-warmed pnpm store (13.4) and the baked backend venv (6.2) already existed,
  so `install` never downloaded anything. Its time went into copying ~1 GB / 64k files from the store volume into
  the bind-mounted workspace. New: one **shared node_modules volume per dependency set**
  (`bga-fe-modules-<key>`, key = sha of `pnpm-lock.yaml`, `pnpm-workspace.yaml` and package.json's dependency
  fields), filled offline once per worker process and mounted **read-only** at `/work/node_modules`, with a tmpfs
  for the three folders Vite/Vitest write to (`.vite`, `.vite-temp`, `.vitest-cache`; tsc, ESLint, next build and
  Playwright only read). The `install` check then runs `pnpm ls` ("dependencies ready (shared node_modules …)").
  A project whose dependencies differ, or whose packages are not in the store, installs into the workspace as
  before. Switch: `FRONTEND_SHARED_MODULES` (default on); `make down-all` removes the volumes.
- **Timings** (fake engine, `make up`, Docker Desktop):

  | | before | after |
  |---|---|---|
  | `frontend:install` | 50.5 s | 0.8 s |
  | `validate_frontend` attempt 1 / 2 | 99 s / 49 s | 43 s / 35 s |
  | static generation `static-landing`, end to end | 192 s | 86–88 s |
  | full frontend validation of the golden site (sandbox test) | 72–90 s | 36–38 s |

  The gain is larger than the install alone: with node_modules in a volume, `tsc`, `next build` and the tests
  no longer read it through Docker Desktop's file sharing. Auto-fix costs ~0.5 s (ruff) and ~4 s (eslint) per
  validation. Repairs: the last real backend run (`gen_01M5XTFV…`) failed `lint` on 2 × I001 + 2 × format and
  spent 197 s in `repair_code`; that case is now fixed before the checks (sandbox test
  `test_autofix_clears_import_order_and_formatting_before_lint`). The last real static run's 226 s frontend
  repair was a `custom-hooks` conventions finding, which no tool fixes; 17.2 removes that kind of failure. In the
  dynamic fake run, auto-fix also reformatted the Alembic migration that `ensure_migration` autogenerates.
- **Trade-off:** a repair engine running on the host no longer finds a filled `node_modules` in the workspace
  (only the mount point). Generation never had one (it runs before the first install).
- Verified: `make test` (419 passed), sandbox tests (`BGA_SANDBOX_TESTS=1`: auto-fix with real ruff and ESLint,
  the golden static site on the shared node_modules), `make up` with the fake engine: static `static-landing`
  COMPLETED, dynamic `project-tracker-dynamic` + `two-entity` COMPLETED and switched to the live API.
