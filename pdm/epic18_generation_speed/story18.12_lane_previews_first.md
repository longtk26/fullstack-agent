# Story 18.12 — Each lane's preview starts the moment the lane passes; integration runs in the background

**Epic:** [18 — Generation speed](epic18_generation_speed.md) · **Requirements:** FR-21, FR-27, FR-30 · **Depends on:**
18.8, 14.2, 7.3, 13.5

## User story

As a user of a dynamic app, I want to click through the frontend (on mock data) as soon as the frontend lane passes,
and try the backend API as soon as the backend lane passes, without either waiting for the other lane or for the
integration step, so that I see my app minutes earlier; the switch to the live API and the live checks happen in
the background once both are up.

## Evidence (2026-11-04, `gen_01M6J88EY82D746ZG01MB7WE77`, Antigravity on the host worker)

| Time | Event |
|---|---|
| 03:08:36 | frontend lane COMPLETED: **no frontend preview started** |
| 03:30:00 | backend lane COMPLETED: **no backend preview started** |
| 03:30:00 | `integrate` → `integration.kept_mocks` "backend preview is not running" (no wait), integration SKIPPED |
| 03:30:01 | generation COMPLETED_WITH_WARNINGS; only now `request_start` sends both preview starts |
| 03:31:06 / 03:31:18 | frontend / backend previews RUNNING (the frontend 22.5 min after its lane passed) |
| 03:32:34 | a later recheck switches to live, recreates the frontend and **restarts the backend** |

Why the early starts of 18.8 never fire here:

- Antigravity jobs run on the host worker, started with `PREVIEW_WORKER=false` (`Makefile`, `ANTIGRAVITY_AUTH=account`).
  `bootstrap.py` passes `previews=None` to the runner on such a worker, so `package_lane_preview`
  (`orchestrator/integration.py`) returns at its first line, and `integrate` has no preview service to probe or
  switch with. Only the end-of-run `on_completed` → `PreviewService.request_start` goes through the Redis command
  bus. 18.8 was verified with the fake engine on the Docker worker, which is a preview worker.
- `integrate` is a graph node after both lanes (one LangGraph super-step holds `backend_lane` and `frontend_lane`),
  so the generation's status, the UI's App-tab hand-off (`use-generation-detail.ts`: COMPLETED **and** frontend
  RUNNING) and the API tab's try-it (`use-api-tab.ts`: `isSucceeded(detail.status)`) all wait for the slower lane
  plus integration.
- The lanes are coupled: a failed frontend lane cancels the backend (`abort_backend(..., frontend_failed=True)` in
  `graph.py` and `frontend_nodes.py`), and once the frontend passes, a watchdog cancels a backend that is still
  validating after `INTEGRATION_WAIT_SECONDS` (`JobContext.start_integration_wait_watchdog`).

## Steps

1. **Previews from any worker.** The job context gets a preview client that works on every worker: the local
   `PreviewService` on a preview worker; elsewhere a client that sends the same commands over `PreviewCommandBus`
   (as the API does for recheck / use-mocks) and waits for the reply where it needs one (`start` with its options,
   `switch-frontend`, `probe`, `status`). `package_lane_preview` and `integrate` use only this client, so they act
   the same on the Docker and the host worker. The bus `start` command carries `options_override` (`mockApi`,
   `apiBaseUrl`).
2. **Frontend preview when the frontend lane passes.** `validate_frontend` (pass, dynamic mode) packages
   `frontend.zip` and starts the frontend preview right away: on the live API if the backend preview is already
   RUNNING, else on mocks (`MOCK_TEST_API=true`). No wait for the backend lane or for `integrate`.
3. **Backend preview when the backend lane passes.** `run_validation` (pass, dynamic mode) packages the backend
   (18.8 step 1, unchanged) and starts the backend preview, with the frontend's port already reserved for CORS (as
   today), so the later switch does not restart the backend.
