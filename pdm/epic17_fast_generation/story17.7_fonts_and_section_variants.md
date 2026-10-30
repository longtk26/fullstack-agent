# Story 17.7 — Fonts that load and section variants

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-22 · **Depends on:** 17.1, 17.2
**Planned:** after the main Epic 17 stories (agreed 2026-10-29); re-planned 2026-10-30 to come after 12.4 and
before 12.6, which picks fonts and variants from this story. Research:
[docs/research/design-skills.md](../../docs/research/design-skills.md).

## User story

As a user, I want the fonts I pick to really show on my site, and a few looks per section (not one fixed design),
so that a generated site feels designed while still being built without the engine.

## Acceptance criteria

- [ ] A curated set of about 20 Google fonts (sans, serif, display, mono) is part of the pinned base as
      `@fontsource` packages, so they install offline from the pre-warmed store and work in the static export.
      The theme's `headingFont` / `bodyFont` load the matching files; today only the CSS names them, and visitors
      without the font installed see a fallback (e.g. Northwind's Playfair Display shows as a generic serif).
      The set is chosen from the pairings in UI UX Pro Max's `typography.csv` (12.6), e.g. Inter, Space Grotesk,
      Plus Jakarta Sans, DM Sans, Outfit, IBM Plex Sans, Poppins, Rubik, Nunito, Source Sans 3, Playfair Display,
      Cormorant Garamond, EB Garamond, Crimson Pro, JetBrains Mono, so most of its pairings load.
- [ ] The validator warns when a font is outside the set and suggests the closest one; the editor schema lists
      the set.
- [ ] Section variants, typed in the props models (17.1): e.g. Hero `variant: "split" | "centered" | "banner"`,
      `background: "default" | "muted" | "primary" | "image"` on content sections, card style for list sections.
      Variants use the theme tokens only, so they follow every preset and light/dark.
- [ ] The section library and its variants pass a design checklist (from Taste Skill's page rules, see the
      research note): one accent per page, one radius system, two font families and five type sizes at most, body
      line length 45–75 characters, hero headline two lines at most at 390 / 768 / 1440 px, primary CTA above the
      fold, nav ≤ 80 px, off-black / off-white in dark mode, motion on transform and opacity only with a
      `prefers-reduced-motion` fallback. The checklist lives next to the library; deviations are noted there.
- [ ] The section-library fixture covers every variant; screenshots of each preset in the Status note.
- [ ] Still no engine call for a catalogue-only static site.

**Status:** open.
