# Story 4.4 — Workspace manager & crash-safe recovery

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** FR-10 (recovery), NFR 8.1, 8.2, 8.3 · **Depends on:** 4.3

## User story

As the system, I want each job to have an isolated, versioned workspace so that a resumed job never sees
half-written files and never repeats completed side effects.

## Acceptance criteria

- [ ] `WorkspaceManager.create(gen_id)` → `$WORKSPACE_ROOT/<gen_id>/{project/, spec/, plan/, logs/, reports/}`
      (mode 0700). All path inputs are resolved and checked to stay under the root.
- [ ] `project/` is a local git repo (the template's own `.git` is discarded, 5.2). **Every node that changes files ends with a commit**
      (`node:<name> attempt:<n>`), and the sha is stored in `state.node_commits`.
- [ ] On resume, the workspace is `git reset --hard && git clean -fdx` back to the sha of the last checkpointed
      node before the graph continues. Partial writes from the crashed node are discarded.
- [ ] Side-effect idempotency: artifact packaging uses deterministic names plus sha256 (re-run overwrites).
      Sandbox and preview containers are named `sandbox-<gen>` / `preview-<gen>` and removed or reused when found on resume.
- [ ] Disk guard: if the workspace exceeds `WORKSPACE_MAX_MB` (default 500) → FAILED `DISK_LIMIT`.
- [ ] Retention: workspaces of finished jobs are deleted after `WORKSPACE_RETENTION_HOURS` (default 72).
      Artifacts follow `ARTIFACT_RETENTION_DAYS`.
