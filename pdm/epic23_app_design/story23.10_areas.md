# Story 23.10 — Areas: a different app per role group

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-06, FR-36 · **Depends on:** 23.6, 23.9

## User story

As a user drafting an app whose roles use it in different ways, I want each group of roles to get screens made
for how they use it (for example a catalogue for the people who browse and a back office for the people who
manage), from the same requirement, the same contract and the same API.

## Context

- Today (22.7) every role gets the same shell; `app.json` `access` (operationId → secured, roles) hides nav, "New"
  and pages a role can't use. The backend enforces roles, ownership (10.3) and visibility (23.9).

## Steps

1. **Outline `areas`** (optional; none means one area, as today): `[{id, label, roles, prefix, design}]`, where
   `design` is the brief of 23.6 for that area (archetype, shell, home, views per entity). Each role has one home area
   (`roles`); a role may open another area whose operations it can call (a manager can "view as learner"). Code
   checks: roles exist in `auth.roles`, every role has exactly one home area, prefixes are unique (`/` for the first,
   then `/<id>`), and an app with a public part has a `public` area for guests.
2. **Screens per area.** `app_frontend_spec` runs once per area on the operations its roles may call (from the access
   map): the manage area gets lists, create, edit, delete and transitions; the learner area gets list, get and the
   custom operations learners may call (`enroll`, "my enrolments"). Coverage: every operation is reachable in at
   least one area whose roles may call it; an operation no area reaches is unplaced (an error, as in 22.3). Bindings
   are written as today, one per section.
3. **Kit.** One Next route group per area (`(learn)/`, `(manage)/`) with its own `layout.tsx` and `AppShell` variant;
   the theme (colours, fonts, recipe) is shared, density and shell come from the area's design. After sign-in,
   `AppAuth` goes to the role's home area (or `next`). A link into an area the role can't use shows "Not for your
   role" with a link home. An area switcher in the user menu lists the areas the role can open.
4. **Explaining, not filtering.** When `x-bga.visibility` (23.9) applies, the empty state says what the role can see
   ("Only published courses are shown"). The frontend never adds a filter the backend didn't apply.
5. **Scenarios and walks.** Scenarios run per demo user (one per role, 22.7's `demoUsers`); the app walk runs once per
   area as that area's role.
6. **Review.** The draft review lists the areas with their roles and brief; the user can merge two areas into one
   (a spec edit, no model call).
7. Tests: area checks, screens per area from the access map, coverage across areas, route groups and redirects, the
   switcher, per-role scenarios, snapshots of the LMS app.

## Acceptance criteria

- [ ] The LMS golden app has a learner area (catalogue, top bar, media grid, Enroll) at `/` and a manager area (back
      office, sidebar, table, publish) at `/manage`, from one contract.
- [x] Every operation is reachable in an area whose roles may call it; no area shows an operation its roles can't
      call.
- [ ] Sign-in goes to the role's area; a manager can open the learner area; a learner opening `/manage` is told it's
      not for their role.
- [ ] Learners never see draft courses, on mocks and live, and no frontend filter does that work (checked by a test
      that the learner area's list bindings equal the manager's apart from the operation set).
- [ ] Apps without roles are unchanged (one area); pair check 0 issues; the app walk passes per area.
- [x] Static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make up` with the LMS and workshop apps, the app walk per
area on mocks and live, `make design-check-app` per area.

## Status

**Implemented (2026-11-06), on the fake engine and mocks.**
- **Outline areas** (`AppArea`), checked by `complete_design`: roles of the app, each in one area, the one sign-up
  leads to first (at `/`), the others at `/<id>`; one area is the app itself.
- **Screens per area** (`screens._area_screens`): each area planned from the operations its roles may call, the first
  at `/`, the others under their prefix with pages and forms renamed; sign-in and payment pages once; coverage on the
  union. The three golden apps with areas (clinic, plant shop, event tickets) plan with 0 pair issues.
- **Kit:** `useLayout` resolves the area by the path; `AppShell` shows the area's shell and only its navigation;
  `AreaSwitch` lets a role open the other areas it belongs to; after sign-in `AppAuth` goes to the role's area
  (`homePath`); a page the role cannot use says so (22.7).
- Verified: `tests/test_app_areas.py`; the three area apps build on mocks with 0 failures.

Deviations: areas are plain route prefixes, not Next route groups (the shell switches by path); verified on the clinic,
plant shop and event tickets drafts (Learnly's real draft has no areas); the per-area app walks and the sign-in
redirect run with the user's real test.
