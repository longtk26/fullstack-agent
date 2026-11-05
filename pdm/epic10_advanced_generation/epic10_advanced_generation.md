# Epic 10 — Advanced generation: plugins, auth, rules, files, jobs, email, webhooks, payments

## Overview

Re-planned 2026-11-04 with the user. The first version of this epic (auth, policies, rules, stubs for integrations
and jobs) left the engine to write most of it. This version follows what Epic 17 and Epic 21 did for CRUD and
aggregates: **backend features are generation-time plugins** that write known, tested code into the project. The
engine still writes custom operations, custom rules and custom job bodies, but calls the plugins' APIs instead of
inventing auth, queue or payment code.

**Backend only (re-scoped 2026-11-05).** The user's order is backend first; the frontend halves (form kit, pickers,
sign-in, uploads, pay, role-aware actions) moved to [Epic 22](../epic22_dynamic_app_frontend/epic22_dynamic_app_frontend.md), the dynamic app frontend, which builds them once
on its app kit. This epic still puts into the contract everything a frontend needs (field sources, parent summaries,
roles, rules, error fields).

The forms findings below are why the contract gains field sources (10.0b); the frontend fixes are 22.5 and 22.6:

| Finding (code, 2026-11-04) | Effect |
|---|---|
| Form fields have no reference type (`FormField`, `frontend_spec/schema_v1.py`); the contract's schemas do not mark foreign keys (only `x-bga.fixtures` uses them) | A card form asks the user to type a deck's UUID |
| `Form.tsx` maps `date` to the native `<input type="date">`; `datetime` has no input type and becomes a text box; Calendar and Popover are in the base but unused | Dates are hard to enter and look different in every browser |
| Tree forms (`tree-forms.tsx` `guessFields`) take field types from a sample record's JavaScript `typeof`; their form ids are not in `plan["forms"]`, so `formSchemas[formId]` is undefined and no Zod schema validates them | On designed pages every field is a text box, nothing is required, enums lose their values, and nothing is validated |
| Enum labels are the raw values lowercased; booleans are a label over a lone checkbox; `min`, `max`, `maxLength` never reach the input; one `max-w-lg` column, no card, no required marker, no help text, no spinner | The forms look unfinished next to the designed pages |
| Server errors only toast; 409 `ConflictException` from the repository carries no field, 422 `details` (`exc.errors()`) are not mapped | The user cannot see which field was rejected |

**Requirements:** FR-06, FR-07, FR-34 (backend feature plugins), FR-35 (forms that fit the API); requirements v1.8.

## Decisions (2026-11-04)

| # | Decision | Instead of |
|---|---|---|
| P1 | **Generation-time plugins copy plain fastapi-skills source** into the project (overlay-owned, checked by `conventions`), on well-known libraries; each plugin's version goes into the manifest. No plugin framework at runtime, no private `bga-*` package | The engine writing each feature, or a runtime dependency on us |
| P2 | **Six named hook points** in backend codegen: router parameters, use-case pre-checks, use-case events (outbox), repository filters, response fields, app and worker startup. What does not fit goes to the engine, as `codegen_gaps` does today | Patching generated code freely |
| P3 | **Plugins cover both lanes** in dynamic mode: backend files plus the frontend half (client, kit components, form fields, MSW mocks that enforce the same rules). Since 2026-11-05 this epic writes the backend half and the contract; the frontend half is written in 22.7 | Backend-only features the frontend cannot use without the engine |
| P4 | **Every request field has a source** in the contract (`x-bga.source`: `server`, `currentUser`, `route`, `reference`, `upload`, `input`), and the pair check proves every form field has one that works on its page | The frontend guessing from the schema |
| P5 | **Postgres-backed job queue** in the generated backend (`jobs` table, `SKIP LOCKED`, retries, cron) with a **transactional outbox** for events | Redis + `arq` (one more service per preview, and no outbox) |
| P6 | **Payments start with a fake provider** behind an `IPaymentProvider` port (own checkout page, signed webhook); Stripe is a later adapter a developer adds by implementing the port | Stripe first (needs keys in every preview and sandbox) |
| P7 | **Files through MinIO** with signed upload and read URLs, on the S3 API (`boto3` with `endpoint_url`), so S3 is an env change | Uploads through the backend |
| P8 | (frontend, built in 22.7) **Token storage is a runtime flag** in generated frontends: `AUTH_TOKEN_STORAGE=local` (default: token in `localStorage`, bearer header on direct calls) or `cookie` (httpOnly cookie set by Next route handlers, calls through a same-origin proxy that adds the bearer). Read through `/api/runtime-config`, so switching needs an env change and a restart, not a rebuild; both modes are generated and tested. The backend stays bearer-only. An agreed exception to nextjs-skills' "never `localStorage`" rule, for easy previews; the generated README recommends `cookie` for production | One fixed mode |

