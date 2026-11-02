# Epic 20 — Design diversity: distinct directions, icons and motion

## Overview

Drafted sites look alike. Two spa requirements get the same pink palette, Playfair Display and banner hero; a
clinic and a pharmacy differ only in colour; no site has an icon, and nothing moves. The cause is not one piece of
data but how a look is chosen and how much the renderer can draw:

| Finding (code, 2026-11-02) | Effect |
|---|---|
| `design_direction.py` maps the requirement to a UI UX Pro Max product type (BM25) and takes that row's palette, font pairing and landing pattern | One category → one look; the 2 alternatives are mostly other rows or small variations of the same row |
| The renderer varies by 5 presets, 3 hero variants (`split` by default), 3 card styles, 4 section backgrounds, radius, density | Two directions with different colours still have the same layout; every Features section is a card grid |
| `PATTERN_SECTIONS` encodes Hero → Features → Testimonials / Stats → CallToAction, and prompt v7 says "build the home page from the brief's sections"; when the requirement has no proof or questions, v7 asks for generic sample content | Every site gets the same sections (FAQ, testimonials, a CTA band, "Explore …" buttons), whatever the requirement says |
| About ten marketing sections in the catalogue | Different businesses are squeezed into the same few sections |
| `FeatureItem` has no `icon`; no library section draws one | Sites have no icons, although `lucide:<Name>` assets exist |
| The only library motion is the CardGrid hover lift | Pages feel like screenshots |
| Nothing measures how far apart two drafts or two directions are | "More varied" cannot be checked |

Research: [docs/research/design-diversity.md](../../docs/research/design-diversity.md) (Design Creativity Bench,
Design Homogenization, Design Theater, Verbalized Sampling, oil-ui's direction method, draw-ui, icon sets, motion,
MoVer / LogoMotion).

This epic makes each draft come with **three directions that really differ** (layout, type, colour, imagery,
icons, motion), each fitting the requirement, while generation stays as it is: catalogue sites are built by the
renderer from spec values, with no engine call. Epic 16 (revisions) is revised after this epic, since its theme
editor and "try another direction" must work on the new fields.

**Requirements:** add FR-33 (distinct design directions, icons and motion) to `requirements.md` when the epic is
accepted; FR-24 (design direction) and FR-22 (FrontendSpec) are extended.

## How we diversify (decisions proposed for review)

