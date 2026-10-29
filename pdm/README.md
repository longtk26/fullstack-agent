# Fullstack Generation Agent — Product Backlog

Source: [requirements.md](../requirements.md) (v1.4, updated to match this backlog). Created 2026-10-23,
extended 2026-10-26 with frontend generation (Epics 12–14, Stories 9.7–9.8) and 2026-10-27 with site images and
revisions (Epics 15–16) and 2026-10-28 with fast generation (Epic 17).

## What we are building

A local-first agent that turns a **natural-language requirement**, a **BackendSpec JSON**, a **FrontendSpec
JSON**, or an imported **Frontend-Agent site JSON** (e.g. [`revue-de-mode.json`](../examples/frontend/revue-de-mode.json))
into tested, running software. The user first picks a **generation mode**:

| Mode | Output |
|---|---|
| **Backend API only** | a FastAPI backend (fastapi-skills), running as its own container |
| **Static website** | a Next.js site (nextjs-skills) with content baked in — no backend |
| **Dynamic web app** | frontend **and** backend generated **in parallel** from one API contract; the frontend runs on mocks (`MOCK_TEST_API=true`) until the backend is healthy, then switches to the real API |

A Next.js UI covers mode choice, input and spec review (pages, theme, components), live workflow steps for each
lane, tracing, results, and an OpenAPI explorer that sends test calls to the running generated backend.

## Runtime topology (docker compose)

```
                         REST + SSE                       enqueue / pub-sub
  browser ─▶ agent-ui ─────────────────▶ agent-api ◀──────────────────────▶ redis
            (Next.js :3000)             (FastAPI :8000)                       ▲
                │                             │ SQL                          │ dequeue
                │ try-it (CORS)               ▼                              │
                │                        postgres ◀──── checkpoints ──── agent-worker
                │                     (jobs + LangGraph)                (LangGraph + engine CLIs:
                ▼                                                        claude / agy)
   ┌──────────────────────────┐                                               │ docker.sock
   │ preview-<genId>  :18xxx  │◀──────────── docker run (after COMPLETED) ────┤
   │ preview-db-<genId>       │                                               │
   │ preview-fe-<genId> :18xxx│  frontend preview (MOCK_TEST_API → backend)   │
   └──────────────────────────┘    ┌──────────────────────────┐               │
                                   │ sandbox-<genId>          │◀── docker run ┘
                                   │ sandbox-db-<genId>       │   (ruff / alembic / pytest;
                                   │ sandbox-node-<genId>     │    pnpm / tsc / next build / playwright)
                                   └──────────────────────────┘
```

- **compose-managed:** `postgres`, `redis`, `agent-api`, `agent-worker`, `agent-ui`.
- **worker-managed (dynamic):** per-job `sandbox-*` containers for validation, and per-generation
  `preview-*` containers that keep the generated backend running for clients.
- **Dev mode:** `make dev` runs only postgres + redis in Docker. api, worker, and ui run on the
  host with hot reload. `make up` runs the full stack and is how you verify.

## Conventions

| Area | Convention |
|---|---|
| Agent API + worker | `.agents/skills/fastapi-skills`: bootstrapped from the `feat/fastapi` template; hexagonal modules, SQLModel, `@Transactional`, `BaseException` hierarchy, DI type aliases |
| Agent UI | `.agents/skills/nextjs-skills`: pnpm, shadcn/ui, React Query, Zustand, RHF + Zod, cookie-based auth through Server Actions |
| Generated frontends | **nextjs-skills** (Epic 13): pinned Next.js base + overlay, theme tokens from the FrontendSpec, typed API client and MSW mocks generated from the contract |
| Generated backends | **Also fastapi-skills** (decision Q1). Each project starts from the `feat/fastapi` template at a pinned commit plus our *overlay* (tests, ruff, entrypoint), and the skill is copied into the workspace so the engine follows it. Hexagonal `src/modules`, SQLModel, Alembic, Pydantic v2, Pytest, Ruff |
| Code engines | Pluggable `CodeEngine` port: **Claude Code CLI** (default) and **Antigravity CLI** (`agy`) |
| Story DoD | ACs met · unit tests for new logic · `make up` still boots green · API changes documented in OpenAPI |

## Epics

