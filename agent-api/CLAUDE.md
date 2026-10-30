# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

This is the **Fullstack Generation Agent** API + worker, built on the `feat/fastapi` template
(see `templates/template.lock`). From the repo root, prefer `make dev`, `make dev-api`, `make dev-worker`,
`make migrate`, `make test` — they point at the dev Postgres 18 / Redis ports from `.env`.

```bash
make run                        # Start FastAPI dev server (fastapi dev src/main.py)
make worker                     # Start the job worker (python -m src.worker)
make newmg name="<description>" # Auto-generate Alembic migration from model changes
make mghead                     # Apply all pending migrations
make mgdown                     # Rollback last migration
make test                       # pytest (creates and migrates the <db>_test database)
make lint                       # ruff check + format check
```

Agent-specific notes:
- `ports/output/__init__.py` re-exports `I<Name>RepoDep` lazily (module `__getattr__`) so import order cannot cycle.
- Errors render as `{"error": {"code", "message", "details"}}` (`src/libs/exceptions/handlers.py`); pass an `ErrorCode`.
- Auth: `CurrentUserDep` / `AdminUserDep` from `src.modules.auth.presenter`; other users' resources → 404 via `ensure_owner`.
- PostgreSQL enums: add an explicit `sa.Enum(name=...).drop(...)` to migration downgrades.
- Only the worker talks to Docker (sandboxes `src/sandbox/`, previews `src/preview/`). The API reaches previews
  through `PreviewCommandBus` (Redis); artifacts are files under `ARTIFACT_ROOT`, resolved only from DB rows.
