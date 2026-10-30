# Section library design checklist (Story 17.7)

The rules every section and variant in `files/renderer` (and the shared `files/common` layout pieces) keeps, so a
site built from the FrontendSpec without the engine looks designed in every theme preset, light and dark. They come
from Taste Skill's page rules (MIT, see `docs/research/design-skills.md`), used as rules only.

How it is checked: the unit tests (`tests/test_fonts_and_variants.py`) cover what the generator controls (fonts,
dark-mode colours, variant typing, the headline length warning); `scripts/design-check.mjs` measures a built site
at 390 / 768 / 1440 px, light and dark (the section-library fixture in every preset, screenshots under
`.data/shots/story17.7/`). Re-run it when a section or variant changes.

| Rule | How the library keeps it | Measured (fixture, 5 presets × 6 pages × 3 widths × 2 schemes) |
|---|---|---|
| One accent per page | `primary` is the only accent colour (eyebrows, icons, highlighted plan, buttons). The `accent` token is only shadcn's hover tint | by review |
| One radius system | Every corner is a `rounded-*` step derived from the theme's `--radius` (`globals.css`); no fixed pixel radii | by review |
| Two font families at most | `--font-display` (headings) and `--font-body`; both from the theme, loaded from `@fontsource` | the theme's 1–2 families in every view, and the same families report `loaded` in `document.fonts` |
| Five type sizes at most per page | `text-sm`, `text-base`, `text-lg`, `text-2xl` and one hero size (`headlineClass`); stats and prices use `text-2xl` | 4–5 per view (the hero is the only size that changes with the width: 24–60 px) |
| Body line length 45–75 characters | Paragraphs are `max-w-prose` (65ch) | ≤ 75 everywhere (longest 41 in the fixture's copy); see deviations for the 45 minimum |
| Hero headline two lines at most at 390 / 768 / 1440 px | `headlineClass` sizes the headline by length; the validator warns above 50 characters (`FE_DESIGN_RULE`) | 1–2 lines in every view; 42–52-character headlines in Poppins and Playfair Display also stay at 2 |
| Primary CTA above the fold | The hero's first link is its primary CTA | above the fold in every view |
| Nav ≤ 80 px | Header `h-16` (64 px), one line; the menu collapses below `md` | 65 px |
| Off-black / off-white in dark mode | `frontend_theme.py` clamps the dark palette to `#0a0a0a` / `#fafafa` | body `#0a0a0a`…`#14122f` (tinted per preset) with `#fafafa` / `#f8fafc` text; never `#000` / `#fff` |
| Motion on transform and opacity only, with a `prefers-reduced-motion` fallback | The only library motion is the CardGrid hover lift (`transition-transform`, `motion-reduce:` off); colour changes are instant | by review |

## Variants

| Variant | Where | Values |
|---|---|---|
| `background` | every content section | `default`, `muted`, `primary` (the `surface-inverse` token scope swaps primary and background, so cards, muted text and buttons keep contrast), `image` (`backgroundImage` under a scrim in the page colour) |
| `variant` | Hero | `split` (text beside the image from 1024 px), `centered`, `banner` (full width; the image behind the text, or the primary colour) |
| `cardStyle` | Features, Testimonials, Pricing, Stats, CardGrid | `outline` (shadcn card), `filled` (muted surface, no outline), `plain` (no surface) |
| `background` on CallToAction | the panel | `primary` by default, `default` = outlined panel |

## Deviations

- **45-character minimum:** a full-width paragraph on a 390 px phone holds about 40 characters at 16 px. The
  library caps the maximum (`max-w-prose`) and accepts shorter lines on phones.
- **shadcn primitives keep their own motion and chips:** the pinned base's button (`transition-all`), accordion and
  sheet animations are not edited (they belong to the base, `make frontend-base`). The library's own badges use the
  `text-sm` step instead of the primitive's 12 px so a page stays at five sizes.
- **Image backgrounds are faint until Epic 15:** placeholder assets are pale gradients, so `background: "image"` and
  the banner's backdrop barely show under the scrim. Real images (Epic 15) make them visible; the scrim keeps text
  readable either way.
