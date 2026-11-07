# Story 26.4 — Guided tour of the workflows (react-joyride)

**Epic:** [26 — Main business workflows](epic26_business_workflows.md) · **Requirements:** FR-40 · **Depends on:** 26.3

## User story

As someone trying the POC, I want the app to show me, on my first sign-in, how my role takes part in the business's
main workflows, step by step on the real screens, and to replay it whenever I want.

## Context

- react-joyride **3.2.0** (2026): React 16.8–19, ships `'use client'`, SSR-safe with Next.js; controlled mode
  (`stepIndex`, `run`, `onEvent(data, controls)`), events incl. `error:target_not_found`; no built-in multi-page tours
  (a `before` hook navigates and waits); v3 replaced v2's `spotlightClicks` / `hideFooter` with `buttons`,
  `overlayClickAction`, `dismissKeyAction`, `blockTargetInteraction`. Open issue #1211: a tour with `run` true from
  mount and steps loaded later never starts (load steps first).
- The kit renders every screen from `app.json`; stable targets are needed (`data-bga-*`, as `data-bga-demo-accounts`).

## Steps

1. **Pin** `react-joyride@3.2.0` in the Next.js base (`make frontend-base`, `make runner-node`: the pnpm store volume is
   keyed on the base lock).
2. **Targets in the kit:** `data-bga-page`, `data-bga-section="<id>"`, `data-bga-action="<action id>"` on actions,
   "New" buttons, form submit buttons and record rows; no visual change.
3. **`AppTour`** (`components/app/tour/`): reads `app.json` `workflows` for the signed-in role; one tour per core
   workflow; steps in order across pages (a `before` hook pushes the route and waits for the target); a step done by
   another role is shown as a short note ("Next, <role> <action>", from the workflow step) without a target; controlled mode;
   a missing target skips the step and records it (`error:target_not_found`).
4. **When it runs:** automatically once per role and tour version on first sign-in (stored per user in
   `localStorage`); "Guide" in the user menu replays it or picks another workflow; never blocks the app (D6).
5. **Text** from the workflow (action, the status it leads to, the rule), in the app's locale (23.8).
6. Tests: `AppTour` with recorded `app.json` workflows (vitest); the app walk (22.4) opens the tour per role and checks
   every step's target exists, on mocks.

## Acceptance criteria

- [ ] On first sign-in, each demo role sees its tour once; "Guide" replays it.
- [ ] Every tour step's target exists on its page for the three lab apps (on mocks), or the step says why it is skipped.
- [ ] Apps without workflows (option off, static sites) have no tour and no new dependency in their bundle.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (kit), `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make up` and a lab app on
mocks and live, `make design-check-app` (no visual change).
