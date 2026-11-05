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
  the API contract (`orchestrator/integration/contract.py`) and its checks (`checks/conformance.py`, `checks/consistency.py`)
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
  `orchestrator/frontend/renderer.py` (site.json, registry, props types, thin route files). Sections can nest in
  layout nodes (`children`): walk them with `iter_sections` / `walk_sections`, never `page["sections"]` alone.
- Fonts and variants (Story 17.7): theme fonts in `frontend_spec/fonts.py` are `@fontsource` packages pinned in the
  base and imported by the generated `src/app/fonts.ts`; adding one means `make frontend-base` + `make runner-node`
  (the pnpm store volume is keyed on the base lock, `store_volume()`). Section variants (`background`, Hero
  `variant`, `cardStyle`) live in `section_props.py` and use theme tokens only; `background: "primary"` is the
  `.surface-inverse` token scope in `globals.css`. Library changes keep `templates/nextjs_overlay/DESIGN_CHECKLIST.md`
  (measure with `scripts/design-check.mjs`).
- Custom components (Story 17.3): a rendered site's custom components (with a `propsSchema`) are scaffolded as
  their library fallback (`plan["customComponents"]`), then `orchestrator/frontend/custom_components.py` generates each in a
  scratch copy and its own sandbox (`for_job(..., part=...)`), or copies it from the component cache
  (`component_cache` rows + `ARTIFACT_ROOT/cache/components/<key>/`, key in `frontend/component_cache.py`), and rewrites the
  owned registry. Admin purge: `DELETE /api/v1/cache/components`.
- Backend CRUD from templates (Story 17.6): `orchestrator/backend/codegen.py` writes models, entities, CRUD modules,
  `src/routers.py` and the API tests from the plan (no engine); the sandbox's ruff formats them and they are recorded
  as owned (`scaffold.add_owned`). The engine only completes what `codegen_gaps` / `database_gaps` name (custom
  operations, rules, auth; one-to-one / many-to-many models), with the `complete_backend` prompt.
  `options.crudFromTemplates=false` restores the engine path (tests of the engine plumbing use it).
- Backend completion (Story 18.13): `orchestrator/backend/completion.py`. `module_context` is the context pack the
  `complete_backend@v5` prompt inlines (custom operations with their spec entry and contract operation, schemas
  resolved; the module's generated files; its entity and model; related entities and their repository ports; the
  exception helpers), and the prompt says not to read other files. `complete_modules` runs the modules at once, each
  in a scratch copy (`<workspace>/scratch/module-<name>`), merges their changes in plan order, and reruns a module in
  the project when it changed a file an earlier module changed differently. One module, or `ENGINE_CONCURRENCY=1`,
  runs in the project directly. Frontend `conventions` findings and type errors only in test files are warnings.
- Backend plugins (Story 10.1): `orchestrator/plugins/` (registry, `base.py` contribution types, `app.py`) and
  `templates/plugins/<name>/` (`plugin.json`, `backend/files/**`). The planner records `plan["plugins"]` (dependencies
  first); `scaffold_project(..., plan=)` writes the plugins' files, renders `src/main.py` from the app-startup hook and
  fills the `# {{PLUGIN_SETTINGS}}` line of the overlay's `config.py`, `.env.ex` and `requirements.txt` (with no plan:
  the plugins every project has, i.e. the rate limiter). Codegen calls the module hooks (router params, use-case
  pre-checks and events, repository filters, response fields; 10.3: action checks, test preludes and test cases);
  none contributing leaves the code byte-identical, and a later plugin's route parameter of the same name replaces an
  earlier one's. Integrations without a plugin get a port and a stub adapter (`integration-stubs`). The runner image
  bakes every plugin's requirements, so a project uses the baked venv when it has each of its requirement lines.
- Auth and policies (Stories 10.2, 10.3): `auth-jwt` adds the user entity, demo users (`demo-<role>@example.com` /
  `demo12345`) and its own `auth` module; `policies` adds role checks on routes (`require_roles`), ownership in use
  cases and lists, the owner from the signed-in user (`x-bga.source: currentUser`) and `allowedActions` per user.
  Contract scenarios may name the demo user they run as (`scenario.user`); seeds go in parents-first.
- Business rules (Story 10.4): the `rules` plugin writes `transition`, `immutableAfter` and `sumEquals` from one plan
  definition per rule (`op.ruleChecks`; catalog in `src/libs/rules/catalog.py`); `ownerOnly` is the policies
  plugin's; `custom` rules are the engine's (`op.customRules`: the code it raises), ambiguous ones are skipped
  (`op.skippedRules`). `codegen.engine_rules(op)` is what is left for the engine.
- File storage (Story 10.5): `file` / `image` fields are string columns with `column.file`; the `storage` plugin adds
  `src/libs/storage`, `POST /files/presign`, upload checks and `<field>Url`. Sandboxes and previews of such projects
  share one local S3-compatible store (`src/sandbox/object_store.py`, RustFS `bga-storage` on 127.0.0.1:9100), one
  bucket each, joined to their network as `storage`.
