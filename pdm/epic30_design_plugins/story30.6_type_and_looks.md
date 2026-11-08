# Story 30.6 — Font pairings and more looks

**Epic:** [30 — Design plugins](epic30_design_plugins.md) · **Requirements:** FR-44, FR-33 · **Depends on:** 30.3

## User story

As a user drafting an app, I want type and surfaces that give my product its own voice (a reading app set like a
book, a dense tool set like a terminal, a media app dark and quiet), so that the look fits the product and not only
its colours.

## Context

- Fonts: `@fontsource` packages pinned in the base (`frontend_spec/fonts.py`, `make frontend-base`, `make runner-node`);
  app typesetting per script (23.8). Recipes: 12, with families and guards (`recipes.py`).

## Steps

1. **`font-pairing` kind:** a descriptor names a heading and a body font (bundled), an optional mono font, the heading
   weight, case and tracking, the type scale ratio, the scripts it supports (Latin, Japanese, …) and its `choose` text;
   no kit file (the theme writes it). Start with eight pairings drawn from today's bundled fonts, each tagged with the
   archetypes and recipes it suits.
2. **Pairing rules (code):** a pairing that does not cover the app's script is never offered; the requested look's
   heading kind (23.13) filters pairings; the three looks of a draft use at least two pairings.
3. **New recipes** (each a `recipe` plugin with its guards and gates):
   - `cinema` (dark first, quiet surfaces, media-first; not for products that need print-like reading),
   - `paper` (warm off-white, ruled lines, reading-first),
   - `terminal` (mono headings, hairline borders, dense; for developer and data tools only),
   - `luxe` (high contrast type, generous space, thin rules; not for dense back offices).
4. **Density personalities:** recipes may set the default density and the card plugin they look best with
   (`prefers` in the descriptor), used by 30.7 as a tie-breaker, never as a rule.
5. Tests: pairing filters by script and requested heading kind; recipe guards; plugin checks clean.

## Acceptance criteria

- [ ] Eight font pairings and four new recipes are `ready` and pass their gates in every kind's fixture.
- [ ] A Japanese app is never offered a pairing without Japanese coverage.

## Verify

`make design-plugin-check` for each plugin, `make test`, `make app-design-report`.

## Status

Proposed 2026-11-08.
