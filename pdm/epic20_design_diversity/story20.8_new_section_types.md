# Story 20.8 — New section types

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-22 · **Depends on:** 17.7

## User story

As a user, I want the site generator to have the kinds of sections real sites of my type use (how it works, the
team, the menu, opening hours and where to find us, a story told over time, a comparison, a statement of what we
stand for), so that my site is built from what my business actually has instead of being squeezed into Features,
Testimonials, FAQ and a call to action.

## Context

- Built-in sections today (`frontend_spec/catalogue.py`, `BUILTIN_SECTIONS`): Hero, Features, CallToAction,
  Testimonials, Faq, Pricing, Stats, Gallery, RichText, ContactInfo, Form, CardGrid, DataTable, DetailView, List,
  ActionBar, plus the layout nodes Columns, Stack, Grid, Tabs. About ten of them are content sections for a
  marketing site, so most static sites are made of the same few.
- Typed props: `section_props.py` (`SECTION_PROPS`, `Surface`); library: `files/renderer/src/components/sections/`;
  per-site selection and props types: `orchestrator/frontend_renderer.py` (`RENDERED` set of catalogue sections);
  drafter's list: `drafting.section_catalogue()`.
- Fixture: `tests/fixtures/frontend-specs/section-library.json`; rules: `DESIGN_CHECKLIST.md`; forms and rhythm
  from 20.2, icons from 20.5 (the new sections take `icon` where it fits once 20.5 lands).
- Story 20.9 makes the drafter choose sections by content; it needs these types to exist first.

## Steps

1. **New sections** (typed content, theme tokens only, `Surface` backgrounds, each with 2–3 forms in the 20.2
   style):

   | Section | Content | Forms | Typical use |
   |---|---|---|---|
   | `Steps` | `title?`, `items: [{title, body?}]` (2–8) | `numbered` / `horizontal` / `connected` (a line joins the steps) | how booking, ordering or a service works |
   | `Timeline` | `title?`, `items: [{date, title, body?, image?}]` | `vertical` / `alternating` | history, a story over time, an event programme |
   | `Team` | `title?`, `members: [{name, role?, bio?, image?}]` | `grid` / `list` / `portraits` (large images) | people of a studio, clinic, firm, school |
   | `PriceList` | `title?`, `groups: [{title?, items: [{name, price?, description?, tags?}]}]` | `menu` (dotted leaders) / `columns` / `cards` | a restaurant menu, salon or repair price list |
   | `Location` | `title?`, `address`, `hours?: [{days, opens, closes}]`, `phone?`, `email?`, `mapLink?` (https), `image?` | `split` / `card` / `band` | opening hours and how to get there (no embedded map: a link and an optional image) |
   | `Comparison` | `title?`, `columns: [string]` (2–4), `rows: [{label, values: [string \| bool]}]` | `table` / `cards` (stacked on small screens) | plans, options, before / after |
   | `Statement` | `text` (≤ 280 chars), `attribution?`, `image?` | `large` (oversized type) / `quote` / `band` | what the business stands for, a manifesto, one real quote |

   Rules: no invented data in the components (prices, hours and names come from content); `Location` shows the
   hours as a table with today highlighted (client-side, no network); `Comparison` uses a real `<table>` with
   headers; every section keeps the checklist (type sizes, line length, one accent).
2. **Plumbing.** Props models, catalogue descriptions (when to use each, written for the drafter), the renderer's
   `RENDERED` set and per-site copying, generated props types, the editor schema, JSON Schema snapshots, schema
   digests (18.9), validator rules (e.g. `PriceList` items without prices → fine; `Location.mapLink` must be
   `https://`).
3. **Fixture and checklist.** One fixture page per new section with every form; `DESIGN_CHECKLIST.md` lists them;
   the coverage test includes them.
4. Tests: props validation; renderer selection (a site that uses none of them copies none); snapshots; sandbox build
   of the fixture offline; `design-check.mjs` on the fixture in all presets.

## Acceptance criteria

- [ ] `Steps`, `Timeline`, `Team`, `PriceList`, `Location`, `Comparison` and `Statement` exist with their forms,
      typed, in the catalogue, the editor schema and the drafter's section list.
- [ ] Existing specs render unchanged; a site copies only the sections it uses.
- [ ] The fixture covers every new section and form; the sandbox build passes.
- [ ] `design-check.mjs` on the fixture (5 presets × 390 / 768 / 1440 × light / dark): no rule fails; screenshots in
      the Status note.

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `BGA_SANDBOX_TESTS=1 make test`,
`node scripts/design-check.mjs` on the fixture, `cd agent-ui && pnpm exec tsc --noEmit`.

## Status
