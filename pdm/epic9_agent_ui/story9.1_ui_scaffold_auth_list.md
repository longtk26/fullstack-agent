# Story 9.1 — UI scaffold, auth & generations list

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Depends on:** 1.4, 4.1

## User story

As a user, I want to log in and see all my generations with their status, so that I have one place to start
and track work.

## Acceptance criteria

- [ ] App shell built outside-in (sidebar + header + content) with layout primitives and shadcn components. Light/dark tokens.
- [ ] Login through a Server Action. The JWT is stored in an httpOnly `SameSite=Lax` cookie, never in local or session storage.
      Middleware redirects unauthenticated users to `/login`.
- [ ] `lib/api-client.ts` plus Next.js route handlers `/api/proxy/[...path]` forward requests to `API_URL` with
      the cookie token, including SSE streaming passthrough.
- [ ] `/generations`: table (id, project name, engine, status badge, current step, duration, created), status
      filter, cursor pagination, row click → detail. React Query, refetched every 5 s while any row is active.
- [ ] Types follow the skill (`TGeneration`, `TGenerationStatus`). Query key factory in `features/generations/query-keys.ts`.
