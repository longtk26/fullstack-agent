# Story 20.2 — Hero layouts and section forms

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-22 · **Depends on:** 17.7

## User story

As a user, I want the first screen and the sections of my site to have a structure that suits its direction, not the
same "text beside a picture, then a row of cards" on every site, so that different directions really look
different.

## Context

- Typed props: `modules/shared/domain/frontend_spec/section_props.py` (`HeroVariant` = `split` / `centered` /
  `banner`, `CardStyle`, `Background`, `Surface`, `HeroProps`, `FeaturesProps`, `TestimonialsProps`, `StatsProps`,
  `CardGridProps`); catalogue descriptions in `frontend_spec/catalogue.py` (`BUILTIN_SECTIONS`); the drafter's list
  `drafting.section_catalogue()`.
- Library: `templates/nextjs_overlay/files/renderer/src/components/sections/*.tsx` (`Hero.tsx`, `Features.tsx`,
  `Testimonials.tsx`, `Stats.tsx`, `CardGrid.tsx`, `styles.ts`); `PageRenderer.tsx` lays out a page's sections.
- Rules: `templates/nextjs_overlay/DESIGN_CHECKLIST.md` (17.7): headline ≤ 2 lines at 390 / 768 / 1440 px, primary
  CTA above the fold, nav ≤ 80 px, ≤ 5 type sizes, one accent, one radius system, theme tokens only.
- Fixture: `agent-api/tests/fixtures/frontend-specs/section-library.json`, checked by `tests/test_fonts_and_variants.py`
  (`test_the_section_library_fixture_covers_every_variant`) and built by
  `tests/sandbox/test_frontend_sandbox.py`.
- Hero layouts come from oil-ui's eight first-screen skeletons (`docs/research/design-diversity.md`).

## Steps

1. **Hero layouts.** `HeroVariant` grows to 8 values (additive; the default stays `split`):

   | Value | First screen |
   |---|---|
   | `split` | text on one side, image on the other (from 1024 px) |
   | `centered` | one sentence or object centred in wide space |
   | `banner` | a full-bleed image (or the primary colour) with the text over it |
   | `stage` | the image is the screen: large image first, headline and CTA set on its lower edge |
   | `type` | type is the image: an oversized headline across the full width (may be cropped at the edge on wide screens), no image |
   | `stacked` | a full-width headline, then a wide image or content row below it |
   | `collage` | headline plus 3–4 images in an asymmetric grid (uses `images: [asset]`, new optional field; falls back to `split` with one image) |
   | `vertical` | a vertical or rotated display label beside the headline (the eyebrow or a short word); body text never rotated |

   Every layout keeps the checklist: headline ≤ 2 lines (for `type`, the size scales with length and width), CTA
   above the fold at every width, accessible names and order in the DOM unchanged by the visual layout.
2. **Section forms** (new optional `form` on these sections; the default is today's look):
   - Features: `cards` | `list` (numbered rows, large numerals) | `ledger` (hairline-separated rows, title left, text
     right) | `alternating` (image / text rows, alternating sides; needs item images, falls back to `list`).
   - Testimonials: `cards` | `quote` (one large quote, others below as a short list) | `strip` (one row, horizontal
     scroll on small screens).
   - Stats: `cards` | `figures` (large numbers, no boxes) | `inline` (one line with dividers).
   - CardGrid: optional `featured: true` (the first item spans two columns).
3. **Page rhythm.** New optional page field `rhythm`: `uniform` (today) | `alternate` (content sections alternate
   `default` and `muted` backgrounds unless a section sets its own) | `dividers` (hairline rules between sections,
   no background changes). Applied by `PageRenderer`.
4. **Plumbing.** Props models, catalogue descriptions, `section_catalogue()`, the generated props types, the UI's
   spec editor schema (enums appear as choices), the validator (`collage` without `images` → warning
   `FE_DESIGN_RULE` with the fallback named), JSON Schema snapshots, schema digests (18.9).
5. **Fixture and checklist.** The section-library fixture gets a page per hero layout and every form and rhythm;
   the coverage test lists the new enums. `DESIGN_CHECKLIST.md` documents each layout and form (how it keeps the
   rules) and any deviation.
6. Tests: props validation and defaults; existing examples render unchanged (snapshots); fixture coverage; sandbox
   build of the fixture; `design-check.mjs` on the fixture in all presets.

## Acceptance criteria

- [x] 8 hero layouts and the section forms and rhythms above, typed, in the catalogue and the editor schema.
- [x] Existing specs and examples validate and render exactly as before (defaults unchanged).
- [x] The fixture covers every value; the sandbox build passes (install, typecheck, build, routes; see Status).
- [x] `design-check.mjs` on the fixture (5 presets × 390 / 768 / 1440 × light / dark): no rule fails; screenshots of
      every hero layout and form in the Status note.

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review the diff), `BGA_SANDBOX_TESTS=1 make test`,
`node scripts/design-check.mjs` on the fixture (as the checklist describes), `cd agent-ui && pnpm exec tsc --noEmit`.

