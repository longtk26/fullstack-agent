# Story 20.3 — Tone tokens, colour roles and display fonts

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-22 · **Depends on:** 17.7

## User story

As a user, I want the feel of my site (quiet or loud, raw or refined, airy or dense, light or heavy, playful or
serious) to show in its type, surfaces and use of colour, not only in its palette, so that two directions with
similar colours still feel different.

## Context

- Theme model: `frontend_spec/schema_v1.py` (`Theme`: `style`, `colorScheme`, `colors`, `typography` {`headingFont`,
  `bodyFont`, `scale`}, `radius`, `density`, `direction`); presets in `frontend_spec/catalogue.py` (`THEME_PRESETS`:
  minimal, editorial, playful, corporate, dashboard).
- CSS: `orchestrator/frontend_theme.py` (`build_theme`, `globals_css`, `fonts_ts`, `inverse_palette`, contrast
  helpers `contrast`, `on`, `mix`); the library reads tokens only (`files/renderer/.../styles.ts`).
- Fonts: `frontend_spec/fonts.py` (`FONTS`, 22 bundled `@fontsource` packages, `closest_font`, `font_category`);
  installed in the pinned base by `scripts/frontend-base.sh` (`make frontend-base`).
- The tone scales and their visible effects are from oil-ui (`docs/research/design-diversity.md`).
- Checklist rule "one accent per page" (17.7) stays: the anchor role below uses the primary or a deep neutral, not a
  second accent.

## Steps

