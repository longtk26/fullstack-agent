# Epic 4 — LangGraph workflow & generation jobs

## Overview

The asynchronous job system and its LangGraph state machine: submit a job (HTTP 202), queue it in Redis,
run it on a worker with checkpointed state, stream progress over SSE, cancel it, and recover safely
after a worker crash. This epic wires the full graph. Nodes that are not real yet use the FakeEngine
until Epics 5–6 land.

**Requirements:** §3.1, §3.2, FR-09, FR-10, FR-14, FR-15, NFR 8.2, 8.3

## Workflow

```
 START ─▶ validate_spec ──invalid──▶ END (FAILED, validation errors)
              │ ok
              ▼
        plan_architecture ─▶ generate_database ─▶ generate_backend ─▶ generate_tests
                                                                          │
              ┌───────────────────────────────────────────────────────────┘
              ▼
        run_validation ──all passed──▶ package_artifacts ─▶ END (COMPLETED) ─▶ [post] deploy_preview (7.3)
           ▲     │ failed
           │     ▼
           │  attempts < max ? ──no──▶ END (FAILED, diagnostic report)
           │     │ yes
           └── repair_code
```

Status mapping: `validate_spec … generate_tests` and `package_artifacts` → `RUNNING`, `run_validation` → `VALIDATING`,
`repair_code` → `REPAIRING`. Final status is set by the runner from the graph's `outcome`.

**Status (2026-10-23):** done on `feat/epic4-workflow-jobs`; all three epic acceptance checks verified on the Docker
stack (fake engine: full run with one repair; worker SIGKILLed mid-`generate_backend` → reaper requeue → resumed from
the Postgres checkpoint without re-running finished nodes; API restart mid-job has no effect).
Placeholders until later epics: `plan_architecture` uses a skeleton plan (5.1), `run_validation` only checks syntax
statically and reports the other checks `not_run` (6.1/6.2), `package_artifacts` produces no artifacts yet (7.1).
Code: `agent-api/src/orchestrator/`, `agent-api/src/modules/generations/`, `agent-api/src/libs/queue/`.

## Stories

| # | Story | Depends on |
|---|---|---|
| 4.1 | [Generation job API & Redis queue](story4.1_generation_job_api.md) | 1.4, 2.3 |
| 4.2 | [Worker process, concurrency & liveness](story4.2_worker_and_liveness.md) | 4.1 |
| 4.3 | [LangGraph graph, state & Postgres checkpointer](story4.3_langgraph_graph_and_checkpointer.md) | 4.2, 3.1 |
| 4.4 | [Workspace manager & crash-safe recovery](story4.4_workspace_and_recovery.md) | 4.3 |
| 4.5 | [Progress events & SSE stream](story4.5_progress_events_sse.md) | 4.3 |
| 4.6 | [Job cancellation](story4.6_job_cancellation.md) | 4.5 |

## Epic acceptance

- With `engine=fake`, a submitted spec goes PENDING → RUNNING → VALIDATING → REPAIRING → VALIDATING → RUNNING → COMPLETED,
  and every transition appears on the SSE stream.
- Killing the worker container mid-job and restarting it resumes from the last checkpoint without re-running completed nodes.
- `docker compose restart agent-api` does not affect running jobs.
