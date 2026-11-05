# Design checks (Stories 17.7, 20.1–20.3)

Two dev tools measure how generated sites look. Neither is part of the generation pipeline. Both build sites with
the section renderer in the Node sandbox, so they need Docker and the `bga-runner-node` image (`make runner-node`),
plus the dev database (`make dev`). Generated drawings and photos are shown as placeholders; nothing calls an engine
or the image API unless you pass a real engine to the report.

## Section library: `make design-check-fixture`

Builds `agent-api/tests/fixtures/frontend-specs/section-library.json` (every section, layout, form and rhythm) and
runs `scripts/design-check.mjs` on every page at 390 / 768 / 1440 px, light and dark, then checks the measured rules
of `agent-api/templates/nextjs_overlay/DESIGN_CHECKLIST.md`: headline lines, nav height, CTA above the fold, type
sizes, font families and loading, line length.

```bash
make design-check-fixture                                   # every theme preset → .data/shots/design-check/<preset>/
make design-check-fixture ARGS="--combos"                   # six tone, font and preset combinations (Story 20.3)
make design-check-fixture ARGS="--presets minimal --out $PWD/.data/shots/try"
make design-check-fixture ARGS="--recheck --out $PWD/.data/shots/try"   # re-read saved reports, build nothing
make design-check-fixture ARGS="--combos --motion"          # + motion on and JavaScript off (Story 20.6)
make design-check-fixture ARGS="--combos --spec ../examples/frontend-specs/shop-dynamic.json \
    --backend ../examples/specs/shop.json"                   # a dynamic app on its mock API (Story 20.4)
```

`--combos` gives each combination the icons and motion its tone maps to (Stories 20.5, 20.6) and another signature
moment. `--motion` adds two passes per page at 1440 px: motion on (time until the hero's call to action is fully
visible, at most 1 s; after scrolling to the end nothing may stay transparent or displaced) and JavaScript off
(nothing hidden).

A dynamic spec needs its BackendSpec (`--backend`): it is planned against the API contract, built with
`next build` and started with `next start` on the mock API (`MOCK_TEST_API=true`); every page without route
parameters and one record page per resource (the route tests' example paths) are checked. Rules that need a hero
(CTA above the fold) only apply where a page has one, so data pages are measured on the rest.

The checks' sandboxes carry their own instance label (`DEV_INSTANCE` in `agent-api/scripts/site_check.py`), so a
running stack's worker does not remove them as orphans mid-build.

Each output folder holds the screenshots and `report.json`; `summary.json` lists the failures per preset. Run it
after changing a section, a variant or the theme CSS.

## Diversity report: `make design-diversity`

Drafts the golden requirements in `examples/requirements/diversity/` (static mode, and the manifest's `dynamic` ones
in dynamic mode; through the worker's `DraftRunner`, rows deleted afterwards; AI photos off, LangSmith off) and
measures how different the designs are
(`agent-api/src/orchestrator/drafting/design_diversity.py`): the four visual fields of each direction (hero layout, heading
font, hue family, key visual), the difference test, distinct combinations across five drafts of one brief, the
distance between similar businesses, the category's default home order, section frequency, home-composition
similarity, repeated headings and CTA labels, stock phrases left (Story 20.9), and draft time. Since Story 20.4 the
directions are the engine's direction cards; the fake engine draws them from `agent-api/design_data/concepts.json`
with the draft's seed.

```bash
make design-diversity                                      # fake engine, field measures (~10 s)
make design-diversity ARGS="--screenshots"                 # + build each direction, compare first screens (~5 min)
make design-diversity ARGS="--seed 100"                    # repeatable: seeds 100, 101, … per draft
make design-diversity ARGS="--engine claude-code"          # a real engine: costs money, only with the user's yes
```

With `--screenshots`, a dynamic requirement's three directions are built on the mock API and checked on every page
at every width and scheme; the checklist failures are in the report and the screenshots stay in
`shots/<name>-<n>-shots/`.

Output: `.data/reports/design-diversity/<timestamp>/report.md` and `report.json` (+ `shots/`). The epic's targets
(`pdm/epic20_design_diversity/epic20_design_diversity.md`) are written against these measures. With the fake engine
the drafted content is the same example spec for every requirement, so section and copy measures only mean
something with a real engine.

## App kit (Story 22.4)

`make design-check-app` plans an app of the dynamic app flow from an example BackendSpec and outline (no engine),
builds it in the Node runner and screenshots every screen at 375 and 1440 px, light and dark, on the mock API;
parameterised routes take the first fixture record. `ARGS="--app two-entity:project-tracker"` picks another app;
screenshots and `report.json` land in `.data/shots/design-check-app/<app>/`. The rules it measures are in
`templates/nextjs_overlay/DESIGN_CHECKLIST.md` ("App kit").

`agent-api/scripts/app-walk.mjs` walks a running app through every screen and action in a browser (open every page,
open a record from each list, edit and save, add a child from its parent, create, delete from the row menu, record
actions), driven by the app's own `src/content/app.json`, and fails on any failed API call, error state or page error.
Run it in `bga-runner-node` with a project's `node_modules` (the shared `bga-fe-modules-*` volume) mounted next to it:
`node app-walk.mjs <url> <app.json> [shots dir]`; `WALK_HOST=host.docker.internal` when the app runs on the host.
