# Story 22.7 — Plugin frontends: auth, roles, rules, uploads, payments, relations

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-06, FR-07, FR-34, FR-36 · **Depends on:** 22.6, Epic 10

The frontend halves of Epic 10's plugins, moved here on 2026-11-05 so they are built once, on the app kit. Each
plugin keeps its frontend files under `templates/plugins/<name>/frontend/files/` (Epic 10, decision P1); this story
writes them. Static mode has no backend, so none of this reaches static sites.

## User story

As a user of a generated app, I can sign up and sign in, I see only what I may do, the app offers only what the rules
allow, and I can upload files, pay, and link related records, on mocks and on the live backend.

## Acceptance criteria

Auth (10.2):

- [ ] FrontendSpec `auth` (reserved since 12.1) → sign-in and sign-up screens on the form kit (22.5), and a user menu
      in the `AppShell` top bar (signed-in user, sign out).
- [ ] Token storage follows the runtime flag `AUTH_TOKEN_STORAGE` (decision P8), read through `/api/runtime-config`:
      - `local` (default): the token in `localStorage`, sent by `client.ts` as a bearer header on direct calls; routes
        whose operations need auth are guarded in the browser.
      - `cookie`: Next route handlers (`/api/auth/login|register|logout`) call the backend and set or clear an httpOnly,
        `SameSite=Lax` cookie; `client.ts` calls a same-origin proxy (`/api/backend/[...path]`, checks `Origin`) that adds
        the bearer from the cookie and forwards to `API_BASE_URL`; routes are guarded on the server.
      - Either way a 401 clears the session and goes to `/login?next=<path>`. In mock mode both use MSW from the
        browser with an in-memory session (MSW cannot set httpOnly cookies).
      - The generated README and `.env.example` document the flag and recommend `cookie` for production.
- [ ] The `conventions` check accepts `localStorage` for the auth token only in the `local` mode helper.
- [ ] MSW mocks register, login and `me` in memory and enforce the token on protected operations.

Roles and ownership (10.3):

- [ ] Navigation the signed-in user's role cannot use is hidden (`x-bga.auth`); record actions follow
      `allowedActions` (10.3).
- [ ] MSW returns the same `allowedActions` and rejections for records owned by the mock user and by another user;
      10.3's scenarios pass on MSW.

Rules (10.4, 10.10):

- [ ] From `allowedActions`: a status field offers only the `transition:<STATE>` entries; edit and delete are hidden
      on locked records; a full parent (no `create:<child>`) shows "full" and hides its create action.
- [ ] MSW applies the deterministic rules from the same plan definitions with the same codes; 10.4's and 10.10's
      scenarios pass on MSW; a rejection, custom rules included, shows its `x-bga.errors` message on its field (22.5).

Uploads (10.5):

- [ ] An upload field in the form kit (drag and drop, progress, image preview, replace and remove) through the
      presigned URL; images show in lists and details through the signed read URL.
- [ ] MSW answers presign and the `PUT` and keeps the file as a blob URL.

Payments (10.9):

- [ ] A Pay action on the record, success and cancel screens that poll the status; MSW mocks the checkout.

Relations (10.11):

- [ ] A multi-select reference picker (`x-bga.source: reference`, `many: true`); lists and details show related
      records as chips; add and remove through the link operations; MSW and fixtures handle link records.

All:

- [ ] Agent tests check each plugin's generated frontend files, in both auth modes.
- [ ] The workshop-bookings app works in the preview on mocks and live: sign-up, sign-in, a protected page, a booking
      from the workshop's page, an image upload, a fake payment, a status change, and an action hidden without the
      role (checked in the `make up` flow; journeys stay off, decision FE-TESTS).
- [ ] Static golden passes.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (agent-ui), `make test`, `BGA_SANDBOX_TESTS=1 make test`; `make up`, generate
workshop-bookings on the fake engine and walk the flow above in both auth modes.

## Status

**Planned (2026-11-05)**, from the frontend halves of 10.2, 10.3, 10.4, 10.5, 10.9, 10.10 and 10.11.
