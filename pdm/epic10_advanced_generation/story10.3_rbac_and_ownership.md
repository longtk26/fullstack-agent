# Story 10.3 — Roles and ownership

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-06 · **Depends on:** 10.2

## User story

As a backend consumer, I want role and resource-ownership policies enforced server-side, as declared in the spec;
the contract tells a frontend which roles each operation needs (hiding actions: [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).

## Acceptance criteria

Backend (the `policies` plugin):

- [x] `policies[].type=role` → a `require_roles(*roles)` dependency in `src/libs/security/` (403 `ForbiddenException`
      when the role is missing), through the router-parameter hook.
- [x] Ownership checks live in **use cases** (business logic, per the skill), not routers, through the use-case
      pre-check hook. The use case receives the current user from the router.
- [x] `policies[].type=ownership` with `ownerField` → create sets the owner from the current user (client value
      ignored; `x-bga.source: currentUser`, 10.0b). Get, update and delete check ownership, and list filters to the
      owner's records through the repository-filter hook (admins bypass if configured).
- [x] Non-owner access returns **404** for single resources by default (configurable to 403 per policy), and this is
      documented in OpenAPI responses.
- [x] Template tests per protected operation: owner allowed, other user rejected, role missing rejected.

Contract:

- [x] Each operation carries its roles and whether ownership applies (`x-bga.auth`).
- [x] `allowedActions` (10.0b) drops what the signed-in user may not do: another user's record has no `update` or
      `delete`; a missing role removes its operations. MSW computes the same from its mock users.
- [x] Errors (401, 403, 404 for another user's record) are in `x-bga.errors`, with scenarios: no token, wrong role,
      another user's record.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`, under the user's review. Planned 2026-11-04; frontend half
moved to 22.7 on 2026-11-05.

- **The `policies` plugin** (`orchestrator/plugins/policies.py`, `templates/plugins/policies`, needs `auth-jwt`; on
  when an operation names a policy). Spec additions on `policies[]`: `bypassRoles` (roles that reach every record) and
  `denyStatus` (403 or 404, default 404). An operation with a `policy` now always needs a sign-in (`auth: jwt`).
- **Roles**: `require_roles(*roles)` in auth-jwt's `src/libs/security/roles.py` (403 `FORBIDDEN`, "Your role cannot
  do this"). The route's `current_user` becomes `Annotated[UserEntity, Depends(require_roles("admin"))]`: a later
  plugin's route parameter of the same name replaces an earlier one's (a new framework rule, tested with the probe).
- **Ownership**, in the use cases: get, update and delete check the loaded record's owner (pre-check hook; 404 like
  an unknown id, or 403); lists pass `owned_by` to the repository (repository-filter hook, now scoped to the list
  operations that have the policy); bypass roles see everyone's. The owner field becomes a foreign key to the user
  entity (a relationship is added when the spec has none, so responses carry an `owner` `{id, label}` summary). Create
  takes the owner from `current_user` (`to_entity(owner_id)`); the request DTO accepts and ignores a sent value, the
  update DTO has no owner, and the contract lists it as `readOnly` with `x-bga.source: currentUser`. The engine's note
  says the same for engine-written operations.
- **`allowedActions` per user** (new `action_checks` hook): the response DTO gets `allowed_actions(entity, user)`;
  use cases that have the current user pass it, so another user's record has no `update`, a member's has no `delete`.
- **Template tests**: seeds default the owner to the signed-in test account (`tests/auth.py`: `sign_in(client,
  role=...)`, `current_user_id()`); a role operation's tests sign in with a role it allows (`test_prelude` hook); added
  cases (`test_case` hook): another user's record (get, update), a bypass role reaching it, the list showing only the
  caller's records, and a missing role (403).
- **Contract**: `x-bga.policy` per operation (`{name, type, roles}` or `{name, type, ownerField, bypassRoles, deny}`);
  403 in `x-bga.errors` and the responses; `x-bga.entities[...]` gains `ownerField` and `actionPolicies` (what the
  mocks need to narrow `allowedActions`). Scenarios: "wrong role" (403), "another user's record" (404 or 403), and
  every scenario of a role or ownership operation runs as a demo user it suits (`scenario.user`; the smoke script
  signs each demo user in once). The demo users get a second plain account (`demo-member-2@example.com`).
- **Fixed on the way**: seeds are inserted parents first by foreign key (the user entity comes last in the spec but
  owns records); a create whose only reference is the owner has no bad-reference error or test; the repository's
  `list` signature wraps one parameter per line past 120 characters.

**Deviations:**

- `x-bga.auth` stays `"jwt"` (other code reads it as a string); roles and ownership are in `x-bga.policy`.
- MSW does not compute `allowedActions` per mock user yet: the mocks have no signed-in user until 22.7. The contract
  carries what they need (`actionPolicies`, `ownerField`); 22.7 uses it.
- One policy per operation (the spec's shape): "admins only, and only their own" needs a custom rule (10.4).
- A list scoped by its path (`/projects/{projectId}/tasks`) is owner-filtered too, but gets no "own records" test.

**Verified:** `make lint`; `tests/test_policies.py` (9), the plugin (11), auth, contract and codegen tests; `make test`
(all pass); `BGA_SANDBOX_TESTS=1` for a policy generation through the workflow
(`test_a_backend_with_role_and_ownership_policies_passes_its_tests_and_scenarios`): every check passes on the first
try, ruff clean, 42 template tests, 34 scenarios (run as the admin and the member demo users), 14 operations matching.
`make up`, then a fake-engine backend generation of two-entity with an owned `Task` (`gen_01M6MZR2B0PK0YQ7DEF6R3MBWK`):
COMPLETED; on its preview each member lists only their own tasks and the admin all six; a member gets 404 for the
admin's task (get and update), sees `allowedActions: ["update"]` on their own and the admin `["update", "delete"]`;
a member's delete is 403 `FORBIDDEN`, the admin's 204; a create sending the admin's `ownerId` is owned by the caller;
create without a token is 401; the OpenAPI documents the 403 on delete.