4. **Integration in the background.** When the second of the two previews is RUNNING (whichever lane finished
   last), integration starts: `check_backend_ready`, switch the frontend to live (`integration.switched_to_live`;
   the frontend container is recreated with the runtime config, the backend is not touched), then the live checks
   (`integration:health`, `contract`, `smoke`, `journeys`). The previews stay usable throughout; a failed live check
   sets the integration lane FAILED (as today) and never stops a preview. Integration stays the last graph node, so
   the trace, the timings and the final status still include it; what changes is that nothing the user sees waits
   for it.
5. **Lanes no longer cancel each other.**
   - A failed frontend lane no longer cancels the backend lane: the backend finishes, its preview starts, the
     integration lane is SKIPPED ("frontend lane failed"), and the generation ends `COMPLETED_WITH_WARNINGS`
     (the mirror of Q14). Decision D-LANES below; FR-21 changes with it.
   - The integration-wait watchdog is removed: a slow backend is bounded by the job timeout only.
     `INTEGRATION_WAIT_SECONDS` keeps one use: how long `integrate` waits for the backend preview to reach RUNNING.
   - A cancelled generation still stops every preview it started (18.8 step 5).
6. **UI.**
   - App tab: shows the frontend preview as soon as its row is STARTING / RUNNING, during the run, with a line
     that says which API it uses ("Mock data: the backend is still being generated" → "Live API"). The automatic
     hand-off to the App tab happens the first time the frontend preview turns RUNNING, not on COMPLETED (once,
     and never after the user picked a tab).
   - API tab: try-it is enabled once the backend preview is RUNNING (`canPreview` checks the backend lane and
     `backend.zip`, not the overall status).
   - Steps / lanes view: the integration lane reads "Waiting for the backend" (or the frontend) while one lane
     still runs, then "Switching to live", then the check results.
7. Backend-only and static modes keep today's flow (their only lane ends the generation).
8. **Tests** (fake engine, fake preview runtime, fake bus):
   - on a non-preview worker, the lane previews start through the bus;
   - the frontend preview is requested while the backend lane is still running (planted slow fake backend);
   - backend first: the frontend starts straight on the live API;
   - frontend first: one switch to live, no backend restart;
   - a failed frontend lane lets the backend finish and preview, giving `COMPLETED_WITH_WARNINGS`;
   - a slow backend is no longer cancelled by the watchdog;
   - cancellation stops early previews;
   - UI: the hand-off and the API-tab gating, with React Testing Library on the hooks.

## Acceptance criteria

- [x] In dynamic mode the frontend preview starts when the frontend lane passes, and the backend preview when the
      backend lane passes, on the Docker worker **and** on the host worker (`PREVIEW_WORKER=false`).
- [x] The App tab shows the running frontend during the generation and opens by itself when it first runs; the
      API tab's try-it works once the backend preview runs.
- [x] The switch to live and the live checks run without stopping either preview; the backend container is never
      restarted by the switch.
- [x] A failed frontend lane no longer cancels the backend; the generation ends `COMPLETED_WITH_WARNINGS` with a
      running backend preview. A slow backend is not cancelled by an integration timeout.
- [ ] The status note records: seconds from each lane's COMPLETED to its preview RUNNING (before: 1 350 s
      frontend, 78 s backend), and from the second lane's COMPLETED to `integration.switched_to_live`.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `cd agent-ui && pnpm exec tsc --noEmit`. `make up` with
the fake engine, dynamic `project-tracker-dynamic` with a slowed fake backend lane: watch the `preview.status`,
`lane.changed` and `integration.*` events and the App tab. Repeat with a host worker (`make dev-worker` with
`PREVIEW_WORKER=false` and the fake engine) to cover the bus path. No paid engine.

## Status

**Planned (2026-11-04)**, at the user's request: "frontend completed → preview starts immediately; backend
completed → starts without waiting for the frontend; integration in the background".

