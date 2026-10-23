# Story 5.3 — Data layer generation (`generate_database`)

**Epic:** [5 — Backend generation](epic5_backend_generation.md) · **Requirements:** FR-04 · **Depends on:** 5.2, 3.2, 3.4, 6.1

## User story

As the workflow, I want domain entities, SQLModel models and an Alembic migration generated per the skill, so
that the schema is correct and tested against a real PostgreSQL.

## Acceptance criteria

- [x] Engine call (`generate_database` prompt, scope `src/modules/shared/**` and `src/modules/__init__.py`) writes:
  - pure Pydantic domain entities in `shared/domain/entities/<entity>_entity.py` (no ORM imports)
  - SQLModel models in `shared/infrastructure/models/<entity>_model.py`: PKs (uuid default `uuid4`, or int/string
    per spec), FKs with `ondelete`, 1:1, 1:N, M:N (link model), unique constraints, nullable, defaults, indexes,
    and enums (`sa_column=Column(Enum(...))` with a named type)
  - every model imported in `src/modules/__init__.py`
- [x] The migration is **not** written by the LLM. The node starts the sandbox with an empty Postgres, then runs
      `make newmg name="initial_schema"` (autogenerate), then `make mghead`.
- [x] Deterministic post-checks: the reflected DB schema (tables, columns, FKs, uniques, indexes) matches `plan.models`.
      AST check: no file under `shared/domain/entities` imports `sqlmodel` or `sqlalchemy`. Mismatches become validation
      errors for repair.
- [x] Commit `node:generate_database`.

**Status (2026-10-23):** done. Migrations are derived artifacts (`orchestrator/migrations.py`): regenerated in the
sandbox only when the model files changed, with enum `DROP TYPE`s appended to the downgrade so
`downgrade base` + `upgrade head` works. The node reports the schema post-check; `run_validation` enforces it
(check `migration`) so repair can fix mismatches.