- Tracing (Epic 8): spans come from `src/orchestrator/tracing.py` (RunTree API; LangGraph's own tracer is off).
  Use `tracing.span(...)` / `tracing.current().child(...)`; record what the local trace needs in the DB too
  (`model_calls`, `sandbox_execs`), since `/trace` and `/usage` are built from records, not from LangSmith.
- Modes (Epic 12): `generations.mode` + `lanes`; graph per mode in `orchestrator/graph.py`; lane rules in
  `modules/shared/domain/generation_modes.py`. FrontendSpec lives in `modules/shared/domain/frontend_spec/`;
  the API contract (`orchestrator/contract.py`) and its checks (`checks/conformance.py`, `checks/consistency.py`)
  are pure functions with snapshot tests (`UPDATE_SNAPSHOTS=1`).
- Frontend lane (Epic 13): `orchestrator/frontend_*.py` (planner, theme, codegen, scaffold, validation, nodes);
  base in `templates/nextjs_base` (regenerate with `make frontend-base`, never edit by hand), overlay in
  `templates/nextjs_overlay` (`overlay.json` = drift manifest). Frontend checks are stored as `frontend:<check>`;
  the frontend has its own git repo (`<workspace>/frontend`), sandbox kind (`for_job(..., "frontend")`) and
  preview kind (`previews.kind`).
- Before the checks (Story 17.5), `orchestrator/autofix.py` restores changed generator-owned files and runs
  `ruff --fix` / `eslint --fix`, committed as `node:autofix`. Frontend sandboxes mount a shared read-only
  node_modules per dependency set (`bga-fe-modules-<key>`, `FRONTEND_SHARED_MODULES`); only `.vite*` folders are
  writable inside it.
- Section renderer (Stories 17.1, 17.2, 17.4): built-in section content is typed (`frontend_spec/section_props.py`);
  a spec the library can render, static or dynamic (`plan["rendering"] == "renderer"`, else `rendererGaps` says
  why), is built without the engine; dynamic data sections read through the generated `bindings.ts`: overlay part `templates/nextjs_overlay/files/renderer` (only the sections a site uses) plus
  `orchestrator/frontend_renderer.py` (site.json, registry, props types, thin route files). Sections can nest in
  layout nodes (`children`): walk them with `iter_sections` / `walk_sections`, never `page["sections"]` alone.
- Custom components (Story 17.3): a rendered site's custom components (with a `propsSchema`) are scaffolded as
  their library fallback (`plan["customComponents"]`), then `orchestrator/custom_components.py` generates each in a
  scratch copy and its own sandbox (`for_job(..., part=...)`), or copies it from the component cache
  (`component_cache` rows + `ARTIFACT_ROOT/cache/components/<key>/`, key in `component_cache.py`), and rewrites the
  owned registry. Admin purge: `DELETE /api/v1/cache/components`.
- Backend CRUD from templates (Story 17.6): `orchestrator/backend_codegen.py` writes models, entities, CRUD modules,
  `src/routers.py` and the API tests from the plan (no engine); the sandbox's ruff formats them and they are recorded
  as owned (`scaffold.add_owned`). The engine only completes what `codegen_gaps` / `database_gaps` name (custom
  operations, rules, auth; one-to-one / many-to-many models), with the `complete_backend` prompt.
  `options.crudFromTemplates=false` restores the engine path (tests of the engine plumbing use it).
- Requirement drafting (Stories 2.4, 12.4): `POST/GET /api/v1/spec-drafts` (`specs` module) stores a `spec_drafts` row
  and queues it on `bga:drafts:<engine>`; the worker's `_consume_drafts` (own slots, `DRAFT_CONCURRENCY`) runs
  `orchestrator/drafting.py` in `<WORKSPACE_ROOT>/drafts/<id>/` (inputs in `.bga/`: schemas, an example from
  `EXAMPLES_DIR`, the section catalogue), validates (+ pair check in dynamic mode), repairs with `repair_spec`, and ends
  SUCCEEDED / NEEDS_REVIEW / FAILED. Usage is kept on the draft (`usage`), not in `model_calls` (those belong to a
  generation); `/usage` reports it as `drafts`. A generation created with `draftId` stores `options.draftId`, and
  packaging writes `requirement.md` / `.txt`. Requirement checks: `modules/shared/domain/requirement.py`.
- Test doubles (fake engine, golden two-entity project, static validator, fake CLIs, opt-in test flags) are listed in
  `docs/development/test-doubles.md`; add any new fake there and mark it at its definition.

## Architecture

Module-based hexagonal (clean) architecture. Each module owns its own layers; shared domain and infrastructure live in `modules/shared/`.

```
src/
├── main.py              # App entry point; lifespan registers routers
├── routers.py           # Central router registry — add new module routers here
├── configs/
│   └── config.py        # Pydantic Settings singleton (reads .env)
│
├── modules/
│   ├── __init__.py      # Import all ORM models here for Alembic autogenerate
│   ├── shared/
│   │   ├── domain/
│   │   │   ├── entities/          # Pure Pydantic domain entities (no ORM)
│   │   │   │   └── user_entity.py
│   │   │   └── value-objects/
│   │   └── infrastructure/
│   │       └── models/            # SQLModel ORM classes (shared across modules)
│   │           └── user_model.py
│   │
│   ├── health/
│   │   ├── ports/input/           # Input port ABCs (use-case interfaces)
│   │   ├── usecases/
│   │   │   └── health_check_usecase.py  # Use-case class + Dep type alias
│   │   └── presenter/
│   │       ├── router.py          # FastAPI router; injects use-case deps
│   │       └── dtos/              # Request/response Pydantic models
│   │
│   └── users/
│       ├── ports/
│       │   ├── input/             # Input port ABCs
│       │   └── output/            # Output port ABCs (IUserRepository)
│       │       └── user_repository.py
│       ├── usecases/
│       │   ├── create_user_usecase.py   # Use-case class + Dep type alias
│       │   └── get_user_usecase.py
│       ├── infrastructure/
│       │   ├── persistence/
│       │   │   └── user_repository.py  # UserRepository + IUserRepoDep binding
│       │   └── adapters/
│       └── presenter/
│           ├── router.py
│           └── dtos/
│
└── libs/
    ├── database/session.py              # DBSessionManager, SessionDep
    ├── repository/base_repository.py    # Optional BaseRepository utility
    ├── exceptions/base_exception.py     # NotFoundException, BadRequestException, etc.
    └── decorators/transactional_decorator.py  # @Transactional decorator
```

## Key Concepts

- **Entity** (`shared/domain/entities/`): Pure Pydantic `BaseModel` — no ORM annotations. Shared across modules.
- **Input port** (`ports/input/`): ABC defining the use-case interface.
- **Output port** (`ports/output/`): ABC defining the repository interface that the use case depends on.
- **Use case** (`usecases/<action>_usecase.py`): Implements business logic. Depends on the output port interface only. Defines its own `<Name>Dep` type alias.
- **Model** (`shared/infrastructure/models/`): SQLModel ORM class. Only the repository touches this.
- **Repository** (`infrastructure/persistence/`): Implements the output port. Maps between ORM model and domain entity. Defines the `I<Name>RepoDep` binding (interface → concrete).
- **Presenter** (`presenter/`): FastAPI router + DTOs. Injects use-case deps and handles HTTP.

## Dependency Injection Pattern

Each layer defines its own `Dep` type alias; downstream layers import and use it:

```python
# infrastructure/persistence/user_repository.py
IUserRepoDep = Annotated[IUserRepository, Depends(UserRepository)]

# usecases/create_user_usecase.py
from src.modules.users.ports.output import IUserRepoDep


class CreateUserUsecase:
    def __init__(self, user_repo: IUserRepoDep): ...


CreateUserUsecaseDep = Annotated[CreateUserUsecase, Depends(CreateUserUsecase)]

# presenter/router.py
from src.modules.users.usecases import CreateUserUsecaseDep


@user_router.post("")
async def create_user(user: CreateUserRequestDto, usecase: CreateUserUsecaseDep): ...
```

For use cases with no repository (e.g. health), `Depends` directly on the concrete class:

```python
HealthCheckUsecaseDep = Annotated[HealthCheckUsecase, Depends(HealthCheckUsecase)]
```

## Adding a New Module

1. Add shared domain types (if cross-module):
   - `src/modules/shared/domain/entities/<name>_entity.py` — pure Pydantic `BaseModel`
   - `src/modules/shared/infrastructure/models/<name>_model.py` — SQLModel ORM class
2. Create `src/modules/<name>/` with:
   - `ports/input/` — input port ABCs *(optional)*
   - `ports/output/<name>_repository.py` — `I<Name>Repository` ABC *(skip if no DB)*
   - `infrastructure/persistence/<name>_repository.py` — concrete repo + `I<Name>RepoDep` *(skip if no DB)*
   - `usecases/<action>_usecase.py` — use-case class + `<Action>UsecaseDep`
   - `presenter/router.py` — FastAPI router
   - `presenter/dtos/<name>_dto.py` — request/response DTOs
3. Import the ORM model in `src/modules/__init__.py` (required for Alembic autogenerate)
4. Run `make newmg name="<description>"`, review, then `make mghead`
5. Register the router in `src/routers.py`

## Key Conventions

- **`@Transactional`**: Apply to use-case methods that write to the database; auto-commits on success, rolls back on exception.
- **Exceptions**: Use custom exceptions from `src/libs/exceptions/base_exception.py` rather than raw `HTTPException`.
- **ORM ↔ Entity mapping**: Repositories map between `<Name>Model` (ORM) and the domain entity. Use cases never import ORM classes.
- **Environment**: Copy `.env.ex` to `.env`. Required vars: `DB_URL`, `JWT_SECRET` (≥ 32 chars). See the root `.env.example`.

## Stack

- **FastAPI 0.124** with `fastapi[standard]` (includes Uvicorn)
- **SQLModel 0.0.27** — ORM models live in `modules/shared/infrastructure/models/` only
- **Alembic 1.17** for migrations
- **PostgreSQL 18** via psycopg 3 (`postgresql+psycopg://` URLs)
- **LangGraph / LangSmith / Redis / Docker SDK** for the generation workflow (later epics)
- **pydantic-settings** for config
