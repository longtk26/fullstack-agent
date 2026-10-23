# Story 5.4 — Module generation: ports, use cases, DTOs, routers (`generate_backend`)

**Epic:** [5 — Backend generation](epic5_backend_generation.md) · **Requirements:** FR-05, FR-17 (stable operationIds) · **Depends on:** 5.3

## User story

As the workflow, I want one hexagonal module per entity generated following the skill's "Adding a New Feature
Module" steps, so that the API matches the spec exactly and the code matches your conventions.

## Acceptance criteria

- [ ] Engine call(s) with scope `src/modules/<entities>/**` and `src/routers.py`, batched per entity (one module
      per call) to stay within turn limits. Each module contains:
  - output port `I<Entity>Repository(ABC)` and its implementation with `SessionDep`, `__to_entity`/`__to_model`
    mappers, `flush()` on mutations, and `I<Entity>RepoDep`
  - one use case per operation, depending only on the port. Writes are decorated with `@Transactional`. Errors are
    `NotFoundException`/`BadRequestException`/`ConflictException`/`ForbiddenException`, never a raw `HTTPException`.
    Each use case exports `<Action><Entity>UsecaseDep`.
  - request DTOs with `to_entity()`, response DTOs, list response `{items, total, limit, offset}`
  - `<entity>_router = APIRouter(prefix=…, tags=[…])`, registered in `src/routers.py` (`all_router`)
- [ ] CRUD semantics: create → 201, get → 200/404, list → 200 with pagination (`limit`/`offset`, `total`),
      update (PATCH partial) → 200/404, delete → 204/404. Custom operations get a use case that implements the rule,
      or raises and is listed in `unresolved`.
- [ ] Filtering on declared `filters[]`, sorting on declared `sort[]` (`?sort=-date`), and `q` search on declared
      search fields (2.5). An invalid sort field → 422.
- [ ] Each route sets `operation_id="<operationId>"` exactly, plus `response_model` and `responses` for error codes.
      Sensitive routes (auth, writes) get rate-limit decorators.
- [ ] Deterministic post-check: OpenAPI exported from the **started** app (routers register in lifespan, see 6.2)
      contains every planned `(method, path, operationId)` and nothing extra. Mismatches → validation errors.
- [ ] Commit `node:generate_backend`.
