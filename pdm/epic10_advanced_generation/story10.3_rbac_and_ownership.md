# Story 10.3 — Roles and ownership

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-06 · **Depends on:** 10.2

## User story

As a backend consumer, I want role and resource-ownership policies enforced server-side, as declared in the spec;
as a user of the app, I only see the actions I am allowed to take.

## Acceptance criteria

Backend (the `policies` plugin):

- [ ] `policies[].type=role` → a `require_roles(*roles)` dependency in `src/libs/security/` (403 `ForbiddenException`
      when the role is missing), through the router-parameter hook.
- [ ] Ownership checks live in **use cases** (business logic, per the skill), not routers, through the use-case
      pre-check hook. The use case receives the current user from the router.
- [ ] `policies[].type=ownership` with `ownerField` → create sets the owner from the current user (client value
      ignored; `x-bga.source: currentUser`, 10.0b). Get, update and delete check ownership, and list filters to the
      owner's records through the repository-filter hook (admins bypass if configured).
- [ ] Non-owner access returns **404** for single resources by default (configurable to 403 per policy), and this is
      documented in OpenAPI responses.
- [ ] Template tests per protected operation: owner allowed, other user rejected, role missing rejected.

Frontend (dynamic mode):

- [ ] The contract marks each operation's roles; actions, row actions, Manage area links and navigation the signed-in
      user cannot use are hidden.
- [ ] MSW enforces ownership and roles on the fixtures (records owned by the mock user and by another user).

## Status

**Planned (2026-11-04)**, revised from the first Epic 10 (hooks, field source, frontend half).
