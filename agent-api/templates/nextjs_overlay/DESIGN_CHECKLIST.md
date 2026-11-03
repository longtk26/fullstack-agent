# Section library design checklist (Story 17.7)

The rules every section and variant in `files/renderer` (and the shared `files/common` layout pieces) keeps, so a
site built from the FrontendSpec without the engine looks designed in every theme preset, light and dark. They come
from Taste Skill's page rules (MIT, see `docs/research/design-skills.md`), used as rules only.

How it is checked: the unit tests (`tests/test_fonts_and_variants.py`, `tests/test_design_tone.py`) cover what the
generator controls (fonts, dark-mode colours, variant typing, the headline length warning, tone tokens);
`scripts/design-check.mjs` measures a built site at 390 / 768 / 1440 px, light and dark. `make design-check-fixture`
builds the section-library fixture in every preset (`ARGS="--combos"`: in six tone, font and preset combinations,
Story 20.3) and checks the measured rules below; screenshots under `.data/shots/`. Re-run it when a section or
variant changes.

| Rule | How the library keeps it | Measured (fixture, 5 presets × 6 pages × 3 widths × 2 schemes) |
|---|---|---|
| One accent per page | `primary` is the only accent colour (eyebrows, icons, highlighted plan, buttons). The `accent` token is only shadcn's hover tint | by review |
| One radius system | Every corner is a `rounded-*` step derived from the theme's `--radius` (`globals.css`); no fixed pixel radii | by review |
| Two font families at most | `--font-display` (headings) and `--font-body`; both from the theme, loaded from `@fontsource` | the theme's 1–2 families in every view, and the same families report `loaded` in `document.fonts` |
| Five type sizes at most per page | `text-sm`, `text-base`, `text-lg`, `text-2xl` and one hero size (`headlineClass` / `displayClass`); stats, figures, prices, statements and the vertical hero label use `text-2xl` or the hero's size | 4–5 per view (the hero is the only size that changes with the width: 24–60 px) |
| Body line length 45–75 characters | Paragraphs are `max-w-prose` (65ch) | ≤ 75 everywhere (longest 41 in the fixture's copy); see deviations for the 45 minimum |
| Hero headline two lines at most at 390 / 768 / 1440 px | `headlineClass` sizes the headline by length; wide faces and capitals shrink the hero sizes (`--hero-<step>`, `display_scale` from `Font.width`, case and tracking, Story 20.3); the validator warns above 50 characters (`FE_DESIGN_RULE`) | 1–2 lines in every view; 42–52-character headlines in Poppins and Playfair Display also stay at 2 |
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
| `variant` (Story 20.2) | Hero | also `stage` (the image is the first screen, text on its lower edge), `type` (oversized headline, `displayClass`, no image), `stacked` (full-width headline, text and actions in a row, wide image), `collage` (text beside 2–4 images; fewer → `split`, validator warning), `vertical` (the eyebrow as a rotated label at the headline's size, horizontal on phones) |
| `form` (Story 20.2) | Features, Testimonials, Stats | Features `cards` / `list` (numbered rows) / `ledger` (hairline rows) / `alternating` (image and text rows; without item images → `list`, validator warning); Testimonials `cards` / `quote` / `strip` (a keyboard-scrollable row); Stats `cards` / `figures` (no boxes, accent rule) / `inline` |
| `featured` (Story 20.2) | CardGrid | the first record spans two columns from 640 px |
| `rhythm` (Story 20.2) | a page | `uniform`; `alternate` (sections without a background alternate page colour and muted, written into `site.json`); `dividers` (a hairline between sections) |
| `form` (Story 20.8) | Steps, Timeline, Team, PriceList, Location, Comparison, Statement | Steps `numbered` / `horizontal` / `connected`; Timeline `vertical` / `alternating`; Team `grid` / `list` / `portraits`; PriceList `menu` / `columns` / `cards`; Location `split` / `card` / `band`; Comparison `table` (scrolls sideways in a focusable region) / `cards`; Statement `large` / `quote` / `band` |

## Tone tokens (Story 20.3)

Optional theme fields; without them a site looks as before. `orchestrator/design_tone.py` maps a direction's five
tone scales to them (the table is in its docstring).

| Token | Drawn as |
|---|---|
| `typography.headingWeight`, `headingCase`, `tracking` | the `heading` utility (`globals.css`) on hero and section headings: `--heading-weight` (600), `--heading-tracking` (−0.025em; `wide` with capitals), `--heading-case`. Capitals only on display headings (h1, h2), never on statements or body text |
| `typography.ratio` | the display steps of the type scale (`--text-2xl` … `--text-9xl` in `@theme`) and the hero sizes: `tight` smaller, `dramatic` larger (on the hero only the steps of short headlines and the `type` layout, `6xl` and up: longer headlines already fill two lines) |
| `surface` | cards: `outline` (shadcn's hairline ring), `flat` (no ring, no shadow), `raised` (soft shadow instead of the ring); unlayered rules in `globals.css`, the `filled` and `plain` card styles keep their own look |
| `colorArea` | `site.json` per page: `minimal` (call-to-action panels muted, colour on buttons), `block` (one anchor section in the primary colour: the first call to action, else the last content section), `bold` (also the hero). Sections that name a background keep it |

Fonts: eight faces with more character joined the set (Fraunces, Instrument Serif, Newsreader, Bricolage Grotesque,
Syne, Archivo, Unbounded, Familjen Grotesk; OFL). Each bundled font has a rough `width` against Inter; wide faces
(Unbounded, Syne, Montserrat, the monospace faces) shrink the hero sizes so headlines keep to two lines.

## Directions and app pages (Story 20.4)

A direction card sets the theme, tone tokens, hero layout, section forms and rhythm for every page, and composes the
home page from the drafted sections; it adds no new drawing rules. In a dynamic app the data pages (DataTable, List,
DetailView, Form, ActionBar, CardGrid on the API) keep their structure and take the direction through the same
tokens: section headings and the record title use the `heading` utility and the heading face, record panels are
cards (so `surface` applies), and colour, radius and density come from the theme. They are measured on the mock API
(`make design-check-fixture --spec <dynamic spec> --backend <its BackendSpec>`); a page without a hero has no
"CTA above the fold" measurement.

## Icons (Story 20.5)

- **One set per site**, from `theme.icons` (`lucide` / `phosphor` / `none`), with a weight (Lucide draws thin to bold
  as stroke widths 1 / 1.5 / 2 / 2.5; fill and duotone are Phosphor's) and a treatment (`plain`, or `tile`: a 40 px
  rounded square in the muted tone). Items carry a reference or an intent; the generator resolves it to the site's set
  (`frontend_spec/icons.py`) and `src/components/renderer/icons.ts` imports only the icons the site uses.
- **Where:** Features (above a card's title, in place of the list numeral, before a ledger title), Stats (heading a
  card, by a figure's label, before an inline value), Pricing (by a plan's name). Never on headings. The library's own
  marks (checks, minus, contact details, opening hours) are drawn in the site's set through `Icon glyph`.
- **Size and meaning:** 1.25 × the text they sit with, `aria-hidden` (the text carries the meaning), the primary
  colour. With `none`, content icons and decorative marks are left out and lists keep their numbers; checks stay.

## Motion (Story 20.6)

- **Only when it is safe:** the page's inline script sets `html[data-motion="on"]` when JavaScript runs and the
  visitor has not asked for reduced motion, and removes it if the page has not come alive within 3 s. Every rule is
  scoped to it, so without JavaScript or with reduced motion every element is in its final state.
- **Presets, not per-site code:** `theme.motion.feel` picks a spring preset (`orchestrator/frontend_motion.py`):
  durations 120–800 ms, easings as CSS `linear()` (surfaces overshoot ≤ 2%, marks ≤ 15%), `cut` as steps.
- **Three baseline motions:** buttons press to 0.97; the Tabs indicator grows with the feel (Faq keeps the base
  accordion's height animation); the hero enters headline → text → actions → image, one stagger apart, ≤ 600 ms.
- **Reveals by content:** below the hero each section reveals once when 15% (or 240 px) of it is visible:
  headings, cards, list items, figures, quotes, images and tables rise or slide in with the feel, followers one
  stagger apart (at most five), images settle from 1.08 scale; stats count up.
- **One signature moment:** `countUp` (longer count), `headlineRise` (the hero headline rises from a mask),
  `imageUnmask` (the hero image unmasks from the side), `indicator` (navigation links underline on hover and for the
  current page).
- **Properties:** `opacity`, `translate`, `scale`; `clip-path` for the two signature masks only.
- **Measured:** `make design-check-fixture ARGS="--motion"`: with motion on, the call to action is fully visible in
  under 1 s and nothing is left transparent or displaced after scrolling; with JavaScript off nothing is hidden.

## Deviations

- **45-character minimum:** a full-width paragraph on a 390 px phone holds about 40 characters at 16 px. The
  library caps the maximum (`max-w-prose`) and accepts shorter lines on phones.
- **shadcn primitives keep their own motion and chips:** the pinned base's button (`transition-all`), accordion and
  sheet animations are not edited (they belong to the base, `make frontend-base`). The library's own badges use the
  `text-sm` step instead of the primitive's 12 px so a page stays at five sizes.
- **Figures and statements stay at `text-2xl` (Story 20.2, 20.8):** a larger number or statement would add a sixth
  size on pages with a hero; they differ from cards by structure (no boxes, an accent rule, the heading face and
  weight), not by size. Measured: the first figures draft at `text-5xl` gave 6 sizes on the stage page at 1440 px.
- **The `type` hero is not cropped at the edge:** cropping display type hurts reading on phones; it is set as large
  as the two-line rule allows instead.
- **Tabs indicator grows rather than slides (Story 20.6):** the base's tabs draw their indicator per trigger; a
  sliding one would mean editing the primitive. Faq keeps the base accordion's own height animation.
- **UI chrome stays Lucide (Story 20.5):** the menu button, theme toggle and error alert are controls from the base,
  like the shadcn primitives; only content icons and the library's marks follow the site's set.
- **Image backgrounds are faint until Epic 15:** placeholder assets are pale gradients, so `background: "image"` and
  the banner's backdrop barely show under the scrim. Real images (Epic 15) make them visible; the scrim keeps text
  readable either way.
