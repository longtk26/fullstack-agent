# Story 1.4 — Agent API authentication & job ownership

**Epic:** [1 — Foundation](epic1_foundation.md) · **Requirements:** FR-14 (access control) · **Depends on:** 1.3 · **Open question:** Q2

## User story

As a user, I want to log in so that only I can see and control my generation jobs and artifacts.

## Acceptance criteria

- [ ] `POST /api/v1/auth/login` returns a JWT access token. `GET /api/v1/me` returns the user.
- [ ] Users are seeded from env (`SEED_USERS=email:password,...`) on startup. No public registration in MVP.
- [ ] `CurrentUserDep` dependency. Every `/api/v1/generations*`, `/spec-drafts*`, `/specs*` and `/previews*`
      route requires auth.
- [ ] Every query is scoped by `owner_id`. Accessing another user's resource returns **404** (not 403),
      so resources are not leaked.
- [ ] `role=admin` can list all jobs (`?scope=all`).
- [ ] SSE endpoints accept the token through the cookie forwarded by the Next.js proxy (see 9.1),
      because `EventSource` cannot set headers.
- [ ] Rate limiting on login (fastapi-skills pillar 2).

## Technical notes

- `JWT_SECRET` comes from env only. The app refuses to start if it is unset or left at the example value.