Out of scope: audit log, soft delete, SSE / realtime (later epic). An integration with no plugin keeps a stub adapter
and an `unresolved` entry (the old 10.4 behaviour, now the plugin framework's fallback).

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`, all twelve stories (Checkpoints A–E), each committed after its
checks: tests, the real sandbox through the workflow, `make up` and a fake-engine generation's preview. What each
story left open is in its **Deviations**; the main ones: drafts do not write auth, emails or webhooks yet (Epic 22);
the local object store is RustFS (MinIO's images are gone); a full parent has no `create:<child>` action; Stripe is
a documented port, not an adapter; MSW applies auth, policies and rules only from 22.7.

## Stories

Five checkpoints; stop for the user's review after each one.

| Checkpoint | # | Story | Depends on |
|---|---|---|---|
| (before) | 18.13 | [`complete_backend` context pack](../epic18_generation_speed/story18.13_backend_context_pack.md) | 18.11 |
| **A: contract and framework** | 10.0b | [Field sources and parent summaries](story10.0b_field_sources.md) | 18.13 |
| | 10.1 | [Plugin framework](story10.1_plugin_framework.md) | 18.13, 10.0b |
| **B: core** | 10.2 | [JWT authentication](story10.2_jwt_auth.md) | 10.1 |
| | 10.3 | [Roles and ownership](story10.3_rbac_and_ownership.md) | 10.2 |
| | 10.4 | [Declarative business rules](story10.4_business_rules.md) | 10.3 |
| **C: infrastructure** | 10.5 | [File storage (MinIO, signed URLs)](story10.5_file_storage.md) | 10.1 |
| | 10.6 | [Background jobs and events](story10.6_jobs_and_events.md) | 10.1 |
| | 10.7 | [Email](story10.7_email.md) | 10.6 |
| **D: integrations** | 10.8 | [Webhooks (outgoing and incoming)](story10.8_webhooks.md) | 10.6 |
| | 10.9 | [Payments (fake provider first)](story10.9_payments.md) | 10.8, 10.4 |
| **E: domain shapes** | 10.10 | [Capacity, no-overlap and unique-together rules](story10.10_concurrency_rules.md) | 10.4 |
| | 10.11 | [Many-to-many and one-to-one relations from templates](story10.11_relations.md) | 10.0b |

10.0a (form kit) moved to Epic 22 as 22.5 on 2026-11-05.

**While the frontend waits for Epic 22**, each checkpoint is verified on the backend: template tests, validation's
smoke checks, the try-it explorer (with 10.2's "Get token" helper) and backend-only generations. Dynamic examples keep
auth and roles off until 22.7, so today's dynamic frontend still works against them; the static golden (22.1) is not
touched by this epic.

## Plugin shape

```
agent-api/templates/plugins/<name>/
  plugin.json            name, version, requirements, env, owned paths
  backend/files/**       copied into the project (src/libs/<name>/, modules, alembic versions, tests)
  frontend/files/**      copied into the frontend (dynamic mode, written in 22.7): client helpers, kit components, mocks
agent-api/src/orchestrator/plugins/<name>.py
  applies(spec)          which spec fields turn it on
  plan / contract        modules, operations, schemas, x-bga sources it adds
  hooks                  contributions to the six hook points
  smoke                  checks for validation ("API works")
  manifest / notes       manifest entry; the API note the engine gets in the context pack (18.13)
```

## Cross-cutting

- **Spec:** additions stay in BackendSpec / FrontendSpec 1.0 (additive, as before): structured
  `backgroundJobs[].trigger`, `emails[]`, `webhooks`, `payments`, `file` / `image` fields, `entities[].displayField`.
  The draft prompts get new versions so drafts can use them. (FrontendSpec additions are Epic 22's.)
- **Validation (18.11):** plugin smoke checks are "API works" checks. A plugin file that fails is generator-owned and
  stops at once (no engine repair).
- **Previews and sandboxes** gain a worker container (10.6) and two shared services started by the agent worker:
  MinIO (10.5) and Mailpit (10.7).
- **Frontend tests (decision FE-TESTS):** generated frontend unit tests, Playwright and journeys stay off in
  validation, as they have been since 2026-11-01, because they made the frontend lane too slow (applies to Epic 22).
- **Test doubles:** the fake payment provider, the console email adapter and any new fake are listed in
  `docs/development/test-doubles.md`.
- **Golden spec:** a new dynamic example (`examples/specs/workshop-bookings.json` + frontend spec) uses every
  plugin: users with roles, workshops with an image, tags and a seat capacity, bookings owned by a user with a status
  transition and one booking per user and workshop, a fake checkout, a confirmation email, an outgoing webhook on
  `booking.paid`, a nightly reminder job.

## After this epic (candidate epics, noted 2026-11-04)

- **Teams and organisations:** workspaces with members and a role per workspace; records scoped to a workspace
  instead of a user (ownership 10.3 is per user).
- **Backend revisions:** change a generated backend's spec and regenerate it in place (Q17). **Database policy
  (agreed 2026-11-04):** when the schema changes, the preview database is cleared and the migrations run again from
  empty, then the seed is loaded; no data migrations between revisions, so a revision can never fail on a migration.

## Epic acceptance

Backend and contract only; the app-level acceptance (no id inputs, calendar dates, errors on fields, the preview walk
through sign-up, booking, upload and payment) is Epic 22's.

- The workshop-bookings BackendSpec generates a backend whose tests prove 401 without a token, 404 for another user's
  booking, 403 without the role, 409 on an illegal transition, and two concurrent bookings for the last seat give one
  201 and one 409.
- Through the try-it explorer on its preview: an image uploads to MinIO with a presigned URL and its signed read URL
  works; paying with the fake provider marks the booking paid, the confirmation email shows in Mailpit, and the
  webhook reaches a test receiver with a valid signature; the nightly job runs on demand.
- Its contract gives every request field a source, every reference its list operation and label, and every operation
  its roles and rules.
- Auth, policies, the deterministic rules (including capacity, no-overlap and unique-together), all relation kinds,
  storage, jobs, email, webhooks and payments are written with no engine call; only custom operations, custom rules
  and custom job bodies go to the engine.
