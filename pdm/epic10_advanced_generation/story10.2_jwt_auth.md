# Story 10.2 — JWT authentication

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-06 · **Depends on:** 10.1

## User story

As a backend consumer, I want generated backends with working registration, login and protected endpoints when
the spec asks for JWT auth. The dynamic app's sign-in, sign-up and token storage are in [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md).

## Acceptance criteria

Backend (the `auth-jwt` plugin, no engine call):

- [ ] When `spec.auth.type=jwt`, the planner adds a `users` module (the template's sample, which 5.2 removes, is the
      reference shape) with a `User` entity (or extends `auth.userEntity`) holding `email` (unique), `password_hash` and
      `role`, plus operations `auth.register` (201), `auth.login` (200, `{accessToken, tokenType}`) and `auth.me`.
- [ ] Plugin code: `src/libs/security/` (argon2 hashing, PyJWT encode/decode, expiry from env) and `CurrentUserDep =
      Annotated[UserEntity, Depends(get_current_user)]`, following the skill's DI type-alias pattern, contributed to
      routers through the router-parameter hook. Login and register get a stricter per-route rate limit (5.4's
      deferred item).
- [ ] Operations with `auth: jwt` require the bearer token (401 otherwise). OpenAPI declares a `bearerAuth` security
      scheme on exactly those operations; the contract carries `x-bga.auth` per operation.
- [ ] `JWT_SECRET` and `ACCESS_TOKEN_EXPIRE_MINUTES` come from env only. `.env.ex` lists them without real values.
- [ ] Template tests: register, login, `me`, wrong password 401, missing or expired token 401, duplicate email 409.
- [ ] Previews seed a demo user per role; the App tab shows the demo credentials.
- [ ] Manifest `auth` block filled in (7.1).

Agent UI:

- [ ] The try-it explorer's auth helper (9.6): a "Get token" form calls the generated login and fills the bearer.

## Status

**Planned (2026-11-04)**, revised from the first Epic 10 (demo users, 9.6 helper added). Frontend half moved to
22.7 on 2026-11-05.
