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

- [ ] The tokens exist, are optional, are drawn by CSS variables, and existing specs render unchanged.
- [ ] `tone_tokens` maps the five scales to tokens, identically in Python and the UI.
- [ ] One anchor section per page with `colorArea` `block` / `bold`, keeping contrast and one accent.
- [ ] 6–8 new faces are bundled and load offline; the editor lists them.
- [ ] `design-check.mjs`: no rule fails for the fixture in at least 6 token combinations (raw-loud, refined-quiet,
      dense-serious, …); screenshots in the Status note.

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `make frontend-base` + `make runner-node`,
`BGA_SANDBOX_TESTS=1 make test`, `node scripts/design-check.mjs`, `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint`.

## Status
