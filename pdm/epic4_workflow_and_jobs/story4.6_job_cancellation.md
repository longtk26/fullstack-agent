# Story 4.6 — Job cancellation

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** FR-14, NFR 8.2 · **Depends on:** 4.5

## User story

As a user, I want to cancel a running generation and be sure nothing keeps running or consuming tokens.

## Acceptance criteria

- [ ] `POST /api/v1/generations/{id}/cancel` → 202. Sets `cancel_requested` and publishes to `bga:cancel:<genId>`.
      Terminal jobs → 409 `ALREADY_FINISHED`. PENDING jobs → CANCELLED immediately and removed from the queue.
- [ ] The worker listens and then: (1) cancels the active engine invocation (process-group kill, 3.1), (2) stops and
      removes `sandbox-<gen>` containers and network, (3) marks the node as cancelled, (4) sets status CANCELLED,
      (5) emits a final event.
- [ ] The graph checks the cancel flag between nodes, so cancellation also works when no subprocess is running.
- [ ] Test: cancel during a long FakeEngine call → no child PID left, no `sandbox-<gen>` container left, status CANCELLED within 10 s.