## Status

**Done (2026-11-02)**, on `feat/epic20-design-diversity`.

- **Hero** (`section_props.py`, `Hero.tsx`): `variant` adds `stage`, `type`, `stacked`, `collage` (`images`, up to 4;
  fewer than two → `split` + `FE_DESIGN_RULE` warning naming the fallback), `vertical`. The text block is shared;
  the headline stays the first heading and the CTA comes before images in the DOM. `type` uses `displayClass`
  (larger steps, still two lines); the vertical label takes the headline's size class. `collage` splits half and
  half like `split` (a 5/12 text column wrapped a wide face to three lines).
- **Forms:** Features `cards` / `list` / `ledger` / `alternating` (`FeatureItem.image`; none → `list` + warning);
  Testimonials `cards` / `quote` / `strip` (a focusable, keyboard-scrollable region); Stats `cards` / `figures` /
  `inline` (one `useStatValue` hook for content and API values); CardGrid `featured`.
- **Rhythm:** `Page.rhythm` (`uniform` / `alternate` / `dividers`). `alternate` is resolved by the generator
  (`alternate_backgrounds` in `frontend_renderer.py`: sections without a background take the page colour or muted,
  opposite to the section before; CallToAction keeps its panel); `dividers` is a hairline drawn by `PageRenderer`.
  The plan carries `rhythm` only when it is not `uniform`.
- **Drafter:** `section_catalogue()` lists each content field's choices from the props models (e.g. `variant (split
  | centered | … )`), so new layouts and forms reach the drafter without editing descriptions. The catalogue
  descriptions are unchanged, so plans and context packs of existing specs stay equal.
- **Fixture:** five pages (`/layouts-*`) cover every layout, form, `featured` and rhythm;
  `test_the_section_library_fixture_covers_every_layout_form_and_rhythm` checks every `form` field of every section.
- **Verification:** `make test` 714 passed; `make lint` clean; snapshots updated (`section-props.ts`, schema digest,
  ProductGrid context pack for the CardGrid source); plans of the three golden specs unchanged.
  `make design-check-fixture` (new, `scripts/design_check_fixture.py`): 5 presets × 18 pages × 390 / 768 / 1440 ×
  light / dark = 540 views, 0 failures (`.data/shots/phaseB-presets/`). `BGA_SANDBOX_TESTS=1`: the section library
  (with every layout, form and the 20.8 sections) installs, type-checks, builds and passes the route check; the six
  sandbox tests still fail on `main`'s state, not on this story: they expect `lint` and `tests` to pass, which
  `frontend_validation.py` now always skips (`95b547b`), and the live smoke finds no tests. Fixing those
  assertions is left for a separate change.
- **Deviations:**
  - Figures stay at `text-2xl` (a first version at `text-5xl` made six sizes on a page with a hero; see the
    checklist's deviations).
  - The `type` hero is not cropped at the screen edge.