| # | Epic | Req. phase | Stories |
|---|---|---|---|
| 1 | [Foundation & local stack](epic1_foundation/epic1_foundation.md) | Phase 1 | 4 |
| 2 | [BackendSpec schema, validation & drafting](epic2_backend_spec/epic2_backend_spec.md) | Phase 1 | 5 |
| 3 | [Code engine adapters (Claude Code + Antigravity)](epic3_code_engine_adapters/epic3_code_engine_adapters.md) | Phase 1 | 4 |
| 4 | [LangGraph workflow & generation jobs](epic4_workflow_and_jobs/epic4_workflow_and_jobs.md) | Phase 1 / 4 | 6 |
| 5 | [Backend generation](epic5_backend_generation/epic5_backend_generation.md) | Phase 2 | 5 |
| 6 | [Validation & repair](epic6_validation_and_repair/epic6_validation_and_repair.md) | Phase 3 | 3 |
| 7 | [Artifacts & preview container](epic7_artifacts_and_preview/epic7_artifacts_and_preview.md) | Phase 4 | 4 |
| 8 | [Observability & tracing](epic8_observability/epic8_observability.md) | Phase 4 | 4 |
| 9 | [Agent UI](epic9_agent_ui/epic9_agent_ui.md) | cross-phase | 10 |
| 10 | [Advanced generation (auth, policies, rules)](epic10_advanced_generation/epic10_advanced_generation.md) | Phase 5 | 4 |
| 11 | [Hardening, benchmark & release](epic11_hardening_and_release/epic11_hardening_and_release.md) | DoD §10 | 4 |
| 12 | [Generation modes, FrontendSpec & API contract](epic12_contract_and_frontend_spec/epic12_contract_and_frontend_spec.md) | Phase 6 | 5 |
| 13 | [Frontend generation (Next.js on nextjs-skills)](epic13_frontend_generation/epic13_frontend_generation.md) | Phase 6 | 5 |
| 14 | [Parallel generation & live-API switch](epic14_parallel_generation/epic14_parallel_generation.md) | Phase 6 | 3 |
| 15 | [Site images & illustrations](epic15_site_assets/epic15_site_assets.md) | Phase 7 | 5 |
| 16 | [Site revisions & feedback](epic16_site_revisions/epic16_site_revisions.md) | Phase 7 | 5 |
| 17 | [Fast generation: section renderer, component cache, templated CRUD](epic17_fast_generation/epic17_fast_generation.md) | Phase 7 | 6 |

### Suggested delivery order

Build a thin end-to-end skeleton first, then fill it in. The `FakeEngine` (3.1) allows the UI and
workflow to be built before real generation works.

1. E1 → E2 (2.1–2.3) → E3 (3.1, 3.2) → E4 → **E9 (9.1–9.3)**: you can submit a spec and watch fake steps live.
2. E6.1 (sandbox) → E5 → E6.2–6.3 → E7: real generation, validation and repair, then artifacts and a running preview container.
3. E8 (8.1–8.4) → E9 (9.4–9.6, 9.10): tracing with per-node time / model calls / cost, the Usage & traces page, and the OpenAPI try-it explorer.
4. E2 (2.5 frontend JSON import, 2.4 requirement drafting) + E9 (Import tab), E3 (3.3 Antigravity), E10, E11.
5. **Frontend generation (added 2026-10-26):** E7.1 + E7.3 (backend preview, needed for the live switch) →
   E12.1–12.3 + 12.5 (FrontendSpec, modes, contract) → E13 (static mode first: 13.1–13.5 without the API
   client) → E13 dynamic parts (client + mocks) → E14 (parallel lanes, `MOCK_TEST_API` switch, live smoke) →
   E12.4 + 2.4 (requirement drafting for both specs) → E9.7–9.9 (mode choice, parallel view, App tab).
6. **Site images and revisions (added 2026-10-27):** 9.7a (spec editor, both epics build on it) → E14 →
   E15 (15.1–15.3 generated SVGs, then 15.4 uploads; 15.5 only if asked) → E16 (16.1 revisions → 16.2 spec
   edits → 16.3 feedback → 16.4 inspect mode → 16.5 history). E11 (hardening & release) stays last.
7. **Fast generation (added 2026-10-28):** E17 before E15/E16, since both get simpler on the renderer:
   17.5 (auto-fix, pre-installed deps) → 17.1 → 17.2 (static, no engine call) → 17.4 (dynamic data sections;
   moved before 17.3 on 2026-10-29: the custom components in the examples are all dynamic data components) →
   17.3 (custom components + cache) → 17.6 (backend CRUD from templates) → 17.7 (fonts, section variants).

### Status (2026-10-28)

| Epic | State |
|---|---|
| 1, 2 (2.1–2.3, 2.5), 3, 4, 5, 6 (6.1–6.2) | done (merged to `main`); 6.3 repair loop works on real failures |
| 7 | done (merged to `main`) |
| 8 | done (8.4 draft-job accounting waits for 2.4 / 12.4) |
| 9 | 9.1–9.6, 9.7a, 9.8, 9.9 and 9.10 done (9.6 auth helper waits for Epic 10); 9.7b open |
| 12 | 12.1–12.3 and 12.5 done; 12.4 open |
| 13 | done |
| 14 | done (14.1 parallel lanes, 14.2 live-API switch + `/integration/{recheck,use-mocks}`, 14.3 live contract & Playwright smoke checks) |
| 17 | 17.5, 17.1, 17.2, 17.4, 17.3, 17.6 done (auto-fix, shared node_modules; typed content and layout nodes; static sites ~44 s and dynamic frontends rendered without the engine; parallel custom components & component cache; backend CRUD from templates, dynamic shop 59 s with 0 engine calls); 17.7 open; a 17.3 layout follow-up is pending |
| 2.4, 10, 11, 15, 16 | open |

