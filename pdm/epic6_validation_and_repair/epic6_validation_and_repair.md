# Epic 6 — Validation & repair

## Overview

Run the generated code for real inside an isolated per-job Docker sandbox with its own throwaway PostgreSQL.
Report each check truthfully, and when a check fails, feed targeted errors back to the engine for a bounded
repair loop.

**Requirements:** §3.4, FR-11, FR-12, NFR 8.1, 8.3

## Sandbox topology (per job)

```
 agent-worker ──docker API──▶ network  bga-sbx-<gen>   (internal: no internet)
                                 ├── sandbox-db-<gen>   postgres:18, tmpfs, random password
                                 └── sandbox-<gen>      bga-runner image (python 3.12, uv, make, ruff, pytest)
                                                        /work = bind of $HOST_WORKSPACE_ROOT/<gen>/project
                                                        --cpus --memory --pids-limit --read-only rootfs, non-root, cap-drop ALL
 deps install: a separate short-lived container on network bga-sbx-egress, allowed to reach PyPI only
```

**Status (2026-10-23):** 6.1 and 6.2 done with Epic 5; 6.3 (repair loop) exists since Epic 4 and now repairs real
failures (prompt v2 with the structured digest). The diagnostic report for unrepairable jobs comes with 7.2.

## Stories

| # | Story | Depends on |
|---|---|---|
| 6.1 | [Isolated sandbox runner](story6.1_sandbox_runner.md) | 1.2, 4.4 |
| 6.2 | [Validation check pipeline (`run_validation`)](story6.2_run_validation.md) | 6.1, 5.5 |
| 6.3 | [Repair loop (`repair_code`)](story6.3_repair_loop.md) | 6.2 |

## Epic acceptance

- A deliberately broken project (FakeEngine injects a lint error and a failing test) is repaired and ends COMPLETED.
  An unrepairable one ends FAILED after N attempts with a diagnostic report.
- No sandbox container, network or volume remains after any terminal status.