| # | Decision | Instead of |
|---|---|---|
| D1 | **Directions are generated, not looked up.** The drafting engine writes three **direction cards** (oil-ui's method, reduced to what the renderer draws): a concept from the product (material in a setting, a scene, a character, a design tradition, another medium, or one broken convention) in one sentence, five tone values with evidence, hero layout, fonts, colour with where it comes from, key visual, section forms, icon style, motion feel, one signature moment, and what it gives up | BM25 product type → one CSV row |
| D2 | **Code checks and fills, the model chooses.** Our code validates each card (contrast AA light / dark, bundled fonts, known icon set), turns the tone into theme tokens, and runs the **difference test**; only a failing card is asked again | Trusting the model's description (Design Theater: >25% of stated rationale is not built) |
| D3 | **Difference test** between the three directions: any two share **at most one** of hero layout, heading font, hue family (primary hue within 30°, or both neutral), key visual kind; at most one `split` hero; at least one direction leaves the category's default home order | Alternatives that differ only in colour |
| D4 | **The renderer stays the only builder.** Every new look is a typed spec value and a library variant: 8 hero layouts, section forms, tone tokens, colour roles, icon styles, motion presets. No image-first mockups, no per-site animation or layout code | draw-ui's image → code (our renderer cannot reproduce a drawn layout) |
| D5 | **UI UX Pro Max becomes the floor.** Its matched row goes into the engine's fact pack as "the category default to move away from", with its anti-patterns; its contrast-safe palette is the fallback when a card's colours fail twice. The vendored data and ranker stay | It picking the look |
| D6 | **Icons:** the drafter writes an icon *intent* (a few words); code resolves it to a real icon by ranking the set's tags and categories. Lucide (today) plus **Phosphor** (six weights) in the pinned base; one set per site; style from the direction (`none` / line / filled tile / duotone) | Model-invented icon names; Lucide 2 px on every site |
| D7 | **Motion:** presets in the section library, chosen by the direction: three baseline motions (button feedback, one state change with continuity, a staged first entrance), section reveals by content, one signature moment. CSS transitions, `@starting-style`, spring easings as `linear()`; no animation library at first, **no GSAP** (its licence excludes tools competing with Webflow) | Per-site generated animation (MoVer: 58.8% right first time) |
| D8 | **Measure first.** A diversity report with a baseline from today's code, run again at each checkpoint | Judging by eye |
| D9 | **Repeatable.** A draft stores its direction seed; the same draft re-applies the same directions; "another direction" is a new seed. The fake engine samples a curated library of concept engines with that seed | Randomness that cannot be reproduced |
| D10 | **One click (19.10) still works:** the first direction is applied automatically; the other two stay in the draft and the review | Asking the user before every draft |
| D11 | **Content decides the sections.** A section exists only when the requirement gives content for it (no FAQ without questions, no testimonials or stats without real ones; missing ones become assumptions, not samples). The catalogue grows by seven content sections (Steps, Timeline, Team, PriceList, Location, Comparison, Statement); each direction composes its own home page from the drafted content; stock phrases ("Explore …", "Why choose us") are avoided and flagged | A landing-page template filled with sample content |

```
 requirement ─▶ fact pack (product facts, constraints, main object and action,
                 category default from UI UX Pro Max, anti-patterns)
                     │
                     ▼  draft_frontend_spec (one call; three cards, verbalized-sampling style)
             3 direction cards ──▶ validate (contrast, fonts, icon set) ──▶ tone → tokens
                     │                                                        │
                     └──── difference test fails? re-ask that card only ◀─────┘
                     │
                     ▼
   theme: tokens, colour roles, fonts, icons, motion + theme.direction {concept, tone, seed, …}
   pages: hero layout, section forms, home order, icon intents → icon names
                     │
                     ▼  generation (unchanged): section renderer, no engine call
   site ── design-check (reduced motion pass + motion pass) ── diversity report
```

## Expected output

What the user gets:
- A draft with **three directions that look different at a glance**: different first-screen structure, type,
  colour family and imagery, each with a one-line concept and "what it gives up". The Design panel shows each
  direction's **real home page** (rendered, not swatches) with a greyscale "squint" view; switching keeps pages and
  copy.
- Sites with **icons** that match the text and the direction (or deliberately none), and **motion** that fits the
  direction: buttons respond, tabs and FAQ items move with continuity, sections enter by content once, one signature
  moment per site.
- Nothing slower or more fragile: static sites still build with **0 engine calls**, everything passes the design
  checklist, and users with reduced motion get a complete, still page.

Measured targets (the diversity report, `scripts/design-diversity.*`, on the golden requirement set):

| Measure | How | Target |
|---|---|---|
| Directions within a draft | difference test fields + greyscale screenshot similarity of the three home pages at 1440 px | 100% of drafts pass the difference test; screenshot similarity below the threshold set from the baseline |
| Same brief, 5 drafts | distinct (hero layout, heading font, hue family) triples across the 15 directions | ≥ 10 distinct (baseline expected ≤ 3) |
| Paired domains (clinic / pharmacy, spa / gym, bakery / coffee shop, law firm / accountant) | the first directions of each pair | differ in ≥ 2 of the 4 visual fields |
| Category trope | home order of the three directions | ≥ 1 of 3 off the category default |
| Sections from content (real engine, final check) | section frequency across the golden set; home-composition Jaccard between different requirements; repeated headings and CTA labels | optional sections (Faq, Testimonials, Stats, Pricing, CallToAction) only with content from the requirement; no optional type in > 40% of drafts; mean Jaccard ≤ 0.5; 0 stock phrases after repair |
| Quality floor | contrast AA light / dark, design checklist at 390 / 768 / 1440 × light / dark, fonts loaded, no element hidden after motion | no failures |
| Icons | icon intents resolved to a real icon; FE_UNKNOWN_ICON on drafts | 100% resolved; 0 warnings |
| Cost | draft time and engine calls per draft (`spec_drafts.started_at` → `finished_at`, `usage`); generation time and engine calls | draft time ≤ +20% of today's baseline; generation unchanged (0 engine calls for catalogue sites); the report also gives **draft + generation** time, which the UI does not show yet (see the note in `pdm/README.md`) |

## Stories

| # | Story | Phase | Depends on |
|---|---|---|---|
| 20.1 | [Diversity report and baseline](story20.1_diversity_report.md) | A | 12.6, 17.7 |
| 20.2 | [Hero layouts and section forms](story20.2_hero_layouts_and_section_forms.md) | B | 17.7 |
| 20.3 | [Tone tokens, colour roles and display fonts](story20.3_tone_tokens_and_fonts.md) | B | 17.7 |
| 20.4 | [Direction cards and the difference test](story20.4_direction_cards.md) | C | 20.2, 20.3, 12.6 |
| 20.5 | [Icons](story20.5_icons.md) | D | 20.4, 15.1 |
| 20.6 | [Motion](story20.6_motion.md) | D | 20.4 |
| 20.7 | [Design panel: rendered previews, squint view, concept-driven photos](story20.7_design_panel_previews.md) | E | 20.4, 19.3 |
| 20.8 | [New section types](story20.8_new_section_types.md) | B | 17.7 |
| 20.9 | [Content-led pages: sections from the requirement, not from a template](story20.9_content_led_pages.md) | C | 20.4, 20.8 |

Scope of each (details, steps and acceptance criteria in the story files):

**20.1 Diversity report and baseline.** A script that drafts the golden requirement set with the fake engine (and,
only with the user's yes, a real engine), renders the three directions' home pages, and reports the measures above
(field overlap, distinct triples, paired-domain distance, greyscale screenshot similarity, trope check). Golden set:
`examples/requirements/` plus new paired-domain requirements in `examples/requirements/diversity/`. The baseline from
today's code is recorded in this epic's Status note and sets the screenshot-similarity threshold.

**20.2 Hero layouts and section forms.** `HeroVariant` grows from 3 to 8 (additive, `split` stays valid):
`split`, `centered` (one object or sentence in wide space), `banner` (full-bleed image, text over it), `stage` (the
product or object is the first screen), `type` (full-bleed type, may crop at the edge), `stacked` (full-width
headline over content), `collage` (grid collage), `vertical` (a vertical or rotated display label; body text never
rotated). Section forms: Features `cards` / `list` (numbered) / `ledger` (hairline rows) / `alternating`;
Testimonials `cards` / `quote` (one large quote) / `strip`; Stats `cards` / `figures` / `inline`; CardGrid an
optional featured first item. A page `rhythm`: `uniform` / `alternate` / `dividers`. Theme tokens only; the
fixture covers every variant; the 17.7 checklist holds (headline ≤ 2 lines, CTA above the fold, nav ≤ 80 px).

**20.3 Tone tokens, colour roles and display fonts.** Explicit, editable theme tokens that the tone maps to (exact
list fixed in the story): surface (`flat` / `outline` / `raised`), heading weight, heading case and tracking,
type-scale ratio, colour area (`minimal` / `block` / `bold`: how much of the page carries colour), plus the existing
radius and density. Colour roles: neutral canvas, one anchor section, one highlight. A mapping from the five tone
scales (energy, finish, density, weight, seriousness; 1–5 each) to those tokens lives in our code and is unit
tested. 6–8 display faces join the bundled set (e.g. Fraunces, Instrument Serif, Bricolage Grotesque, Syne), so
drafts are not limited to the faces every generated site uses.

**20.4 Direction cards and the difference test.** The direction card schema (D1) and `theme.direction` grows
(additive): `concept`, `engine`, `tone`, `seed`, `givesUp`, `source`. The fact pack and a new prompt version
(`draft_frontend_spec@v8`) ask for three cards in one call; validation, tone → tokens, difference test, re-ask of a
failing card (at most 2 rounds, then the floor palette / next free hero layout); UI UX Pro Max as the floor (D5);
seeds (D9). The fake engine gets a curated library of ~40 concept engines sampled by seed. The UI mirror
(`agent-ui/src/features/specs/lib/design-direction.ts`) applies a card with the same rules. Report: the targets
for directions within a draft, same brief, paired domains and trope are met with the fake engine.

**20.5 Icons.** Optional `icon` on Features, Stats, ContactInfo and Pricing items; `theme.icons` (`set`:
`lucide` / `phosphor` / `none`, `weight`, `treatment`: `plain` / `tile`). The drafter writes intents; a resolver
ranks the set's tags and categories (index generated with the base, like `lucide-icons.txt`); the validator
suggests `closest_icon`. Phosphor added to the pinned base (`make frontend-base`, exact pin, offline). Rules from
the research: one set per site, stroke follows text weight, icon 1–1.25× the font size, no icon on every heading.
Custom component prompts (17.3) get the same set and rules.

**20.6 Motion.** `theme.motion` (`feel`: `none` / `click` / `slide` / `flow` / `drop` / `bounce` / `float` / `cut`;
`signature`: `none` / `countUp` / `headlineRise` / `imageUnmask` / `indicator`). The three baseline motions and
reveals by content in the library, spring easings as `linear()`, a small client observer for reveal-once,
scroll-driven CSS only as an enhancement. Checklist additions: content visible without JS or animation, reduced
motion = final state, motion never delays a primary action, transform and opacity only. `design-check.mjs` runs a
reduced-motion pass (layout screenshots) and a motion pass that fails when an element is still hidden after the
reveals. Custom component prompts get the rules and the check.

**20.7 Design panel: rendered previews, squint view, concept-driven photos.** The review renders each direction's
home page with the renderer (no engine call) and shows the three side by side, with a greyscale toggle, the concept
line, tone, "gives up", and "Use this direction". Drafted photos (19.3) take their style from the chosen
direction's concept instead of `PHOTO_STYLES_BY_PRESET`; switching direction does not regenerate photos
automatically (it offers to).

**20.8 New section types.** Seven content sections with 2–3 forms each: `Steps` (how it works), `Timeline`,
`Team`, `PriceList` (menus and price lists), `Location` (address, opening hours, map link), `Comparison`,
`Statement` (a manifesto or one real quote). Theme tokens only, in the fixture and the checklist.

**20.9 Content-led pages.** The drafting prompt builds sections from what the requirement gives, using the whole
catalogue; no section without real content (FAQ only with real questions or policies; testimonials, stats, pricing
only with real ones; otherwise an assumption, not samples). Each direction card composes its own home page from the
drafted sections (`home`), keeping the required ones; left-out sections stay in the draft's pool so switching
restores them. `PATTERN_SECTIONS` no longer orders pages. Stock phrases are avoided, flagged (`FE_DESIGN_RULE`) and
repaired once. The report adds section frequency, home-composition similarity and repeated copy.

## How to implement (read first)

Work in this order and **stop at each checkpoint** for review:

1. **Phase A:** 20.1. **Checkpoint A** (baseline numbers recorded).
2. **Phase B:** 20.2 → 20.3 → 20.8. **Checkpoint B** (fixture screenshots of every hero layout, section form and
   new section type).
3. **Phase C:** 20.4 → 20.9 (one prompt version for both when done together). **Checkpoint C** (report run:
   direction targets met with the fake engine; content-led rules shown on fixture drafts).
4. **Phase D:** 20.5 → 20.6. **Checkpoint D.**
5. **Phase E:** 20.7. **Checkpoint E**, then the final check.

Rules (from the repository's `CLAUDE.md`; they apply to every story):

- Branch `feat/epic20-design-diversity` from `main`. **Do not commit**; the user commits after review.
- Never run paid engines or paid APIs unless a story says so **and** the user has said yes. Use the fake engine and
  the fake image generator everywhere else.
- Every new fake, stub or test-only switch goes into `docs/development/test-doubles.md` and is marked where it is
  defined.
- Prompts are versioned files; **never edit a released version** (latest today: `draft_frontend_spec@v7`).
- FrontendSpec changes are **additive** (new optional fields and enum values); existing specs and examples stay
  valid. Regenerate the JSON Schema snapshots (`UPDATE_SNAPSHOTS=1 make test`) and review the diff; the schema
  digests (18.9) include the new fields.
- Overlay files follow `nextjs-skills`; keep `templates/nextjs_overlay/DESIGN_CHECKLIST.md` true and measure with
  `scripts/design-check.mjs`. Base changes (Phosphor, display fonts) only through `make frontend-base`; rebuild
  `make runner-node` before `make up`.
- `agent-ui/src/features/specs/lib/design-direction.ts` mirrors `design_direction.py`: keep both in step.
- After each story: `make lint`, `make test`; `BGA_SANDBOX_TESTS=1 make test` when it touches the overlay or base;
  `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint` when the UI changes; `make up` with the fake engine for the
  flows the story names. Tick acceptance criteria and add a dated **Status** note.

## Epic acceptance

- The diversity report meets every target in "Expected output" with the fake engine, compared with the baseline
  from 20.1 in this epic's Status note.
- `make up`, fake engine: a spa requirement drafted twice with different seeds gives six directions with at least
  four distinct hero layouts and three hue families; switching between them in the Design panel rewrites the theme,
  hero layout, section forms, icons and motion, and keeps pages, copy and photos.
- A static generation from each of the three directions completes with **0 engine calls**, passes the design check
  (both passes, 390 / 768 / 1440 × light / dark), and loads its fonts and icons offline.
- Existing examples (`examples/frontend-specs/*.json`) validate and render unchanged.
- Switching directions on a draft changes the home page's sections and order (not only their look) and restores
  them when switching back; a fixture draft whose requirement has no questions or testimonials has no Faq or
  Testimonials section.

## Final check (after Checkpoint E, needs the user's yes)

One real-engine draft each for three golden requirements (e.g. the spa, `northwind-studio.md`, and the
clinic / pharmacy pair), run through the diversity report and generated as static sites. Record in this epic's
Status note: the report against the baseline (including the content-led measures of 20.9, which only a real engine
can show), draft time and cost added, and screenshots of the three directions per requirement.

## Follow-ups for Epic 16 (revise it after this epic)

- The theme editor (16.2) edits the new tokens, colour roles, icon style and motion; it edits tokens, not the tone.
- "Try another direction" becomes a spec-edit revision (new seed, no engine call for the layout; photos optional).
- Hero layout and section form changes are spec edits, not engine feedback.
- Feedback revisions (16.3) on custom components keep the direction's icon set and motion rules.

## Open questions (answered by the user, 2026-11-02: all defaults agreed)

| # | Question | Decision |
|---|---|---|
| Q22 | Three cards from **one** engine call (verbalized-sampling style), or **three parallel** calls given only the fact pack (more independent, ~3× the draft tokens)? | One call; the report shows whether directions are distinct enough, and 20.4 switches to parallel calls if not |
| Q23 | Add Phosphor to the pinned base (a second icon package), or only vary Lucide's stroke width and treatment? | Add Phosphor: its weights give the thin / filled / duotone looks Lucide cannot |
| Q24 | Keep the `vertical` hero layout (rotated display label), or stop at seven? | Keep it, display label only, never body text |
| Q25 | One click (19.10): apply the first direction, or the one the engine ranks best for the requirement? | The engine's best fit first; the other two as alternatives |