### Next up (agreed 2026-10-28, after Epic 14)

Done since the last plan: 9.7a (generate from the UI), Epic 14 (parallel lanes, live-API switch, live smoke), and 9.8 + 9.9 (parallel run view, live switch controls, and embedded App preview tab).
Work in this order; start each item in a fresh session ("implement story 17.5", "implement story 17.1", …).

| # | Item | What the user gets | Why at this point |
|---|---|---|---|
| 1 | **9.8 + 9.9** *(done)* | Parallel lane view with the Mock/Live switch; App tab to use the generated app inside the agent UI | Epic 14 is done, so its lanes and switch can be shown; 16.4 inspect mode lives in the App tab |
| 2 | **Epic 17**: 17.5 → 17.1 → 17.2 → 17.4 → 17.3 → 17.6 (17.7 after the main feature) | Faster runs: auto-fix and pre-installed deps first (every mode), then static sites with no engine call for catalogue sections, cached custom components, dynamic data sections, backend CRUD from templates | Engine calls are >90% of a run (static ~25 min, backend ~17 min); Epics 15 and 16 build on the renderer |
| 3 | **Epic 15** (15.1–15.4) | Real images: engine-drawn SVGs, uploads, links (15.5 only if asked) | Assets become section props on the renderer |
| 4 | **Epic 16** | Revisions: theme and content editors, click-to-comment, history and restore | Spec edits and catalogue feedback are a JSON patch + re-render after 17.2; uses 9.9 and 15 |
| 5 | **2.4 + 12.4, then 9.7b** | Requirement → draft specs; review aids in the editor | May move up if starting from text matters more than speed |
| 6 | **Epic 10**, then **Epic 11** | Auth, roles and business rules in generated backends; hardening, benchmark, release | Epic 11 stays last |

Open decisions along the way:
- Whether to move drafting (2.4 + 12.4) up.
- One paid real-engine run (Claude Code) on `shop-dynamic` to confirm real engines handle the frontend lane and to
  record a timing baseline for Epic 17 (so far the frontend lane has real timings from Antigravity only). Only
  when the user asks.

## Decisions (2026-10-23 review)

