# Story 14.1 — Parallel workflow (fork / join lanes)

**Epic:** [14 — Parallel generation](epic14_parallel_generation.md) · **Requirements:** FR-27, FR-09 · **Depends on:** 12.2, 12.3, 4.3

## User story

As a user, I want the frontend and backend built at the same time, so that a dynamic app takes about as long as
its slowest half.

## Acceptance criteria

- [ ] Parent LangGraph graph per mode: `backend` = today's graph; `static` = frontend lane only;
      `dynamic` = `validate_inputs` (both specs + 12.5) → `build_contract` → **parallel** backend and frontend
      sub-graphs (LangGraph fan-out) → `integrate` (14.2) → finish.
- [ ] Each lane has its own workspace (`project/backend`, `project/frontend`), engine invocations, repair counter
      and lane status (12.2); both read `.bga/contract.json`; neither may change it.
- [ ] Concurrency: the two lanes count as two worker slots; engine calls of both lanes run in parallel.
- [ ] Failure semantics: a failing frontend lane fails the job; a failing backend lane lets the frontend lane
      finish on mocks (→ `COMPLETED_WITH_WARNINGS`); cancel stops both lanes; resume (4.4) restarts each lane
      from its own last completed node.
- [ ] `GET /generations/graph?mode=dynamic` returns the parallel graph for the UI diagram.