- Jobs (Story 10.6): the `jobs` plugin's queue is PostgreSQL (`src/libs/jobs`, `python -m src.worker [--once]`); CRUD
  use cases emit subscribed events in the request's transaction; previews run `bga-preview-worker-<gen>`; the smoke
  check runs the worker once after its calls. Plugin tables: `plan.pluginModels` / `plan.pluginTables`.
- The integration contract (Story 10.0b): the backend decides, a frontend only reads. Request properties carry
  `x-bga.source` (a foreign key: `reference` with `x-bga.ref`); record responses carry a `{id, label}` summary per
  parent and `allowedActions` (the planner's `label`, `references`, `recordActions`); operations list
  `x-bga.errors` and `x-bga.scenarios`; `x-bga.entities` tells the MSW handlers to present records the same way
  (`presented_record` does it from the contract). The smoke check runs every scenario against the backend, so a new
  rule or plugin adds its scenarios and its `allowedActions` entries in the same place as its backend code.
- Requirement drafting (Stories 2.4, 12.4): `POST/GET /api/v1/spec-drafts` (`specs` module) stores a `spec_drafts` row
  and queues it on `bga:drafts:<engine>`; the worker's `_consume_drafts` (own slots, `DRAFT_CONCURRENCY`) runs
  `orchestrator/drafting/drafts.py` in `<WORKSPACE_ROOT>/drafts/<id>/` (inputs in `.bga/`: schemas, an example from
  `EXAMPLES_DIR`, the section catalogue), validates (+ pair check in dynamic mode), repairs with `repair_spec`, and ends
  SUCCEEDED / NEEDS_REVIEW / FAILED. Usage is kept on the draft (`usage`), not in `model_calls` (those belong to a
  generation); `/usage` reports it as `drafts`. A generation created with `draftId` stores `options.draftId`, and
  packaging writes `requirement.md` / `.txt`. Requirement checks: `modules/shared/domain/requirement.py`.
- Pair fixes (dynamic drafts): the user never fixes the FrontendSpec ↔ BackendSpec pair. `orchestrator/drafting/pair_fixes.py`
  `adapt_backend` (in `autofix_draft`, before every check) makes the BackendSpec follow the pages: a custom operation
  gets the request its form sends or the response its section reads (`type: "array"` for list sections, fields from
  the section or the operation's description), a list the filter / sort / search a page asks for, a create / update
  form's field joins its entity; each change is kept only if the BackendSpec stays valid. After the repair rounds,
  `prune_frontend` cuts what the pair check still rejects (action, binding, parameter, field). Both write notes.
- Draft engine (Story 18.10): `engines/gemini_api/` drafts specs with one `generateContent` request per step (no
  agent loop); it has `inline_inputs` (drafting renders the inline prompt versions `draft_frontend_spec@v10`,
  `draft_spec@v4`, `repair_spec@v3`, `repair_direction@v2`, inputs in the prompt) and `drafts_only` (refuses code
  purposes; the engine list marks it). Answers are one JSON envelope of `files` and RFC 6902 `patches`
  (`libs/jsonpatch.py`). `DRAFT_ENGINE` / `registry.draft_default` pick it for drafts; generation keeps the CLI
  engines. A repair round whose errors repeat the previous round's ends the loop. `docs/engines/gemini-api.md`.
- Designed pages (Epic 21): a page may be an element **tree** (`FrontendSpec` `pages[].tree` + `css`, `layout.chrome`
  / `footerTree`; `TreeNode` in `schema_v1.py`), as Frontend-Agent's site JSON writes it. `frontend_spec/trees.py`
  classifies node types (elements, shadcn primitives, Lucide icons, library sections, data components), checks the
  rules (theme-token colours, no fixed, one h1, assets, links, node and depth limits) and repairs what it can
  (`fix_trees`, run by `autofix_frontend_spec`); `tree_bindings.py` binds data components to a collection (static)
  or to the contract's operations (dynamic; `Metric` / `Chart` to **aggregate** operations, else computed from the
  list) and derives the operations a BackendSpec needs (`derive_operations`). `frontend_renderer.tree_site` writes
  the classified tree into `site.json`; the overlay's `renderer/tree/` (copied only when `plan["trees"]`) renders it
  (`TreeRenderer.tsx`, data components in `tree-data.tsx`, `tree-metrics.tsx`, `tree-forms.tsx`). Drafting designs
  each page with `draft_tree@v1` after the spec is valid (`orchestrator/drafting/trees.py`; `FRONTEND_TREES`), in
  parallel on an API engine; a page whose tree fails keeps its sections. BackendSpec `type: "aggregate"` operations
  are templated like CRUD (`backend/planner.py`, `backend/codegen.py`, the contract and the mock compute them).
- Design direction (Stories 12.6, 20.4, 20.9): the drafting engine writes three direction cards in `notes.json`
  (`design.cards`: concept, tone, hero layout, fonts, colours, key visual, forms, rhythm, `home` section ids, fit);
  `orchestrator/drafting/design_cards.py` checks and fills them (bundled fonts, AA contrast, `design_tone` tokens), runs the
  difference test (`repair_direction` prompt, at most 2 rounds, then a code fix) and keeps the drafted home sections
  as `spec_drafts.design.pool`; drafting applies the best fit after the spec repairs (`finish_design`).
  `orchestrator/drafting/design_direction.py` (UI UX Pro Max's vendored data, `make design-data`) is the floor: the category
  default in the fact pack `.bga/design.md`, the palette for cards that miss contrast, the directions when the engine
  wrote no cards. `apply_direction` / `compose_home` are mirrored by the UI's `lib/design-direction.ts`
  (`tests/test_design_cards.py` runs both on the same cases with Node). Stock phrases in headings and buttons
  (`frontend_spec/copy_rules.py`) are `FE_DESIGN_RULE` warnings and get one repair round.
- Design diversity (Epic 20): hero `variant` has 8 layouts, list sections a `form`, pages a `rhythm`, and seven
  content sections joined the library (Steps, Timeline, Team, PriceList, Location, Comparison, Statement), all in
  `section_props.py` with theme tokens only. Optional theme tokens (`surface`, `colorArea`, `typography.headingWeight
  / headingCase / tracking / ratio`) are drawn by `frontend/theme.py` (`heading` utility, `--hero-<step>` sizes
  shrunk by `display_scale` for wide faces) and by `frontend/renderer.py` (`color_roles`, `alternate_backgrounds` in
  `site.json`); `orchestrator/drafting/design_tone.py` maps a five-scale tone to them. Without the new fields a spec plans
  exactly as before and renders the same sizes and weights (`globals.css` gains the variables at today's values).
  Icons (20.5): items take `icon` (`lucide:` / `phosphor:` reference or `intent:` words), resolved to `theme.icons.set`
  when the site is generated (`frontend_spec/icons.py`, index `templates/nextjs_base/icon-index.json` from
  `scripts/icon-index.mjs`); `frontend_renderer.icons_ts` imports only the used icons; the library draws them with
  `sections/Icon.tsx`. Motion (20.6): `theme.motion` (`feel`, `signature`) → `frontend/motion.py` (spring presets as
  CSS `linear()`, rules under `html[data-motion="on"]`), `site.json` `motion`, `PageRenderer`'s inline script and
  `MotionRoot.tsx` (reveals). Dev tools: `make design-check-fixture` (`--motion`), `make design-diversity`
  (`docs/development/design-checks.md`).
- Site images (Epic 15): asset sources and render modes in `frontend_spec/assets.py`; the registry
  `src/assets/index.ts` (`frontend/asset_registry.py`) and the overlay's `components/assets/AssetImage.tsx`. `generate_assets`
  (`frontend/assets.py`) draws all `source: "generate"` assets in one engine call in a scratch dir (cache in
  `ARTIFACT_ROOT/asset-cache/`), `frontend/svg_assets.py` checks SVGs (`frontend:assets`, before build) and converts them to
  components; failing drawings fall back to placeholders (`asset_fallbacks` → COMPLETED_WITH_WARNINGS). Uploads
  (`modules/uploads`) live under `UPLOAD_ROOT`, are copied to `public/assets/` by `scaffold_frontend`.
- Test doubles (fake engine, golden two-entity project, static validator, fake CLIs, opt-in test flags) are listed in
  `docs/development/test-doubles.md`; add any new fake there and mark it at its definition.

## Orchestrator layout

`src/orchestrator/` (the generation workflow) is split by lane:

| Folder | What |
|---|---|
| `orchestrator/` | workflow core: `graph.py`, `runner.py`, `state.py`, `context.py` (JobContext and the helpers nodes share), `store.py`, `tracing.py`, `workspace.py`, `worker_service.py`, `bootstrap.py`; `nodes.py` (the node table, `package_artifacts`), `autofix.py`, `packaging.py`, `previews.py`; `checks/` (pure checks both lanes use) |
| `backend/` | `nodes.py` (validate_spec … repair_code), `planner.py`, `scaffold.py`, `codegen.py` (CRUD from templates), `completion.py` (engine completion), `migrations.py`, `validation.py` |
| `frontend/` | `nodes.py`, `planner.py`, `scaffold.py`, `codegen.py`, `renderer.py`, `theme.py`, `motion.py`, `assets.py`, `asset_registry.py`, `svg_assets.py`, `custom_components.py`, `component_cache.py`, `context_pack.py`, `validation.py` |
| `integration/` | `nodes.py` (validate_inputs, build_contract), `contract.py`, `integrate.py` (live switch and checks) |
| `drafting/` | `drafts.py` (spec drafts), `trees.py` (designed pages), `pair_fixes.py`, `design_cards.py`, `design_direction.py`, `design_diversity.py`, `design_tone.py` |

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
