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
```

Each output folder holds the screenshots and `report.json`; `summary.json` lists the failures per preset. Run it
after changing a section, a variant or the theme CSS.

## Diversity report: `make design-diversity`

Drafts the golden requirements in `examples/requirements/diversity/` (static mode, through the worker's
`DraftRunner`, rows deleted afterwards; AI photos off, LangSmith off) and measures how different the designs are
(`agent-api/src/orchestrator/design_diversity.py`): the four visual fields of each direction (hero layout, heading
font, hue family, key visual), the difference test, distinct combinations across five drafts of one brief, the
distance between similar businesses, the category's default home order, section frequency, home-composition
similarity, repeated headings and CTA labels, and draft time.

```bash
make design-diversity                                      # fake engine, field measures (~10 s)
make design-diversity ARGS="--screenshots"                 # + build each direction, compare first screens (~5 min)
make design-diversity ARGS="--engine claude-code"          # a real engine: costs money, only with the user's yes
```

Output: `.data/reports/design-diversity/<timestamp>/report.md` and `report.json` (+ `shots/`). The epic's targets
(`pdm/epic20_design_diversity/epic20_design_diversity.md`) are written against these measures. With the fake engine
the drafted content is the same example spec for every requirement, so section and copy measures only mean
something with a real engine.
