# Story 10.2 — JWT authentication

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-06 · **Depends on:** 10.1

## User story

As a backend consumer, I want generated backends with working registration, login and protected endpoints when
the spec asks for JWT auth. The dynamic app's sign-in, sign-up and token storage are in [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md).

## Acceptance criteria

Backend (the `auth-jwt` plugin, no engine call):

- [x] When `spec.auth.type=jwt`, the planner adds a `users` module (the template's sample, which 5.2 removes, is the
      reference shape) with a `User` entity (or extends `auth.userEntity`) holding `email` (unique), `password_hash` and
      `role`, plus operations `auth.register` (201), `auth.login` (200, `{accessToken, tokenType}`) and `auth.me`.
- [x] Plugin code: `src/libs/security/` (argon2 hashing, PyJWT encode/decode, expiry from env) and `CurrentUserDep =
      Annotated[UserEntity, Depends(get_current_user)]`, following the skill's DI type-alias pattern, contributed to
      routers through the router-parameter hook. Login and register get a stricter per-route rate limit (5.4's
      deferred item).
- [x] Operations with `auth: jwt` require the bearer token (401 otherwise). OpenAPI declares a `bearerAuth` security
      scheme on exactly those operations; the contract carries `x-bga.auth` per operation.
- [x] `JWT_SECRET` and `ACCESS_TOKEN_EXPIRE_MINUTES` come from env only. `.env.ex` lists them without real values.
- [x] Template tests: register, login, `me`, wrong password 401, missing or expired token 401, duplicate email 409.
- [x] Previews seed a demo user per role; the App tab shows the demo credentials. *(Shown in the API tab, next to
      the try-it explorer; the App tab's sign-in screens are 22.7.)*
- [x] Manifest `auth` block filled in (7.1).

Agent UI:

- [x] The try-it explorer's auth helper (9.6): a "Get token" form calls the generated login and fills the bearer.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`, under the user's review.

- **The `auth-jwt` plugin** (`orchestrator/plugins/auth_jwt.py`, `templates/plugins/auth-jwt`). Before planning
  (`Plugin.extend_spec`, new) it gives `auth.userEntity` (added as `User` / `users` when the spec has none) a unique
  login field, a secret `passwordHash` (dropping any `password` field the spec had) and a `role` (an enum of
  `auth.roles`, else a string defaulting to `user`), and seeds one demo user per role (`demo-<role>@example.com`,
  password `demo12345`, a precomputed argon2id hash). The planner adds its own `auth` module (`module["plugin"]`), which
  codegen, the engine path, the completion step and the smoke custom calls leave alone.
- **Generated code**: `src/libs/security/` (pwdlib argon2id, PyJWT HS256 with `ACCESS_TOKEN_EXPIRE_MINUTES`,
  `HTTPBearer(scheme_name="bearerAuth")`, `get_current_user` and `CurrentUserDep`); `src/modules/auth/` (register 201,
  login 200 `{accessToken, tokenType}`, `me`; register and login limited by `AUTH_RATE_LIMIT`, default 10/minute);
  `current_user: CurrentUserDep` on every operation with `auth: jwt` through the router-parameter hook (so they answer
  401 before any code runs). `auth: jwt` is no longer an engine gap; a policy still is (10.3).
- **Secrets**: a column marked `secret` is in the model and entity but never in a request, a response DTO, the
  contract's schemas, a presented example or a mock answer (`x-bga.entities[...].secretFields`).
- **Settings**: `JWT_SECRET` (required, env only), `ACCESS_TOKEN_EXPIRE_MINUTES=60` in `.env.ex`; settings may carry a
  test value, written into the overlay's `tests/conftest.py` (`# {{PLUGIN_TEST_ENV}}`, which also took over the rate
  limiter's line).
- **Contract**: `components.securitySchemes.bearerAuth`, the three auth operations with their errors and scenarios
  (register success / duplicate / missing password, login success / wrong password, `me` signed in), and a first
  `no token → 401` scenario on every protected operation; `x-bga.auth.login` says how to sign in.
- **Validation**: the smoke script signs in as a demo user once and sends the bearer on protected calls, so they are no
  longer skipped. Template tests: the plugin's six auth tests, and an autouse fixture (the new `test_setup`
  contribution) that signs a fresh account in for every test of a module with protected operations.
- **Runner**: the image bakes every plugin's requirements, and `ensure_venv.sh` uses the baked venv when it has every
  line of the project's requirements (was: an exact hash of the base file).
- **Manifest** `auth`: login, register and `me` operations, roles and demo users. **Agent UI**: the API tab shows a
  "Sign in to the API" card (demo users, a "Get token" form against the running preview) and passes the token to the
  try-it explorer (Scalar `authentication.securitySchemes.bearerAuth`).
- **Fixed on the way**: the 429 body is now the error envelope (the handler is synchronous, which SlowAPI's middleware
  needs); backend-only previews get the plugins' seed records even when the spec has no `seed`; a plugin's operations
  do not count as uncovered (no Manage area forms for sign-in).

**Deviations:**

- No `users` CRUD module is added: the plugin's `auth` module holds register, login and `me`; a spec that declares
  operations on the user entity gets them as usual, without the password hash.
- The demo credentials are in the API tab, not the App tab (its sign-in screens are 22.7).
- Drafts do not add `auth` yet (`draft_frontend_spec@v10` still says apps are open by default); a spec with `auth`
  (written or edited) gets it. Drafting auth belongs with Epic 22's sign-in screens.
- The "Get token" helper is checked by `tsc` and ESLint, not clicked in a browser.

**Verified:** `make lint`, `pnpm exec tsc --noEmit`; `tests/test_auth_jwt.py` (8) and the plugin, contract and
integration tests; `make test` (all pass but one coverage test, fixed: plugin operations); `BGA_SANDBOX_TESTS=1` for an
auth generation through the workflow (`test_a_backend_with_jwt_auth_passes_its_tests_and_scenarios`): every check
passes on the first try, baked venv, 37 template tests, 31 scenarios, 14 operations matching the plan and the contract.
`make up`, then a fake-engine backend generation of two-entity with auth (`gen_01M6MXPJQ9TC828BV7YRVX76K1`): COMPLETED
in 40 s; on its preview the demo admin signs in, `me` answers without a password, tasks answer 401 without the token
and 200 with it, a second register is 409 with `details.fields`, the twelfth login in a minute is a 429 envelope, and
the exported OpenAPI declares `bearerAuth` on exactly the six protected operations.
