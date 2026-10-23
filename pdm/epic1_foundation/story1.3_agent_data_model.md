# Story 1.3 — Agent data model & migrations

**Epic:** [1 — Foundation](epic1_foundation.md) · **Requirements:** FR-01 (preserve spec), FR-10, FR-14, FR-15, FR-16 · **Depends on:** 1.1

## User story

As the system, I need persistent tables for users, specs, jobs, events, CLI invocations,
validation runs, artifacts and previews so that jobs survive restarts and the UI can show history.

## Acceptance criteria

- [ ] SQLModel ORM models plus pure Pydantic domain entities (fastapi-skills split), with an Alembic migration:

| Table | Key columns |
|---|---|
| `users` | id, email (unique), password_hash, role, created_at |
| `backend_specs` | id, owner_id, spec_version, raw_json (original, untouched), normalized_json, source (`json` / `requirement`), requirement_text, created_at |
| `spec_drafts` | id, owner_id, requirement_text, engine, status, spec_id (nullable), assumptions jsonb, unresolved jsonb, error |
| `generations` | id (`gen_<ulid>`), owner_id, spec_id, options jsonb, engine, status, current_step, repair_attempts, trace_id, langsmith_run_url, error_summary, created_at, started_at, finished_at, heartbeat_at, cancel_requested |
| `generation_events` | id (bigserial = SSE id), generation_id, ts, type, step, status, payload jsonb |
| `node_runs` | id, generation_id, node, attempt, status, started_at, finished_at, summary jsonb |
| `cli_invocations` | id, generation_id, node_run_id, engine, purpose, argv_redacted, exit_code, status, duration_ms, turns, input_tokens, output_tokens, cost_usd, stdout_ref, stderr_ref |
| `validation_runs` | id, generation_id, attempt, check (syntax/lint/deps/startup/migration/tests/openapi), status, duration_ms, output_ref, details jsonb |
| `artifacts` | id (`art_<ulid>`), generation_id, kind (source/openapi/manifest/report/plan/log), name, path (internal, never exposed), size, sha256, content_type |
| `previews` | id, generation_id (unique active), status, container_id, db_container_id, host_port, url, started_at, last_accessed_at, expires_at, error |

- [ ] Status enums: generation `PENDING|RUNNING|VALIDATING|REPAIRING|COMPLETED|FAILED|CANCELLED`, preview
      `STARTING|RUNNING|STOPPED|FAILED`.
- [ ] Indexes on `generations(owner_id, created_at desc)` and `generation_events(generation_id, id)`.
- [ ] `make migrate` applies it. Downgrade to base works.

## Technical notes

- Large outputs (stdout, logs, test reports) are stored as files under the workspace or artifact dir.
  DB rows hold `*_ref` pointers only (FR-10).
- LangGraph checkpoint tables are created by `PostgresSaver.setup()` (4.3), not by Alembic.
