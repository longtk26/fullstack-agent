# Story 22.4 — App kit: shell, lists, details, dashboard

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-36, FR-25 · **Depends on:** 22.3

## User story

As a user of a generated app, I want it to look and behave like a well-made product: one consistent shell, readable
tables, clear details, loading and empty states, and the same patterns on every screen.

## Steps

1. **Kit components** in `templates/nextjs_overlay/files/dynamic/app/`, built on the shadcn components in the base
   (no new dependencies; tables sort and page on the server, so `@tanstack/react-table` is not needed):

   | Component | What |
   |---|---|
   | `AppShell` | `sidebar` with icons and the outline's nav, collapsible; top bar with breadcrumbs and a slot for the user menu (22.7); a `sheet` on phones |
   | `AppList` | `table` (or cards for `listStyle: cards`) with search, filters, sort and `pagination` bound to the list operation; row actions in a `dropdown-menu`; `empty`, `skeleton` and error states |
   | `AppDetail` | header with the display field and actions; fields in a description grid; `tabs` for children |
   | `AppDashboard` | figure cards and `chart`s from aggregates; recent records |
   | `AppActions` | buttons, confirm `alert-dialog`, `sonner` toasts on success |

2. **One spacing and type scale** for the whole kit (page padding, section gaps, table density from the direction's
   `density`); the direction sets only theme tokens.
3. **Actions from the record:** row and detail actions, and create buttons on a parent, show only what the
   record's `allowedActions` (10.0b) lists; no rule is re-implemented in the frontend. Error messages come from
   `x-bga.errors`, on the field when `fields` is set, else a toast.
4. **Renderer**: app sections render to the kit through the existing contract-bound client and React Query hooks,
   on MSW until the backend is live (as today).
5. **Same behaviour on mocks and live:** the contract's scenarios (10.0b) run against MSW in the Node sandbox
   (`msw/node`, a generated script of seconds, not a test suite; blocking), and after the switch to live through the
   frontend's API path (base URL or proxy), in the background like the other live checks (18.12).
6. **Design checklist**: `DESIGN_CHECKLIST.md` gains an app section (shell, table, detail, states, focus order,
   keyboard use of menus and dialogs); `scripts/design-check.mjs` measures an app fixture at 375 px and 1440 px, light
   and dark.

## Acceptance criteria

- [ ] Flashcards and project-tracker render as apps on the kit with no engine call in the frontend lane, build and
      typecheck, and work on mocks and live.
- [ ] Every screen has loading, empty and error states; tables page and sort on the server.
- [ ] Actions follow `allowedActions` (a record without `delete` shows no delete); errors show their `x-bga.errors`
      message.
- [ ] The scenarios pass on MSW and live; a planted mock mismatch fails the frontend lane.
- [ ] The app fixture passes the design checklist in light and dark at 375 px and 1440 px.
- [ ] Agent tests check the rendered pages for each app section (pytest, no Node).
- [ ] `DYNAMIC_FRONTEND` defaults to `app` once this story is accepted; static golden passes.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (agent-ui), `make test`, `BGA_SANDBOX_TESTS=1 make test` at the checkpoint's
end; `make up`, generate `flashcards-dynamic` and `project-tracker-dynamic` on the fake engine and use them in the
App tab.

## Status

**Planned (2026-11-05).**