**Implemented (2026-11-04)**, on `feat/story18.12-lane-previews` (stacked on `feat/story18.10-api-drafts`):
- `orchestrator/previews.py`: `PreviewClient` gives a non-preview worker the same calls as `PreviewService` (`start`
  with options, `switch_frontend`, `probe`, `stop`) over `PreviewCommandBus`; `bootstrap.py` hands it to the runner
  when `PREVIEW_WORKER=false`. The preview worker's `handle` gained `start` options, `switch-frontend` and `probe`
  (reply with the raw body base64). `wait_settled` waits for a row to leave STARTING and, for a switch, to run on
  the requested API (a switch can queue behind a start that is still building).
- `package_lane_preview` starts the frontend on the live API when the backend preview already runs, else on mocks;
  `integrate` waits for the frontend to settle before the switch. `switch_frontend` restarts the backend only when
  its CORS lacks the frontend's port (`cors_ports`, recorded at backend start), so the switch never restarts it in
  the usual flow.
- Lanes: in dynamic mode a frontend engine / sandbox failure or repair limit sets `frontend_error` (no raise, no
  `abort_backend`); the frontend lane always flows into `integrate`, which skips the switch ("frontend lane
  failed") or ends the job when both lanes failed (`route_after_integrate`). `overall_status`: one lane COMPLETED and
  the other FAILED → COMPLETED_WITH_WARNINGS. The integration-wait watchdog (`start_integration_wait_watchdog`,
  `backend_validating`) is gone; `INTEGRATION_WAIT_SECONDS` only bounds the wait for the backend preview.
- UI: the stream refreshes the detail on `lane.changed`, `preview.status` and `integration.*` and refetches the
  preview rows; the App tab opens the first time the frontend preview runs (not after the user picked a tab), and
  says "Mock data: the backend is still being generated" / "Switching to the live API…"; the API tab's try-it
  works once the backend lane passed; the integration lane reads "Waiting for the backend / frontend".
- Tests (`test_parallel_generation.py`): the bus path from a non-preview worker (frontend preview RUNNING before the
  backend lane ends; two frontend deploys, mocks then live; one backend deploy), a failed frontend lane with a
  running backend preview, both lanes failing, a slow backend repair no longer cancelled; `test_generation_modes`.
  Deviation: the UI has no test runner, so the hand-off and API-tab gating are covered by `tsc` / ESLint only.
- Found on the way: since `95b547b` (frontend e2e tests dropped) `integration:smoke` ran `playwright test` with no
  specs and failed ("No tests found"); it never showed because `integrate` was always skipped on real runs. Now
  it reports `skipped` when the frontend has no `tests/e2e/*.spec.ts` (the live contract check still runs). The
  frontend sandbox tests still expected ESLint and frontend tests to run; updated to what the lane does since then.
- `make up`, fake engine, `project-tracker-dynamic` + `two-entity` (`gen_01M6JKC031W3JJ4WCV6AGM9CFP`): frontend lane
  COMPLETED 06:19:49 → its preview STARTING 06:19:50 (RUNNING 06:22:38, the first image build); switch to live
  06:23:12–14 recreated only the frontend; integration COMPLETED (health, contract passed; smoke, journeys
  skipped); generation COMPLETED. Found: the backend lane passed at 06:20:02 but its preview started only at
  06:22:39, because a backend start took the frontend's lock (to reserve its port) and waited for the frontend
  build. `PreviewService.lock_kinds`: once the frontend row has its port, a backend start takes its own lock only.
  Rerun (`gen_01M6JKW0D1V2MSFN31ACNP7CAK`): frontend lane 06:28:12 → preview STARTING 06:28:13; backend lane
  06:28:24 → preview STARTING 06:28:24, RUNNING 06:28:49 while the frontend image still built (RUNNING 06:30:37);
  switch 06:30:38–40; COMPLETED 06:30:42. The frontend's ~2.5 min is its `next build` in the image (18.6's
  decision: previews build from the ZIP).
- Still to measure with a real run (with the user's yes): seconds from each lane's COMPLETED to its preview RUNNING
  on the host worker.