| # | Decision | Impact |
|---|---|---|
| Q1 | Generated backends use **fastapi-skills**, the same foundation as the agent service | Epic 5 rewritten around template + overlay. Paths in 3.4, 6.x, 7.x and 10.x follow `src/modules/…`. A new `conventions` validation check enforces the skill's 6 pillars. |
| Q5 | The UI imports Frontend-Agent site JSON and generates an example BackendSpec from it | New Story 2.5 (converter), Import tab in 9.2, optional `seed[]` in BackendSpec (2.1) so previews serve the site's real records |
| Q8 | `git init` done at the repo root (branch `main`, `.gitignore` added) | – |
| PG | **PostgreSQL 18** everywhere (agent DB, sandbox DB, preview DBs) | Volumes mount at `/var/lib/postgresql` (PG 18 image layout) |
| FE (2026-10-26) | **Frontend generation is in scope**: modes `backend` / `static` / `dynamic`; dynamic generates frontend and backend in parallel from a contract, frontend on mocks until the backend is healthy (`MOCK_TEST_API` switch); the UI asks static vs dynamic first | New Epics 12–14, Stories 9.7–9.8; requirements v1.2 (FR-21…FR-27); §1.3 no longer excludes frontend generation |
| Q4 (2026-10-26) | Antigravity also supports the **`agy` account login** (`ANTIGRAVITY_AUTH=account`): works headless on the host (dev worker); in Docker it reports unavailable, use `GEMINI_API_KEY` or ADC there | Story 3.3 updated; account login verified; own turn/time limits (`ANTIGRAVITY_MAX_TURNS`, `ANTIGRAVITY_TIMEOUT_SECONDS`) |
| Q6 (2026-10-26) | Backend previews **start automatically** on COMPLETED; 2 h idle TTL, max 3 running, host ports 18000–18099 bound to `127.0.0.1` | Epic 7 (7.3, 7.4) defaults |
| Q12 (2026-10-26) | The frontend lane uses our own **FrontendSpec** (easier for the agent); the Frontend-Agent site JSON stays an *input* (2.5), no converter | Epic 12 as written |
| Q13 (2026-10-26) | **v0-style preview:** when a generation completes, the user sees the generated site running and can click through it inside the agent UI (App tab, real backend in dynamic mode). Dynamic: Node standalone server (runtime `MOCK_TEST_API` switch); static: nginx serving the export | 13.5, 9.9 (auto-opens the App tab on completion) |
| Q14 (2026-10-26) | Backend lane fails in dynamic mode → **`COMPLETED_WITH_WARNINGS`** (frontend usable on mocks) | 14.1, 14.2 |
| Q11 (2026-10-26) | Frontend base = **`pnpx create-next-app`** exactly as nextjs-skills prescribes (versions pinned by the lock file) + our overlay; no template repo | 13.2 |
| IMG (2026-10-27) | Site images: **SVG illustrations drawn by the code engine** in the theme's colour variables (no new provider or key); uploads and links for photos and logos; AI raster images only as an optional, opt-in provider; icons from `lucide-react` | New Epic 15; FrontendSpec `assets[]` gains sources `generate` / `upload:` / `lucide:` (additive, still 1.0) |
| REV (2026-10-27) | Feedback becomes **revisions**: small jobs on the finished frontend, one commit each, validated and redeployed; spec edits (theme, content, assets) need no engine call; frontend only; the contract stays fixed | New Epic 16; artifacts gain `frontend.bundle` and per-revision ZIPs |
| SPEED (2026-10-28) | Generation is made faster by **doing less with the engine**: catalogue sections are rendered from the FrontendSpec by a section library in the overlay, custom components are generated in parallel and cached by content once validated, backend CRUD comes from templates | New Epic 17; requirements v1.4 (FR-30) |
| Q18 (2026-10-28) | FrontendSpec nesting: **only layout nodes** (`Columns`, `Stack`, `Grid`, `Tabs`) hold sections as children, **depth ≤ 3**; no element trees. Sections lay out their own insides, so layout nodes only arrange sections | 17.1 |
| Q19 (2026-10-28) | **Keep the code engine** for custom components (one call each, in parallel, cached) | 17.3 |
| Q20 (2026-10-28) | Component cache is **shared by all users, exact key only**; no similarity matching | 17.3 |
| Q15 (2026-10-26) | Product renamed **Fullstack Generation Agent** (docs, UI, `APP_NAME`, LangSmith project). Internal identifiers stay: `bga-runner`, `.bga/`, compose project `bga`, schema `$id`s, repo folder | – |

## Changes from requirements v1.0 (accepted via Q1; now part of v1.1)

| Requirement | Was | Now |
|---|---|---|
| §6 generated project structure | `app/{core,api,models,schemas,services,repositories}` | fastapi-skills `src/{configs,libs,modules/<module>/{ports,usecases,infrastructure,presenter}}` |
| §2 generated ORM "SQLAlchemy 2.x" | SQLAlchemy declarative models | SQLModel (built on SQLAlchemy 2.x) |
| FR-16 `.env.example` | `.env.example` | `.env.ex` (template name) |
| FR-16 "dependency manifest (`pyproject.toml`)" | `pyproject.toml` | `requirements.txt` (+ `requirements-dev.txt`) as in the template. `pyproject.toml` holds only ruff and pytest config. |
| FR-17 manifest | – | Manifest adds `architecture: "fastapi-skills-hexagonal"` and `templateRef: <commit sha>` so the Integration Agent knows the layout |

## Open questions (please answer during review)

| # | Question | My default if unanswered |
|---|---|---|
| Q3 | *(default applied in Epic 3)* Claude Code auth: `ANTHROPIC_API_KEY`, or a read-only subscription credentials file (`CLAUDE_CREDENTIALS_HOST_FILE`) | Keep? |
| Q2 | Agent API auth: seeded local users + JWT (meets FR-14 ownership), or a single static API key for local use? | Seeded users + JWT (Story 1.4) |
| Q7 | Do you have a LangSmith API key and project? Tracing is a no-op without one. | Optional. Works without it, and the local trace store (8.3) still feeds the UI. |
| Q9 | Template fixes such as tests, ruff, `ConflictException` and the migrate-on-start entrypoint live in our overlay. Should they go upstream into `longtk26/template-frameworks@feat/fastapi` instead, so the overlay shrinks? | Overlay now; upstream later as a separate PR to your template repo |
| Q16 | Which raster image provider for 15.5, if any? | Build 15.5 only when asked; Gemini image model first (key already used by Antigravity), behind a port |
| Q17 | Should revisions also cover the backend (and contract changes in dynamic mode)? | Not in Epic 16; a later epic once frontend revisions prove out |
| Q10 | The template registers routers inside `lifespan`, so `app.openapi()` is empty unless the app has started. Should the overlay move router registration to module level? | No. Keep the template as-is and export OpenAPI inside a started app (6.2). |
