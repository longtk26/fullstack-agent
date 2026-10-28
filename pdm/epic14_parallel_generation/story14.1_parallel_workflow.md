# Story 14.1 — Parallel workflow (fork / join lanes)

**Epic:** [14 — Parallel generation](epic14_parallel_generation.md) · **Requirements:** FR-27, FR-09 · **Depends on:** 12.2, 12.3, 4.3

## User story

As a user, I want the frontend and backend built at the same time, so that a dynamic app takes about as long as
its slowest half.

## Acceptance criteria

- [x] Parent LangGraph graph per mode: `backend` = today's graph; `static` = frontend lane only;
      `dynamic` = `validate_inputs` (both specs + 12.5) → `build_contract` → **parallel** backend and frontend
      sub-graphs (LangGraph fan-out) → `integrate` (14.2) → finish.
- [x] Each lane has its own workspace (`project/backend`, `project/frontend`), engine invocations, repair counter
      and lane status (12.2); both read `.bga/contract.json`; neither may change it.
- [x] Concurrency: the two lanes count as two worker slots; engine calls of both lanes run in parallel.
- [x] Failure semantics: a failing frontend lane fails the job; a failing backend lane lets the frontend lane
      finish on mocks (→ `COMPLETED_WITH_WARNINGS`); cancel stops both lanes; resume (4.4) restarts each lane
      from its own last completed node.
- [x] `GET /generations/graph?mode=dynamic` returns the parallel graph for the UI diagram.

**Status (2026-10-28):** done. `build_graph(ctx, GenerationMode.DYNAMIC)` in `src/orchestrator/graph.py` fans out
from `build_contract` into two compiled LangGraph subgraphs (`backend_lane` with `output_schema=BackendLaneOutput`
and `frontend_lane` with `output_schema=FrontendLaneOutput`) and converges on `integrate → package_artifacts`.
`JobContext` (`src/orchestrator/context.py`) isolates `current_lane` and `current_run_id` via `ContextVar`s, tracks
concurrent invocations across both lanes (`active_invocations`, `lane_invocations`), acquires a second worker slot
from `WorkerService.slots` while both lanes are active, and restores `.bga/contract.json` in both workspaces before
validation. `_checkpoint_state` in `src/orchestrator/runner.py` inspects `graph.aget_state(run_config, subgraphs=True)`
so resume resets each repository (`project` and `frontend`) to its own lane's last completed commit and restarts each
lane from its own checkpointed node. `_display_graph` exposes the flat fan-out/fan-in topology for
`GET /api/v1/generations/graph?mode=dynamic`.
