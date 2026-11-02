# Varied, distinctive designs for drafted sites (research, 2026-11-02)

Question: drafted sites look alike. Can we drop UI UX Pro Max (12.6) and use a better way to make them more varied,
creative and attractive? Follow-up to [design-skills.md](design-skills.md).

Outcome: **removing UI UX Pro Max alone would not help**. Two things limit variety today: the section renderer can draw
only a few looks, and the direction is a lookup (one product type → one palette, font pairing and pattern). The plan
below borrows the direction method of **oil-ui** (`oil-oil/oil-ui`, MIT): concept from the product, five tone scales,
eight hero skeletons, a difference test between directions. Our code turns that method into spec values, so catalogue
sites still build with no engine call. UI UX Pro Max stays as a floor (contrast-checked palettes, font pairings,
anti-patterns, and "the category default" to move away from), not as the picker.

## Why our drafts look alike

- **Lookup, not design.** `design_direction.py` ranks product types with BM25 and takes that row's palette, fonts and
  landing pattern. Every spa is pink with Playfair Display, every restaurant red. The alternatives are other rows or
  small variations of the best row (next font pairing, another hero), so the three cards often differ only in
  colour.
- **Small renderer range.** A site varies by 5 presets, 3 hero variants (`split` is the default), 3 card styles,
  4 section backgrounds, radius, density, a palette and a font pair. Every Features section is a card grid, every
  Testimonials section a row of quotes. Two directions with different colours still have the same layout.
- **Category defaults by construction.** `PATTERN_SECTIONS` encodes the landing-page trope (Hero, Features,
  Testimonials or Stats, CallToAction) that oil-ui names as the pattern to break.
- **Nothing measures it.** No test or report shows how far apart two drafts or two directions are.

## Research

