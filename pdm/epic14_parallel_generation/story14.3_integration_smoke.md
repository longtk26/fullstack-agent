# Story 14.3 — Live integration smoke test

**Epic:** [14 — Parallel generation](epic14_parallel_generation.md) · **Requirements:** FR-27, FR-11 · **Depends on:** 14.2

## User story

As a user, I want proof that the generated frontend really works against the generated backend, not only
against mocks.

## Acceptance criteria

- [x] After switching to live, the Node sandbox runs the frontend's Playwright smoke tests against the frontend
      preview with the live API: every page renders without console errors; every data-bound section shows
      backend data (seed records); every form submits successfully and the result is visible.
- [x] Live responses are validated against the contract schemas (a mismatch names operation and field).
- [x] Results in `integration` checks of the report; failures do **not** regenerate either side automatically
      (the contract is fixed); they are reported with the failing page, operation and response.

**Status (2026-10-28):** done. After switching the frontend preview to live in `integrate`
(`src/orchestrator/integration.py`), three checks run and are recorded as `ValidationRunEntity` rows (`integration:health`,
`integration:contract`, `integration:smoke`) and written to `integration-validation.json` and `report.json` (`checks`
and `report["integration"]`):
- `check_live_health` probes the backend's `/health` and the frontend preview's `/api/runtime-config` (`mockApi: false`,
  `apiBaseUrl`).
- `validate_live_responses` probes every unauthenticated `GET` operation in `contract.json` against the live backend
  (using fixture IDs from `x-bga.fixtures` for path parameters) and validates the live JSON payload against the
  contract's response schema (`validate_value_against_schema`), reporting any mismatch with `operation`, `field`, and
  `response`.
- `run_playwright_live_smoke` runs `pnpm exec playwright test` in the Node sandbox with `PLAYWRIGHT_BASE_URL` pointing
  at the live frontend preview (`templates/nextjs_overlay/files/dynamic/playwright.config.ts`) and an in-sandbox TCP
  bridge forwarding `127.0.0.1:<fe_port>` and `127.0.0.1:<be_port>` over the shared Docker network to the preview
  containers. Failures set the `integration` lane to `FAILED` (overall `COMPLETED_WITH_WARNINGS`) without regenerating
  either lane.
