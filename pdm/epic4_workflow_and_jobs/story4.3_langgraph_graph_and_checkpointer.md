# Story 4.3 — LangGraph graph, state & Postgres checkpointer

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** FR-09, FR-10 · **Depends on:** 4.2, 3.1

## User story

As the orchestrator, I want an explicit LangGraph `StateGraph` with typed state and persisted checkpoints,
so that execution order, retries and branching are deterministic and recoverable.

## Acceptance criteria

- [ ] `GenerationState` (TypedDict / Pydantic) holds **references only**:
      `generation_id, spec_id, spec_path, plan_ref, workspace_path, engine, current_step, status,
      repair_attempts, max_repair_attempts, validation (per-check status + report ref), error_summary,
      failed_checks[], artifact_ids{}, node_commits{node: git_sha}`.
- [ ] The 8 nodes from FR-09 are registered with the conditional edges shown in the epic diagram. Each node is a
      plain async function `(state, deps) → partial state` with injected ports (engine, sandbox, repos, events),
      so it can be unit-tested without the graph.
- [ ] `AsyncPostgresSaver` checkpointer with `thread_id = generation_id`. `setup()` runs on worker start.
- [ ] The repair limit is read from state (job option) and defaults to 3.
- [ ] Every node writes a `node_runs` row (start/finish/status) and emits `step.started` / `step.finished` events (4.5).
- [ ] Graph unit tests with FakeEngine and a fake sandbox cover: invalid spec → FAILED; pass first time →
      COMPLETED; fail once then repair → COMPLETED; fail past the limit → FAILED with a diagnostic report.
- [ ] `GET /api/v1/generations/graph` returns the node/edge definition (from `graph.get_graph()`) for the UI (9.3).
