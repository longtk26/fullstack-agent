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

- [x] FrontendSpec `auth` (reserved since 12.1) → sign-in and sign-up screens on the form kit (22.5), and a user menu
      in the `AppShell` top bar (signed-in user, sign out).
- [x] Token storage follows the runtime flag `AUTH_TOKEN_STORAGE` (decision P8), read through `/api/runtime-config`:
      - `local` (default): the token in `localStorage`, sent by `client.ts` as a bearer header on direct calls; routes
        whose operations need auth are guarded in the browser.
      - `cookie`: Next route handlers (`/api/auth/login|register|logout`) call the backend and set or clear an httpOnly,
        `SameSite=Lax` cookie; `client.ts` calls a same-origin proxy (`/api/backend/[...path]`, checks `Origin`) that adds
        the bearer from the cookie and forwards to `API_BASE_URL`; routes are guarded on the server.
      - Either way a 401 clears the session and goes to `/login?next=<path>`. In mock mode both use MSW from the
        browser with an in-memory session (MSW cannot set httpOnly cookies).
      - The generated README and `.env.example` document the flag and recommend `cookie` for production.
- [x] The `conventions` check accepts `localStorage` for the auth token only in the `local` mode helper.
- [x] MSW mocks register, login and `me` in memory and enforce the token on protected operations.

Roles and ownership (10.3):

- [x] Navigation the signed-in user's role cannot use is hidden (`x-bga.auth`); record actions follow
      `allowedActions` (10.3).
- [x] MSW returns the same `allowedActions` and rejections for records owned by the mock user and by another user;
      10.3's scenarios pass on MSW.

Rules (10.4, 10.10):

- [ ] From `allowedActions`: a status field offers only the `transition:<STATE>` entries; edit and delete are hidden
      on locked records; a full parent (no `create:<child>`) shows "full" and hides its create action.
- [x] MSW applies the deterministic rules from the same plan definitions with the same codes; 10.4's and 10.10's
      scenarios pass on MSW; a rejection, custom rules included, shows its `x-bga.errors` message on its field (22.5).

Uploads (10.5):

- [x] An upload field in the form kit (drag and drop, progress, image preview, replace and remove) through the
      presigned URL; images show in lists and details through the signed read URL.
- [x] MSW answers presign and the `PUT` and keeps the file as a blob URL.

Payments (10.9):

- [x] A Pay action on the record, success and cancel screens that poll the status; MSW mocks the checkout.

Relations (10.11):

- [x] A multi-select reference picker (`x-bga.source: reference`, `many: true`); lists and details show related
      records as chips; add and remove through the link operations; MSW and fixtures handle link records.

All:

- [x] Agent tests check each plugin's generated frontend files, in both auth modes.
- [x] The workshop-bookings app works in the preview on mocks and live: sign-up, sign-in, a protected page, a booking
      from the workshop's page, an image upload, a fake payment, a status change, and an action hidden without the
      role (checked in the `make up` flow; journeys stay off, decision FE-TESTS).
- [x] Static golden passes.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (agent-ui), `make test`, `BGA_SANDBOX_TESTS=1 make test`; `make up`, generate
workshop-bookings on the fake engine and walk the flow above in both auth modes.

## Status

**Done (2026-11-06), except a full parent's "full" state** (see Deviations). Each plugin's frontend lives in
`templates/plugins/<name>/frontend/files/` and is copied only for apps whose contract has the plugin
(`frontend/app/files.frontend_plugins`); the kit reaches it through the generated `src/components/app/plugins.ts`,
else the kit's `plugin-stubs.tsx`.

