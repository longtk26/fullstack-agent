# Design skills for drafted sites (research, 2026-10-30)

Question: can **UI UX Pro Max** or **Taste Skill** help the drafter (2.4 + 12.4) produce a FrontendSpec that renders
as a good-looking site? The FrontendSpec is the contract between the drafter and the section renderer (Epic 17), so
any design help has to end up as spec values: theme, fonts, section order and variants, and content.

Outcome: **use UI UX Pro Max's data** (vendored CSVs) to pick the design direction in the drafter (Story 12.6), and
**use Taste Skill's rules only as a checklist** for the section library (17.7) and the drafter's copy rules. Neither
skill is installed into the generated workspaces, and neither skill's scripts run in our pipeline.

## UI UX Pro Max (`nextlevelbuilder/ui-ux-pro-max-skill`)

- MIT, v2.15.0, read at commit `28b3b8d` (2026-10-26). A Claude skill (`SKILL.md`) backed by CSV data and a Python
  BM25 search (`scripts/search.py`, `design_system.py`; standard library only).
- The parts that matter to us are the data files (`src/ui-ux-pro-max/data/`):

| File | Rows | What a row holds | Use in our drafter |
|---|---|---|---|
| `products.csv` | 192 | product type, keywords, recommended style, landing pattern, colour focus | match the requirement to a product type |
| `ui-reasoning.csv` | 192 | per product type: pattern, style priority, colour and type mood, key effects, **anti-patterns**, decision rules (JSON) | design notes and anti-patterns shown in review |
| `colors.csv` | 192 | per product type: shadcn-style tokens `primary`, `on-primary`, `secondary`, `accent`, `background`, `foreground`, `card`, `muted`, `muted-foreground`, `border`, `destructive`, `ring` (contrast adjusted) | fills `theme.colors` directly |
| `typography.csv` | 74 | heading / body Google font pairing, mood keywords, best-for | fills `theme.typography`; picks the 17.7 font set |
| `landing.csv` | 34 | landing pattern, section order, CTA placement | default section order of the home page |
| `styles.csv` | 88 (50 active) | visual style (Minimalism, Soft UI, Bento, Glassmorphism, …), effects, do-not-use-for | mapped onto our 5 theme presets + radius + density + variants |
| `ux-guidelines.csv`, `stacks/nextjs.csv`, `stacks/shadcn.csv` | 119 / 61 / 68 | do / don't rules with code | review checklist for the section library (17.7, 17.8) |

Example (`colors.csv`, *Restaurant/Food Service*): primary `#DC2626`, accent `#A16207`, background `#FEF2F2`,
foreground `#450A0A`. Our `ThemeColors` has `primary`, `secondary`, `accent`, `background`, `foreground`, `muted`,
`destructive`, and `frontend_theme.py` derives the rest, so a row maps 1:1 with no model-invented hex values.

The fonts in `typography.csv` cluster: 91 distinct families, but Inter, Space Grotesk, Plus Jakarta Sans, DM Sans,
Outfit, Playfair Display, IBM Plex Sans, Cormorant Garamond, EB Garamond, Poppins, Rubik, Nunito, Crimson Pro and
Source Sans 3 cover most pairings. That is about the size of the ~20-font `@fontsource` set planned in 17.7.

Caveats:
- Style recommendations lean on effects our renderer does not draw (Glassmorphism, Liquid Glass, Neumorphism,
  3D). We use the row's palette, fonts and pattern, and map the style onto our presets. We do not copy effects.
- Some palettes are loud (e.g. *Beauty/Spa*: pink `#EC4899` with a violet accent). Brand words in the requirement
  override the palette, and the review offers alternatives (12.6).
- The data changes often (frequent releases). We pin a commit and refresh on purpose, with a script that copies the
  CSVs and records the commit. We do not run their CLI or Python.

## Taste Skill (`Leonxlnx/taste-skill`, tasteskill.dev)

- MIT, "design-taste-frontend" v2 (experimental; the author says rule wording may change before 2.0.0). A skill made
  of a long `SKILL.md`, reference notes, JSON libraries (directions, palettes, type systems, heroes) and Node
  scripts: `draw.mjs` deals 3 of 20 art directions **at random**, `assets.mjs` fetches photos from open
  collections, and `lint.mjs` / `inspect.mjs` check the page in Chrome at 1440 / 768 / 390 px.
- It describes an agent-driven build loop: deal a direction, write copy, hand-build the page, inspect, fix (up to 3
  rounds). The author puts a build at "30 to 45 minutes and a few hundred thousand tokens".

Why it does not fit as a pipeline step:
- Epic 17 builds catalogue sites with **no engine call** (~44 s). A hand-built page plus a browser critique loop
  undoes that.
- The direction draw is random by design ("Adopt it. Do not blend it."). Our drafts must be repeatable and editable
  as spec values.
- Photos are fetched over the network at build time and need credits. That conflicts with decision IMG (Epic 15:
  generated SVGs, uploads and links).
- Several bans conflict with shadcn defaults our library uses: no shadows at rest, no 1px outlined boxes, no rows
  of identical cards, no glass, and no em-dashes anywhere in copy.

What we take (as rules, credited here):
- **Section library checklist (17.7):** one accent per page; one corner-radius system; two font families at most;
  five type sizes at most per page; body 16–20 px with line-height 1.45–1.6 and 45–75 characters per line; display
  tracking −0.02 to −0.05 em; hero headline two lines at most at every width; nav one line and ≤ 80 px tall;
  primary CTA visible without scrolling; dark mode uses off-black and off-white, never pure values; motion only on
  transform and opacity, staggered 60–90 ms, with a `prefers-reduced-motion` fallback.
- **Drafter copy rules (12.4):** hero subtext ≤ 20 words; no invented proof (testimonials, client logos, numbers
  and awards come from the requirement, or are listed as sample content in `assumptions[]`). This matches FR-07's
  "no invented policies".
- Later, maybe: the inspector's measurements (headline line count, overflow at 390 / 768 / 1440 px, contrast) fit
  the Playwright smoke check (14.3). Not planned yet.
