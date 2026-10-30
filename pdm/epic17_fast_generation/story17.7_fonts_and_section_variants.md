# Story 17.7 — Fonts that load and section variants

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-22 · **Depends on:** 17.1, 17.2
**Planned:** after the main Epic 17 stories (agreed 2026-10-29); re-planned 2026-10-30 to come after 12.4 and
before 12.6, which picks fonts and variants from this story. Research:
[docs/research/design-skills.md](../../docs/research/design-skills.md).

## User story

As a user, I want the fonts I pick to really show on my site, and a few looks per section (not one fixed design),
so that a generated site feels designed while still being built without the engine.

## Acceptance criteria

- [x] A curated set of about 20 Google fonts (sans, serif, display, mono) is part of the pinned base as
      `@fontsource` packages, so they install offline from the pre-warmed store and work in the static export.
      The theme's `headingFont` / `bodyFont` load the matching files; today only the CSS names them, and visitors
      without the font installed see a fallback (e.g. Northwind's Playfair Display shows as a generic serif).
      The set is chosen from the pairings in UI UX Pro Max's `typography.csv` (12.6), e.g. Inter, Space Grotesk,
      Plus Jakarta Sans, DM Sans, Outfit, IBM Plex Sans, Poppins, Rubik, Nunito, Source Sans 3, Playfair Display,
      Cormorant Garamond, EB Garamond, Crimson Pro, JetBrains Mono, so most of its pairings load.
- [x] The validator warns when a font is outside the set and suggests the closest one; the editor schema lists
      the set.
- [x] Section variants, typed in the props models (17.1): e.g. Hero `variant: "split" | "centered" | "banner"`,
      `background: "default" | "muted" | "primary" | "image"` on content sections, card style for list sections.
      Variants use the theme tokens only, so they follow every preset and light/dark.
- [x] The section library and its variants pass a design checklist (from Taste Skill's page rules, see the
      research note): one accent per page, one radius system, two font families and five type sizes at most, body
      line length 45–75 characters, hero headline two lines at most at 390 / 768 / 1440 px, primary CTA above the
      fold, nav ≤ 80 px, off-black / off-white in dark mode, motion on transform and opacity only with a
      `prefers-reduced-motion` fallback. The checklist lives next to the library; deviations are noted there.
- [x] The section-library fixture covers every variant; screenshots of each preset in the Status note.
- [x] Still no engine call for a catalogue-only static site.

**Status:** done (2026-10-30), on `feat/story17.7-fonts-variants`.

- **Fonts:** 22 `@fontsource` packages (5.3.x, exact pins) added to the pinned base with `pnpm add -E` in node:22
  (only font entries plus one recharts peer re-resolution changed in the lock); `scripts/frontend-base.sh` installs
  them on a full regeneration (`make frontend-base` passes the list from `frontend_spec/fonts.py`). The set: Inter,
  Space Grotesk, Plus Jakarta Sans, DM Sans, Outfit, IBM Plex Sans, Poppins, Rubik, Nunito, Source Sans 3, Roboto,
  Montserrat, Atkinson Hyperlegible (sans); Playfair Display, Cormorant Garamond (display); EB Garamond, Crimson
  Pro, Source Serif 4, Lora, Merriweather (serif); JetBrains Mono, Space Mono (mono). Every preset font is in it.
  The theme's fonts are imported by a generated `src/app/fonts.ts` (weights 400–700 the family has), which the root
  layout imports; the export ships the `.woff2` files (24–40 per preset). Font stacks fall back by kind (serif,
  display, mono, sans).
- **Validator / editor:** `FE_FONT_NOT_BUNDLED` warning with `Closest bundled font: …` (`closest_font`: spelling,
  then the default of the guessed kind); the editor schema lists the set as `examples` for `headingFont` /
  `bodyFont`. `FE_DESIGN_RULE` warns when a hero headline is over 50 characters.
- **Variants** (`section_props.py`, theme tokens only): `background` (`default` / `muted` / `primary` / `image` +
  `backgroundImage`) on every content section, Hero `variant` (`split` / `centered` / `banner`), `cardStyle`
  (`outline` / `filled` / `plain`) on Features, Testimonials, Pricing, Stats and CardGrid; CallToAction's
  `background` colours its panel (default `primary`). `primary` is a `.surface-inverse` token scope written into
  `globals.css` from the palette (light and dark), so cards, muted text and buttons inside keep their contrast.
- **Checklist:** `templates/nextjs_overlay/DESIGN_CHECKLIST.md` (rules, how the library keeps them, measurements,
  deviations). Library changes it needed: dark palette clamped to off-black / off-white, paragraphs `max-w-prose`,
  hero headline sized by length (`headlineClass`), split hero side by side from 1024 px, stats values and badges on
  the type scale (`text-2xl`, `text-sm`), no colour transitions (CardGrid lifts with `transition-transform` and a
  `motion-reduce` fallback).
- **Pnpm store:** Docker fills a named volume from the image only on first use, so the store volume is now
  `bga-pnpm-store-<base lock key>` (`store_volume()`); a new base gets a new, filled volume. `make down-all` removes
  them. **Rebuild `make runner-node` (done here) before the next `make up`.**
- **Verification:** `make test` (new `tests/test_fonts_and_variants.py`: pins, suggestions, warnings, editor schema,
  fonts.ts, store key, dark clamp, inverse scope, variant typing, fixture covers every variant; snapshots updated for
  the font imports and the clamped dark palettes); `BGA_SANDBOX_TESTS=1` frontend sandbox tests 7/7 (the section
  library, now with three variant pages, installs offline, type-checks, lints, builds and passes its smoke test);
  `scripts/design-check.mjs` on the fixture in all 5 presets × 6 pages × 390 / 768 / 1440 × light / dark (180
  views, installed with `--network none`): no rule failed, fonts report `loaded`, nav 65 px, headline ≤ 2 lines,
  CTA above the fold, ≤ 5 type sizes. Screenshots: `.data/shots/story17.7/<preset>/frontend/shots/`. A catalogue-only
  static site still plans `rendering: "renderer"` with no gaps (no engine call).
- **Deviations:**
  - The set covers 70 of 148 font uses in UI UX Pro Max's `typography.csv` and both fonts of 26 of its 74 pairings
    (the CSV has 91 families, a long tail incl. script-specific Noto fonts), not "most pairings". 12.6 should prefer
    covered pairings or swap the missing font with `closest_font`.
  - Body line length: 45–75 holds at the top; on a 390 px phone a paragraph holds ~40 characters.
  - shadcn primitives from the base (button transition, accordion and sheet animations) are left as they are.
  - Image backgrounds barely show with placeholder assets until Epic 15 brings real images.
