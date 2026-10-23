# Story 9.1 — UI scaffold, auth & generations list

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Depends on:** 1.4, 4.1

## User story

As a user, I want to log in and see all my generations with their status, so that I have one place to start
and track work.

## Acceptance criteria

- [x] App shell built outside-in (sidebar + header + content) with layout primitives and shadcn components. Light/dark tokens.
- [x] Login through a Server Action. The JWT is stored in an httpOnly `SameSite=Lax` cookie, never in local or session storage.
      Middleware redirects unauthenticated users to `/login`.
- [x] `lib/api-client.ts` plus Next.js route handlers `/api/proxy/[...path]` forward requests to `API_URL` with
      the cookie token, including SSE streaming passthrough.
- [x] `/generations`: table (id, project name, engine, status badge, current step, duration, created), status
      filter, cursor pagination, row click → detail. React Query, refetched every 5 s while any row is active.
- [x] Types follow the skill (`TGeneration`, `TGenerationStatus`). Query key factory in `features/generations/query-keys.ts`.

**Status (2026-10-23):** done. Login is the `loginAction` Server Action; the JWT lives only in the httpOnly
`bga_token` cookie (`COOKIE_SECURE=true` adds `Secure` when served over HTTPS). Next 16 renamed middleware to
`src/proxy.ts`; it does the optimistic cookie check, and a 401 from the API clears the cookie and returns to `/login`.
The BFF route `app/api/proxy/[...path]` forwards only to `/api/v1/*` and streams SSE through unbuffered.