1. **Tokens** (new optional `theme` fields; absent = today's look; final names fixed in this story):

   | Token | Values | Drawn as |
   |---|---|---|
   | `surface` | `flat` / `outline` / `raised` | cards and panels: no border and no shadow / hairline border / soft shadow |
   | `typography.headingWeight` | 400–800 (steps of 100) | heading font weight (only weights the font has; nearest otherwise) |
   | `typography.headingCase` | `normal` / `upper` | uppercase headings with wider tracking |
   | `typography.tracking` | `tight` / `normal` / `wide` | display tracking (−0.03 / 0 / +0.04 em) |
   | `typography.ratio` | `tight` / `default` / `dramatic` | type-scale ratio (~1.2 / 1.25 / 1.414): how much bigger headings are than text |
   | `colorArea` | `minimal` / `block` / `bold` | how much of the page carries colour: buttons and eyebrows only / plus one anchor section / plus coloured hero and CTA |

   Plus the existing `radius` and `density`. All drawn with CSS variables in `globals.css` and classes in
   `styles.ts`; the library reads no new props.
2. **Colour roles.** `colorArea: block` and `bold` mark one **anchor** section per page (the first CallToAction, else
   the section before the footer) with the `surface-inverse` scope, which already keeps contrast. The highlight stays
   the primary colour. No second accent.
3. **Tone → tokens.** A pure function `tone_tokens(tone)` in a new module `orchestrator/design_tone.py`: tone =
   five integers 1–5 (`energy`, `finish`, `density`, `weight`, `seriousness`). The mapping, for example: energy →
   `colorArea` and `typography.ratio`; finish → `radius` and `surface` (raw: `none` radius, `outline`; refined:
   `sm`–`md`, `flat` or `raised`); density → `density` and section spacing; weight → `headingWeight`, `surface`;
   seriousness → `radius`, `headingCase`. The table lives in the module docstring and in
   `DESIGN_CHECKLIST.md`. Mirrored in the UI (`agent-ui/src/features/specs/lib/design-direction.ts` or a sibling
   `design-tone.ts`) with the same table; a shared JSON fixture of tone → tokens cases is tested on both sides.
4. **Display fonts.** Add 6–8 display or characterful text faces to `FONTS` (e.g. Fraunces, Instrument Serif,
   Bricolage Grotesque, Syne, Archivo, Newsreader, Unbounded, Familjen Grotesk; final list by licence (OFL) and
   `@fontsource` availability), exact pins, through `make frontend-base`. Each gets its category and weights;
   `closest_font` covers them. Rebuild `make runner-node`.
5. **Checks.** Every token combination keeps the contrast pairs (`contrast_failures`) and the checklist; a heading
   weight that the font lacks falls back to the nearest; `upper` headings are limited to display sizes (not body).
6. Tests: tokens typing and defaults; `globals.css` snapshots per token; `tone_tokens` table cases (Python and UI on
   the shared fixture); fonts install offline (sandbox); fixture pages in a few token combinations through
   `design-check.mjs`.

## Acceptance criteria

- [x] The tokens exist, are optional, are drawn by CSS variables, and existing specs render unchanged.
- [x] `tone_tokens` maps the five scales to tokens (Python only; the UI needs no mirror, see deviations).
- [x] One anchor section per page with `colorArea` `block` / `bold`, keeping contrast and one accent.
- [x] 6–8 new faces are bundled and load offline; the editor lists them.
- [x] `design-check.mjs`: no rule fails for the fixture in at least 6 token combinations (raw-loud, refined-quiet,
      dense-serious, …); screenshots in the Status note.

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `make frontend-base` + `make runner-node`,
`BGA_SANDBOX_TESTS=1 make test`, `node scripts/design-check.mjs`, `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint`.

## Status

**Done (2026-11-02)**, on `feat/epic20-design-diversity`.

- **Tokens** (`schema_v1.py`, optional): `surface` (`flat` / `outline` / `raised`), `colorArea` (`minimal` / `block`
  / `bold`), `typography.headingWeight` (400–700, the loaded weights), `headingCase` (`normal` / `upper`),
  `tracking` (`tight` / `normal` / `wide`), `ratio` (`tight` / `default` / `dramatic`).
- **Drawn by** `frontend_theme.py`: a `heading` utility (`--heading-weight` 600, `--heading-tracking` −0.025em,
  `--heading-case`) on hero and section headings (h1, h2 only); `ratio` overrides the display steps (`--text-2xl` …
  `--text-9xl`); `surface` adds unlayered card rules (`flat`: no ring; `raised`: soft shadow; `filled` / `plain`
  cards keep their look); `colorArea` is applied per page in `site.json` (`color_roles`: `minimal` mutes CTA
  panels, `block` makes one anchor section primary, `bold` also the hero; named backgrounds are kept). The built
  theme carries `tokens` only when set, so plans of existing specs are unchanged.
- **Tone → tokens:** `orchestrator/design_tone.py` (`tone_tokens`, `apply_tone`; the table in its docstring),
  `tests/test_design_tone.py`.
- **Fonts:** Fraunces, Instrument Serif (400 only), Newsreader, Bricolage Grotesque, Syne, Archivo, Unbounded,
  Familjen Grotesk (OFL, `@fontsource` 5.3.0, exact pins), added with `pnpm add -E --lockfile-only` in node:22 (only
  the eight font entries changed in the lock), `overlay.json` regenerated, `make runner-node` rebuilt. 30 fonts.
- **Wide faces:** found by the combinations: Unbounded in capitals and Syne wrapped hero headlines to 3–4 lines.
  Each font now has a rough `width` against Inter; `display_scale` (width × capitals × tracking, floor 0.6, never
  above 1) shrinks the hero sizes, written as `--hero-<step>` and used by `headlineClass` / `displayClass` with
  Tailwind's line heights, so faces of normal width keep today's exact sizes.
- **Verification:** `make test` and `make lint` as in 20.2; `make design-check-fixture ARGS="--combos"`: six
  combinations (raw-loud: Unbounded / Archivo, refined-quiet: Fraunces / Newsreader, dense-serious: Familjen
  Grotesk / Source Sans 3, playful-bold: Bricolage Grotesque / DM Sans, light-airy: Instrument Serif / Inter,
  heavy-refined: Syne / Inter) × 18 pages × 3 widths × 2 schemes = 648 views, 0 failures, every font `loaded`
  (`.data/shots/phaseB-combos/`).
- **Deviations:**
  - No UI mirror of `tone_tokens`: the UI applies direction cards whose theme the server already filled (20.4), so
    it never maps a tone itself; the mapping lives in one place.
  - `headingWeight` stops at 700 (the weights the library loads), not 800.
  - The token names are final as listed; "section spacing" from density stays the existing `density` token.
