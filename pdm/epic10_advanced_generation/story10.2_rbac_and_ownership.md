# Story 10.2 — Role & ownership authorization

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-06 · **Depends on:** 10.1

## User story

As a backend consumer, I want role and resource-ownership policies enforced server-side, as declared in the spec.

## Acceptance criteria

- [ ] `policies[].type=role` → a `require_roles(*roles)` dependency in `src/libs/security/` (403 `ForbiddenException` when the role is missing).
- [ ] Ownership checks live in **use cases** (business logic, per the skill), not routers. The use case receives the current user from the router.
- [ ] `policies[].type=ownership` with `ownerField` → create sets the owner from the current user (client value ignored).
      Get, update and delete check ownership, and list filters to the owner's records (admins bypass if configured).
- [ ] Non-owner access returns **404** for single resources by default (configurable to 403 per policy), and this is
      documented in OpenAPI responses.
- [ ] Generated tests per protected operation: owner allowed, other user rejected, role missing rejected.
