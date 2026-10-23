# Story 5.1 — Deterministic architecture planner (`plan_architecture`)

**Epic:** [5 — Backend generation](epic5_backend_generation.md) · **Requirements:** FR-03 · **Depends on:** 2.2, 4.3

## User story

As the workflow, I want a reviewable implementation plan derived from the spec, in fastapi-skills terms, so that
generation nodes have an exact file-level scope and the plan is saved as an artifact.

## Acceptance criteria

- [ ] Pure function `plan(spec) → ArchitecturePlan` (no LLM), saved as `plan.json` (artifact kind `plan`):
  - `modules[]`: one per entity → module name (snake_case plural), and every file path the skill's layout requires:
    domain entity, SQLModel model, output port, repository impl, use case per operation, request/response DTOs, router
  - `models[]`: table, columns, FKs, relationships (`Relationship(back_populates=…)`, link model for M:N), indexes, enums
  - `usecases[]`: name (`CreateTaskUsecase`), DI alias (`CreateTaskUsecaseDep`), transactional (true for writes),
    repository methods used, exceptions it may raise
  - `routers[]`: router variable (`task_router`), prefix, tag, operations (operationId, method, path, handler name,
    DTO names, status codes). Registration line for `src/routers.py`.
  - `auth` / `authorization` dependencies required (from Epic 10 when present)
  - `dependencies[]`: additions to `requirements.txt` beyond the template and overlay
  - `tests[]`: required test cases per operation (happy path, 404, 422, and rules from Epic 10)
  - `unresolved[]`: unsupported spec features carried forward to the manifest
- [ ] Deterministic: the same spec gives a byte-identical plan (sorted keys, stable ordering). Snapshot tests per example spec.
- [ ] Naming follows the skill: `I<Entity>Repository`, `I<Entity>RepoDep`, `<Action><Entity>Usecase(Dep)`,
      `<action>_<entity>_dto.py`, handler name derived from operationId (`task.create` → `create_task`).
