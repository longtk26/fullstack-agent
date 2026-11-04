# Story 10.2 — JWT authentication (backend + frontend)

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-06 · **Depends on:** 10.1

## User story

As a backend consumer, I want generated backends with working registration, login and protected endpoints when
the spec asks for JWT auth; as a user of a generated dynamic app, I want to sign up, sign in and be sent to the
login page when my session is missing.

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

Frontend (dynamic mode):

- [ ] FrontendSpec `auth` (reserved since 12.1) → login and register pages from library sections (10.0a form kit),
      a user menu in the shell (signed-in user, sign out).
- [ ] Token storage follows the runtime flag `AUTH_TOKEN_STORAGE` (decision P8), read through `/api/runtime-config`:
      - `local` (default): the token in `localStorage`, sent by `client.ts` as a bearer header on direct calls; routes
        whose operations need auth are guarded in the browser.
      - `cookie`: Next route handlers (`/api/auth/login|register|logout`) call the backend and set or clear an httpOnly,
        `SameSite=Lax` cookie; `client.ts` calls a same-origin proxy (`/api/backend/[...path]`, checks `Origin`) that adds
        the bearer from the cookie and forwards to `API_BASE_URL`; routes are guarded on the server.
      - Either way a 401 clears the session and goes to `/login?next=<path>`. In mock mode both use MSW from the
        browser with an in-memory session (MSW cannot set httpOnly cookies).
      - The generated README and `.env.example` document the flag and recommend `cookie` for production.
- [ ] Journeys and the generated auth tests run in both modes (live); the `conventions` check accepts `localStorage`
      for the auth token only in the `local` mode helper.
- [ ] MSW mocks register, login and `me` in memory and enforce the token on protected operations.
- [ ] Journeys cover sign-up, sign-in and a protected page, on mocks and live.

Agent UI:

- [ ] The try-it explorer's auth helper (9.6): a "Get token" form calls the generated login and fills the bearer.

## Status

**Planned (2026-11-04)**, revised from the first Epic 10 (frontend half, demo users, 9.6 helper added).
