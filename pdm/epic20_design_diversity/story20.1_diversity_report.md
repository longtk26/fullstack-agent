# Story 20.1 — Diversity report and baseline

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-24 · **Depends on:** 12.6, 17.7

## User story

As the team, we want a repeatable report that says how different our drafted designs are, within a draft, across
drafts of one brief and across similar businesses, so that every later story in this epic can show it made sites
more varied without making them worse.

## Context

- Directions today: `orchestrator/design_direction.py` (`directions()`, `direction()`, `apply_direction()`); the draft
  keeps them in `spec_drafts.design` = `{selected, directions}` (12.6).
- Drafting: `orchestrator/drafting.py` (`DraftRunner._run`, `apply_design`, `draw_images`); the fake engine copies an
  example spec by keyword (`engines/fake_engine.py`, `DRAFT_FIXTURES`; see `docs/development/test-doubles.md`), so with
  the fake engine only the direction differs between drafts. That is what this report measures.
- Building a site from a spec without the engine: `orchestrator/frontend_scaffold.scaffold_frontend` +
  `pnpm build` in `bga-runner-node` (as `tests/sandbox/test_frontend_sandbox.py` does).
- Screenshots and measurements: `scripts/design-check.mjs` (Playwright inside `bga-runner-node`).
- Draft timing: `spec_drafts.started_at` / `finished_at` and `usage` (`engineMs`, `modelCalls`). The UI does not show
  draft time in a generation's total yet (note in `pdm/README.md`); this report computes it.
- Golden requirements: `examples/requirements/` (`corner-shop.md`, `northwind-studio.md`, `project-tracker.md`).

## Steps

1. **Golden set.** Add `examples/requirements/diversity/` with short requirements (5–10 lines each, no brand colours
   or fonts so the direction decides the look): one spa (the "same brief" case) and the pairs clinic / pharmacy,
   spa / gym, bakery / coffee shop, law firm / accountant. List them in a `manifest.json` with the pairs.
2. **Script** `scripts/design-diversity.py` (runs on the host against the local stack or in-process with the fake
   engine; `make design-diversity`):
   - drafts each requirement (static mode) through the same code as `POST /spec-drafts`; the spa is drafted 5 times
     (today's code gives the same result each time; after 20.4 each run uses a new seed);
   - for each draft, reads the three directions and computes the **field measures**: hero layout, heading font, hue
     family (primary hue in 30° buckets, "neutral" below a saturation threshold), key visual kind (from 20.4; today
     `photo` / `illustration` / `none` from the hero's image), home order, and whether the order is the category
     default (`PATTERN_SECTIONS` today);
   - with `--screenshots`: applies each direction to the draft spec, scaffolds and builds it in `bga-runner-node`
     (`--network none`), takes the home page at 1440 px in light mode with reduced motion, converts it to greyscale,
     downsamples to 64 × 40 and reports pairwise similarity (1 − mean absolute difference); only the first draft of
     each requirement, to keep a run under ~30 min;
   - records draft time and engine calls per draft (from `spec_drafts`).
3. **Report** `.data/reports/design-diversity/<date>/report.json` + `report.md` with the measures of the epic's
   "Expected output" table: share of drafts passing the difference test (the rule from the epic, D3, computed here
   before 20.4 enforces it), distinct (hero, heading font, hue family) triples across the 5 spa drafts,
   paired-domain distance (fields that differ between the first directions of a pair, 0–4), trope share, mean and
   max screenshot similarity within a draft, draft time and calls. Screenshots are kept next to it.
4. **Baseline.** Run it on today's code with the fake engine and record the numbers in the epic's Status note. Set
   the screenshot-similarity threshold the epic's target refers to (e.g. halfway between today's mean and 0.5) and
   write it into the epic.
5. Tests: the measure functions (hue family, field overlap, difference test, trope check, image similarity on two
   small fixture PNGs) as unit tests; the script itself is a dev tool (not part of generation), listed in
   `docs/development/` with how to run it.

## Acceptance criteria

- [x] The golden diversity set exists with its pairs.
- [x] `make design-diversity` produces `report.json` and `report.md` with every measure of the epic's table; with
      `--screenshots` it adds the greyscale similarity and keeps the screenshots.
- [x] The measures are unit tested.
- [x] Today's baseline is recorded in the epic's Status note, and the similarity threshold is written into the epic.

## Verify

`make lint`, `make test`, `make design-diversity` and `make design-diversity ARGS=--screenshots` with the fake engine
(`make up` running, runner images built).

## Status

**Done (2026-11-02)**, on `feat/epic20-design-diversity`.

- **Golden set:** `examples/requirements/diversity/` (spa, gym, clinic, pharmacy, bakery, coffee shop, law firm,
  accountant; no brand colours or fonts) with `manifest.json` (`sameBrief: spa`, four pairs) and a README.
- **Measures:** `agent-api/src/orchestrator/design_diversity.py` (pure functions): `visual_fields` (hero layout,
  heading font, hue family in 30° buckets or `neutral`, key visual: photo / illustration / image / type / none),
  `difference_problems` (the epic's D3 rule), `off_default`, `distinct_triples`, `pair_distance`,
  `section_frequency`, `jaccard`, `repeated_copy`, `first_screen` + `image_similarity` (greyscale 64 × 40 of the top
  1440 × 900 px). Unit tests: `tests/test_design_diversity.py` (17).
- **Report:** `agent-api/scripts/design_diversity.py`, `make design-diversity [ARGS=...]`. Drafts run in-process
  through the worker's `DraftRunner` against the dev database (owner: the first user; rows deleted afterwards),
  with AI photos and LangSmith off. `--screenshots` builds each direction of every requirement's first draft with
  the renderer (`scripts/site_check.py`, shared with the fixture check of 20.2) and runs `design-check.mjs` at 1440
  px light; 24 builds in ~4 min. `--engine <name>` uses the worker's engine registry (real engines only with the
  user's yes). `design-check.mjs` gained `DESIGN_CHECK_WIDTHS` / `DESIGN_CHECK_SCHEMES` and loads pages with reduced
  motion. How to run: `docs/development/design-checks.md`.
- **Baseline:** in the epic's Status note.
- **Deviations:**
  - The script lives in `agent-api/scripts/` (run as `python -m scripts.design_diversity`, it imports the agent's
    code), not in the repository's `scripts/`.
  - Threshold: not "halfway between today's mean and 0.5" but mean ≤ 0.90 and max ≤ 0.95. Light pages share a
    large light background, so two very different layouts still score about 0.85–0.9; a 0.73 target would demand
    dark or colour-blocked pages. Revisit at Checkpoint C with real direction cards.
  - The category default order is the best UI UX Pro Max match's landing pattern (`home_order`), and "off default"
    compares the first three sections the page has.