- **Auth (auth-jwt):** `/login` and `/register` pages (`AppAuth` on the form kit, demo accounts listed), the top bar's
  `UserMenu` (Sign in / Sign up, or the account with its role and Sign out), `useSession` (`auth.me`). FrontendSpec
  `auth` is written for apps (no `FE_UNSUPPORTED_FEATURE` there). `AUTH_TOKEN_STORAGE` (P8): `local` keeps the token in
  `src/lib/auth/token.ts` (the only `localStorage` use; `src/lib/` is generator-owned, so `conventions` does not scan
  it) and sends a bearer; `cookie` signs in through `/api/auth/login|register|logout` (httpOnly, `SameSite=Lax`
  cookie, plus a readable `bga_signed_in` marker so a signed-out page does not ask the backend), calls go through the
  same-origin `/api/backend/[...path]` proxy (`Origin` checked; `X-Forwarded-Host` = the API's public host), and
  `src/proxy.ts` guards pages on the server. A 401 on a sent session signs out and goes to `/login?next=`. Previews
  take `PREVIEW_AUTH_TOKEN_STORAGE` and get `API_INTERNAL_URL` (the backend's container name) for the server's own
  calls; the README and a new `.env.example` document the flags and recommend `cookie` in production.
- **Roles and ownership:** `app.json` `access` (operationId → secured, roles): navigation, sections and "New" the
  user cannot use are hidden, a page behind sign-in goes to sign-in and back, a page the role cannot use says so;
  record actions follow `allowedActions`.
- **Rules:** transitions are record actions (`Mark as confirmed`, a confirm into a locked state) shown only when
  `transition:<STATE>` is allowed; an edit form's status offers only those states; a locked record shows no Edit or
  Delete; a new record starts in the flow's first state (the field is not on the create form); the payment status
  is the server's (not on any form). A rule's refusal shows its contract message (on its field when it is visible,
  else a toast: an error on a hidden route field is never lost).
- **Uploads (storage):** `UploadField` (drop zone, click or keyboard, size limit, progress over XHR, image preview,
  Replace, Remove → `null`), the key sent; `FileValue` shows images (and file links) through `<field>Url`.
- **Payments:** a `pay` record action (its own kind) starts the checkout and leaves for the provider's page; the
  `/payments/success|cancel` pages (`AppPayment`) follow the payment (`payments.get`, polled) to paid, failed or
  canceled and link back to the record.
- **Relations:** an `AppLinks` tab per many-to-many link: chips linked to the record's page, each removable, a picker
  on the linked entity's list and Add.
- **Mocks:** `src/mocks/plugins.ts` emulates the plugins from the generated `plugins.json` and `defaults.json`:
  sign-up, sign-in and `me` (tokens name their user), secured operations (401), role policies (403), ownership (the
  user's own records; another's is 404), the owner set on create, per-user `allowedActions` (policies, next states,
  locks, unpaid), transitions, locks, capacity, unique-together and unique fields (409s with the contract's
  messages), presign + `PUT` (small files kept as data URLs), the checkout (paid at once) and the links. The mock
  store lasts the tab's session (`sessionStorage`), so a record or a session survives a page load. `scenarios.json`
  now runs signed-in scenarios too (the contract's login, as the smoke check): workshop-bookings 71 of 73 emulated
  (not: `FILE_NOT_FOUND`, the incoming webhook).

Backend fixes found by the live run (Epic 10's plugins together, first generated end to end here): the app's OpenAPI
now documents the 401 of every protected route (`src/libs/security/openapi.py`), `TokenResponseDto` and
`PresignResponseDto` mark their defaulted fields required, the incoming webhook documents its body, the relations
plugin declares its path and page parameters in the contract, public reads of records whose actions depend on the
caller take the signed-in user if any (`OptionalUserDep`, so an organizer sees Edit on a public workshop), and the
checkout builds its provider link from `X-Forwarded-Host` when proxied.

Verified: `tests/test_app_plugins.py` (10, both token modes), the updated app, contract and plugin tests; the
sandbox build of flashcards, project tracker and workshop-bookings (typecheck, lint, build, scenarios: 71 on the
workshop app); full suite; lint. Live (`make up`, fake engine, the new `examples/specs/workshop-bookings.json` +
outline; a requirement mentioning "workshop" drafts it in the app flow): every generation COMPLETED with all checks;
`scripts/plugin-walk.mjs` (sign up, the guard and back, a wrong password, a member's hidden organizer actions, a
booking from a workshop's page with a full workshop refused, a payment through the fake provider's page, a
transition, an organizer's cover upload, a tag linked and unlinked) passed 9/9 and `scripts/app-walk.mjs` (now signed
in as the widest role) 21/21, live in `local` mode, live in `cookie` mode and on mocks. The project tracker and flashcards, regenerated on the 22.7 kit, still pass the app walk (12/12, 21/21).

Deviations:
- **A full parent** is not shown as "full" and its create action is not hidden: the backend does not put
  `create:<child>` in `allowedActions` (10.10 encodes capacity only as the 409 `CAPACITY_REACHED`). The refusal's
  message shows when a booking is tried. Adding `create:<child>` is a backend change for Epic 10.
- The mocks do not emulate `noOverlap` (`OVERLAP`) or `sumEquals` (`TOTAL_MISMATCH`); their scenarios are listed as
  not emulated (none in workshop-bookings).
- The many-to-many picker adds one record at a time (chips show them all, each removable), rather than a multi-select
  list.
- The workshop-bookings walk is a script (`plugin-walk.mjs`), not generated journeys (decision FE-TESTS).