| Work | What it shows | Use for us |
|---|---|---|
| Design Creativity Bench (Kombai, Oct 2026, [arXiv 2610.11539](https://arxiv.org/abs/2610.11539), [code](https://github.com/kombai-io/design-creativity-bench)) | 80 tasks × 2 product domains. Best model 65.5 creativity vs humans 92.3; creative range 0.58 vs 0.90; brief compliance ~99% (models meet briefs but repeat themselves) | Its two measures, originality across runs and range across paired domains, for our diversity check |
| Interrogating Design Homogenization in Web Vibe Coding (UW / Microsoft Research, Mar 2026, [arXiv 2603.13036](https://arxiv.org/abs/2603.13036)) | Generating with no friction pushes sites toward the model's defaults; proposes "productive friction" | The review asks the user to choose between directions that really differ, not to accept a first draft |
| Design Theater (AIES 2026, [arXiv 2607.22928](https://arxiv.org/abs/2607.22928)) | >25% of the design rationale tools show is not built; outputs differ in colour but share layout. Design Homogeneity Index: visual, colour, layout (OmniParser + tree edit distance) | Show real screenshots in the review, not the model's description; measure layout separately from colour |
| Verbalized Sampling (ICML 2026, [arXiv 2510.01171](https://arxiv.org/abs/2510.01171)) | Asking for several candidates with probabilities gives 1.6–2.1× more diverse outputs with no training | One way to get distinct directions from one call |
| GUIDE ([arXiv 2609.21285](https://arxiv.org/pdf/2609.21285)) | Reference set + design.md + conformance scorer; designer feedback updates all three | Later: user picks feed the direction library |

Design-to-code tools (ScreenCoder, Design2Code, screenshot-to-code) target how faithfully code matches a screenshot.
That is not our gap.

## draw-ui (`oil-oil/draw-ui`)

A Chinese-language agent skill (README says MIT, no LICENSE file, ~530 stars). Flow: settle the page's purpose and
**one visual concept**, draw the page as an image (default `openai/gpt-image-2` through ZenMux or the OpenAI API), then
rebuild it in HTML / an existing project / a WeChat mini program, with Python scripts that measure colours and boxes
on the image and compare a browser capture against it.

Ideas worth taking:
- The concept is written as concrete composition, type, photo angle, proportion and colour relations, never
  "premium, warm, professional". The feature list decides what is on the page, not how it looks.
- Not every block becomes "centred title + equal cards + same padding"; sections get different weight and rhythm,
  while fonts, components and alignment stay one system.
- No invented testimonials, sales numbers or certifications (we already have this rule).

Why not as a step: image-first is for hand-built pages. Our renderer cannot reproduce an arbitrary drawn layout, so a
drawn mockup would promise a page we do not build (the Design Theater gap). An image costs an engine call per
direction and takes seconds.

## oil-ui (`oil-oil/oil-ui`)

Same author, MIT, ~2.6k stars, a broader design skill (a paid Pro edition exists; we use neither edition). Its
`references/design-direction.md` and `direction-persuasion.md` are the most concrete method we found for directions
that differ. What maps onto a spec:

- **Concept from the product, not adjectives.** Each direction starts from one "engine": a material in a setting, a
  concrete scene (time, place, light), a character archetype, a design movement or cultural grammar tied to the
  subject, the expressive means of another medium, or breaking one specific convention. Colour does not come from the
  engine's material (brass or darkroom metaphors push every product into the same colours).
- **Tone on five scales, each with evidence:** energy (quiet ↔ loud), finish (raw ↔ refined), density (sparse ↔
  dense), weight (light ↔ heavy), seriousness (playful ↔ solemn). The common failure is evidence pointing to loud and
  raw, delivered as beige cards with soft shadows: the model's default "quiet premium".
- **Translate vague words into decisions:** "premium" → type contrast, divider style, spacing scale, number of hues;
  "restrained" → accent ≤ 10% of the screen, motion limit, hue count.
- **Eight hero skeletons,** chosen before any copy is written: full-bleed image with type over it; one centred object
  or sentence in wide space; the product or object itself as the screen; full-bleed type (cropped or crossing the
  edge); full-width headline stacked over content; grid collage; vertical or diagonal type; left-right split. Split
  is the model's default: at most one direction per round uses it, with a reason.
- **Colour:** brand assets and the product's content first. Each direction has its own hue family; the classic
  failure is "one light, one dark, one warm". At least one direction leaves the category's default palette. A default
  for new brands: ~85% neutral canvas and controls, ~10% one low-value anchor block, ~5% one highlight.
- **Difference test:** any two directions share **at most one** of hero skeleton, fonts, colour, key visual; compare
  greyscale wireframes, not descriptions ("squint test": same light/dark masses means redo the skeleton); at least
  one direction breaks the category trope (landing page: hero, features, testimonials, CTA); no copying a reference
  site's fonts, palette and visuals together.
- **Each section has a form from the concept,** not the same module recoloured (e.g. features as a numbered ledger, a
  spec table or cards).
- **One memorable moment per direction,** everything else quiet.
- **Independent generation:** concepts come from fresh agents given only a fact pack (product facts, constraints, main
  object and action), at least three candidates, then an independent reviewer passes or rejects each direction card.

## Other skills

| Skill | Note |
|---|---|
| Anthropic `frontend-design`, Impeccable (`pbakaus/impeccable`, Apache 2.0) | Anti-default rules for hand-built UI (avoid Inter / Roboto everywhere, identical card grids, gradient text, glass by default). Rules for our checklist; not a step |
| `VoltAgent/awesome-design-md`, getdesign.md | DESIGN.md files describing real sites' design systems. Inspiration for abstract directions only; we do not offer "look like <brand>" |
| `nexu-io/open-design` | Open-source Claude Design alternative driving coding agents. Same hand-built model; not a fit for the renderer |
| Taste Skill | Already used as the 17.7 checklist ([design-skills.md](design-skills.md)) |

## What we take

1. **Wider renderer range** (still theme tokens only, still the 17.7 checklist):
   - Hero: the eight skeletons, replacing 3 variants (`banner` ≈ full-bleed image, `centered` ≈ centred object,
     `split` kept). Vertical / diagonal type only as a decorative label, never body text (legibility).
   - Section forms: Features as cards / numbered list / ledger / alternating rows; Testimonials as one large quote /
     grid / strip; Stats as large figures / inline row; CardGrid with a featured first item.
   - Tone tokens: the five scales map to concrete values in our code, e.g. energy → saturation and contrast budget;
     finish → radius, hairline borders vs shadows; density → spacing scale; weight → heading weight, type-scale ratio,
     size of colour blocks; seriousness → radius and motion amplitude.
   - Colour roles: neutral canvas, one anchor section (a dark or deep block), one highlight; section rhythm (alternating
     surfaces or hairline dividers).
   - More display faces in the font set (e.g. Fraunces, Instrument Serif, Bricolage Grotesque, Syne), since the 22
     current fonts are the ones every generated site uses.
2. **Directions as cards, generated, then checked by code.** The drafting engine gets a fact pack (no category
   template) and returns three direction cards in a schema: concept engine + one sentence, five tone values with
   evidence, hero skeleton, fonts, colour (hex + where it comes from), key visual, section forms, memorable moment, what
   it gives up. Three independent parallel calls, or one call with verbalized sampling. Our code then: checks contrast
   and bundled fonts, turns tone into tokens, runs the difference test (≤ 1 shared of skeleton / fonts / hue family /
   key visual; ≤ 1 split hero; ≥ 1 direction off the category's default section order) and re-asks only for a
   failing card. A stored seed keeps a draft repeatable; "try another direction" is a new seed.
3. **UI UX Pro Max as the floor.** Its row for the matched product type becomes "the category default" in the fact
   pack (what to move away from), plus anti-patterns and a contrast-safe fallback palette when the engine's colours
   fail. The fake engine samples directions from a curated library of concept engines with a seeded RNG.
4. **Real previews.** The Design panel shows each direction's home page rendered by the renderer (no engine call),
   with a greyscale "squint" toggle, not swatches and a description. The direction's concept also drives the photo
   prompt style (today `PHOTO_STYLES_BY_PRESET`, by preset).
5. **Measure first.** A diversity report: N drafts of one brief, and paired domains (clinic / pharmacy, spa / gym)
   in the spirit of Design Creativity Bench; distance over direction fields, layout skeleton, and greyscale
   screenshot similarity. Record today's numbers before changing anything, then show the change moves them.

Not taken: image-first mockups as the design source (above), oil-ui's reference-site screenshots at draft time
(network access, brand-copy risk), and any skill's scripts.

## Icons (added 2026-11-02)

Today: the pinned base ships `lucide-react` 1.62, and an asset can be `lucide:<Name>` (validated against
`templates/nextjs_base/lucide-icons.txt`, `FE_UNKNOWN_ICON`). But **no library section draws an icon**:
`FeatureItem` has no `icon` field (17.1 left it for Epic 15), so drafted sites have no icons at all.

Findings:
- **Icon sets converge too.** oil-ui (`references/visual-language.md`): the model default is Lucide or Heroicons
  (24 px, 2 px stroke, round caps) on every direction. The icon set is part of a direction, like the fonts: name the
  set, stroke and caps, or use none. Its mapping: refined / editorial → Phosphor Thin or Light, Iconoir; industrial /
  tools → Carbon, Material Symbols Sharp, Radix; friendly / consumer → Phosphor Fill or Duotone; pixel / retro →
  Pixelarticons. Rules: one set per site; stroke follows the text weight (1–1.5 px with light type, 2 px+ or filled
  with heavy type); icon 1–1.25× the font size, aligned on the visual centre; editorial directions often use
  characters instead (→ ↗ § numbers); no icon on every heading.
- **Phosphor** (`@phosphor-icons/react`, MIT): ~1,200+ icons in six weights (thin, light, regular, bold, fill,
  duotone) via a `weight` prop, tree-shakable, an SSR submodule for server components. One package gives several
  looks.
- **Picking the right icon.** Models invent names (our `FE_UNKNOWN_ICON` exists for this). Matching keywords to icon
  *file names* by embeddings is fragile: SlideDeck AI's helper mapped "handshake" → `dash-circle` and "Ferry" →
  `cart`. Lucide keeps per-icon metadata with `tags` and `categories` in its repo; ranking over tags + categories
  (lexical, like our BM25 in `design_direction.py`) is more reliable than names alone.
- **Generated icon sets** keep drifting in style across a set (the main complaint in vendor guides; research on
  consistent sets is thin). Epic 15 already decided icons are not generated; that still holds.

What we take:
1. An optional `icon` on list items (Features, Stats, ContactInfo, Pricing features), rendered by the library.
2. The drafter writes an icon **intent** (a few words); our code resolves it to a real name by ranking the set's
   tags and categories, with a `closest_icon` suggestion in the validator (like `closest_font`). The fake engine
   uses the same resolver.
3. Icon treatment is a direction field: `none` (numbers or characters) / `line` / `filled tile` / `duotone`, plus
   set and weight from the tone (finish and weight scales). Lucide's `strokeWidth` covers the first step; Phosphor
   joins the pinned base as the second set (offline, exact pins, like the 17.7 fonts). One set per site.

## Motion (added 2026-11-02)

Today: the only library motion is the CardGrid hover lift; the 17.7 checklist allows transform and opacity only, with
a `prefers-reduced-motion` fallback. `tw-animate-css` is in the base. `scripts/design-check.mjs` does not control
motion, so entrance animations would be screenshotted half-way.

Findings:
- **oil-ui** (`references/motion.md`, `scroll-narrative.md`): every interface first gets **three** motions: feedback
  on the main action (press scale 0.96–0.98, 150–300 ms), one state change that shows where things come from and go
  (a sliding tab indicator, an expanding panel), and one staged entrance on first visit (main element first, others
  40–80 ms apart, ≤ 600 ms total, played once). Landing pages add section reveals **by content** (stats count to
  their value, lists unfold in reading order, images unmask while scaling 1.08 → 1, headlines rise by line), played
  once, not one fade-up for every block. The **feel comes from the direction**, named as an action + an object with
  spring values: click (magnet, 350–400 / 10–15), slide (drawer, 250–300 / 20–25), flow (honey, 150–200 / 30–40),
  drop (hammer, 400–500 / 5–10), bounce (ball, 300 / 8), float (balloon, 100 / 25). Heavy materials click and
  drop, light ones float and flow; a loud, raw direction may use hard 80–150 ms linear cuts on purpose. Overshoot
  ≤ 1–2% on large surfaces, 10–20% on small badges. Springs can be written as CSS `linear()` easings (sample the
  spring curve at 20–30 points), so no JS library is needed. Exits run at 60–70% of the entry time.
- **Browser support:** scroll-driven CSS animations (`animation-timeline: view()`) work in Chrome / Edge and Safari
  26; Firefox stable still had them behind a flag in mid-2026 (Interop 2026 item). Use them only as an enhancement:
  content must be fully visible without them.
- **Libraries:** Motion (`motion/react`, MIT) is the usual React choice for layout and gesture animation. GSAP is
  now free, but Motion's comparison page says its licence forbids use in a tool that competes with Webflow, which a
  site generator may be. Read the GSAP licence before ever adding it; until then, no GSAP.
- **Research:** generated animation code needs checking by measuring the motion, not by trusting it. MoVer (Stanford,
  ACM TOG 2025, [arXiv 2502.13372](https://arxiv.org/abs/2502.13372)) checks spatio-temporal predicates on SVG
  animations; its LLM pipeline was right on 58.8% of prompts first time and ~93.6% after repeated fixes. LogoMotion
  (CHI 2025, [arXiv 2405.07065](https://arxiv.org/abs/2405.07065)) renders, spots visual errors and repairs the code.
  Keyframer (2024, [arXiv 2402.06071](https://arxiv.org/abs/2402.06071)) lets users iterate on LLM-written CSS
  animation.

What we take:
1. **Motion presets in the library, chosen by the direction**, not written per site: the three baseline motions in
   every section that has them (buttons, Tabs / Faq indicator, hero entrance), section reveals by content type, and a
   `motion` field on the direction (feel preset from the tone: energy, weight, seriousness; `none` allowed).
   CSS transitions, `@starting-style` and `linear()` springs, with a small client observer for reveal-once. No
   animation library at first; Motion only if a layout animation needs it.
2. **One signature moment per direction** (from the direction card), picked from a small tested set: count-up stats,
   a headline that rises by line, an image unmask, a sliding indicator. A scroll-driven hero (depth, or a wordmark
   that shrinks into the nav) comes later and only as an enhancement.
3. **Safety rules in the checklist:** content is visible when JS or the animation does not run; reduced motion puts
   everything in its final state; motion never delays a primary action; transform and opacity only (unchanged).
4. **Checks:** `design-check.mjs` takes layout screenshots with reduced motion emulated, then a second pass with motion
   on that fails if any element is still hidden (opacity 0 or off-screen) after the reveals finish. Custom components
   (17.3) get the same rules in their prompt and the same check, since their motion is engine-written (the MoVer /
   LogoMotion lesson).

## Proposed order (not yet in the backlog)

1. Diversity report and baseline (5).
2. Renderer range: hero skeletons, section forms, tone tokens, colour roles, display fonts (1).
3. Direction cards, difference test, UI UX Pro Max as floor (2, 3).
4. Icons: `icon` on items, intent → name resolver, treatment and set per direction, Phosphor in the base.
5. Motion: baseline motions and reveals in the library, feel presets per direction, one signature moment, the two-pass
   design check.
6. Rendered previews and squint view in the Design panel; concept-driven photo style (4).

Icons and motion fields belong in the direction card (3), so 4 and 5 come after it; their library work can start
alongside 2.
