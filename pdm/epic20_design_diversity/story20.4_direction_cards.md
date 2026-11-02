# Story 20.4 — Direction cards and the difference test

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-24 · **Depends on:** 20.2, 20.3, 12.6

## User story

As a user who describes a site in plain language, I want the draft to come with three directions that each fit my
site and clearly differ from each other (first screen, type, colour, imagery), each explained in one line, so that I
can pick a look instead of getting the default look of my category.

## Context

- Today: `orchestrator/design_direction.py` ranks UI UX Pro Max product types (BM25) and builds three directions from
  CSV rows (`directions()`); `drafting.apply_design` applies the one the engine names in `notes.json`
  (`design.productType`); `brief_markdown` writes `.bga/design.md`; `design_notes` adds anti-patterns to the
  assumptions. The UI mirrors `apply_direction` in `agent-ui/src/features/specs/lib/design-direction.ts`
  (`applyDirection`, `applyDirectionToText`, `isCurrentDirection`) and shows cards in
  `features/specs/components/DesignPanel.tsx`.
- Prompt: `prompts/draft_frontend_spec/v7.md` (the design part tells the engine to pick a brief and not to choose
  colours, fonts or the hero layout).
- Draft record: `spec_drafts.design` = `{selected, directions}`; `theme.direction` (`ThemeDirection`: `productType`,
  `pattern`, `palette`, `fontPairing`, `source`).
- One click (19.10) applies the selected direction and continues to generation.
- New in this epic: 8 hero layouts and section forms (20.2), tone tokens and display fonts (20.3).
- Decisions (epic): D1–D3, D5, D9, D10; Q22 one engine call; Q25 the engine's best fit first.

## Steps

1. **Direction card schema** (`orchestrator/design_cards.py`, Pydantic, camelCase JSON):
   `{name, concept, engine: "material" | "scene" | "character" | "tradition" | "medium" | "convention", evidence,
   tone: {energy, finish, density, weight, seriousness} (1–5), heroLayout, sectionForms: {Features?, Testimonials?,
   Stats?}, rhythm, fonts: {heading, body}, colors: {primary, background, foreground?, muted?, source},
   keyVisual: "photo" | "illustration" | "type" | "product" | "pattern", icons?, motion?, signature?, givesUp,
   fit}` (`icons` / `motion` / `signature` are filled by 20.5 / 20.6; until then ignored). `fit` is the engine's
   1–3 ranking of how well each card fits the requirement.
2. **Fact pack** (`.bga/design.md`, replaces the briefs): product facts from the requirement (who, what, main object
   and action, setting), brand values if named, **the category default** from the matched UI UX Pro Max row
   (palette, font pairing, landing pattern: "the look to move away from"), its anti-patterns, the hero layouts and
   section forms available, the bundled fonts by category, and the rules: concept from the product (not adjectives),
   colour from the brand or content (not from the concept's material), each direction its own hue family (never
   "one light, one dark, one warm"), at most one `split` hero, at least one direction off the category's usual home
   order.
3. **Prompt `draft_frontend_spec/v8.md`** (copy of v7): the engine writes the spec as before plus three cards in
   `notes.json` (`design.cards`), produced together and deliberately far apart (verbalized-sampling style: three
   candidates with their fit, not one). Brand colours and fonts named in the requirement go into every card.
   Switch `drafting.py` to v8.
4. **Validate and fill** (`design_cards.py`, no LLM):
   - card checks: fonts bundled (else `closest_font`), hero layout and forms known, colours parse;
   - theme from the card: `colors` (derived tokens and the light / dark pair through `frontend_theme`), fonts,
     tokens from `tone_tokens(tone)` (20.3), `style` preset nearest to the tone (for the parts presets still drive);
   - contrast: `contrast_failures` on light and dark; on failure, adjust lightness of `primary` / `foreground` within
     the hue (keeps the hue family), else take the UI UX Pro Max row's palette (the floor, D5) and note it.
5. **Difference test** (`difference(cards) -> list[problem]`): any two cards share at most one of hero layout, heading
   font, hue family (30° buckets, or both neutral), key visual; at most one `split`; at least one home order off the
   category default. On a problem, ask the engine again **for the failing card only** (a small repair call with the
   other two cards and the problem; at most 2 rounds); after that, code fixes it (next free hero layout, next font in
   the same category, a hue rotation of ≥ 60° checked for contrast) and adds a note.
6. **Apply.** `apply_direction` takes a filled card: theme, `theme.direction` (extended, additive: `concept`,
   `engine`, `tone`, `seed`, `givesUp`, `keyVisual`, `source: "card"` or `"ui-ux-pro-max@<sha>"` for the floor),
   home page order, hero layout, section forms, rhythm. Pages and copy are kept. The selected card is the one with
   the best `fit` (Q25); `spec_drafts.design` keeps the three filled cards. The UI mirror applies them with the same
   rules (shared JSON fixtures of card → spec tested on both sides).
7. **Seeds and the fake engine.** The draft stores a seed (random at creation, in `spec_drafts.design.seed`); the
   seed goes into the prompt context ("variation <seed>") and into the fake. The fake engine
   (`engines/fake_engine.py`) writes three cards drawn from a curated library (`agent-api/design_data/concepts.json`,
   ~40 concepts with tone, layout, fonts, colours and key visual) with a seeded RNG, filtered by a keyword match on
   the requirement, so `make test` and fake runs show varied directions. Listed in
   `docs/development/test-doubles.md`.
8. **Notes.** The assumptions show the chosen card's concept, "gives up", and any fix made by code (contrast, floor,
   difference). `design_notes` keeps the UI UX Pro Max anti-patterns.
9. **Report.** Run 20.1's report; the directions-within-a-draft, same-brief, paired-domain and trope targets are met
   with the fake engine.
10. **Dynamic apps (epic D12).** Dynamic drafts must look as good as static ones; their data pages keep the
    structure the backend contract gives them (CRUD), so this step checks their look, not their layout:
    - golden set: add two dynamic requirements to `examples/requirements/diversity/` (e.g. a clinic booking app and
      a small shop with orders), listed in `manifest.json` under `dynamic`; the report drafts them in dynamic mode
      and applies the difference test to their directions like the static ones;
    - `--screenshots` builds each direction of a dynamic draft on mock data (`MOCK_TEST_API`, no backend) and runs
      the design check on every page without route parameters plus one record page per resource (`site_check.py`
      gains what dynamic builds need, if anything);
    - data sections (DataTable, List, DetailView, Form, ActionBar, CardGrid from the API) are checked against the
      20.3 tokens (`surface`, `heading` on page titles, radius, density, `colorArea`) and fixed where they ignore
      them; `make design-check-fixture --spec` runs `shop-dynamic.json` and `project-tracker-dynamic.json` on mock
      data in the six tone combinations;
    - rules that only fit marketing pages (e.g. "CTA above the fold") are skipped on data pages by route, not
      loosened for everyone.
11. Tests: card schema; fill and contrast adjust (a failing palette is fixed or floored); difference test cases and
    the repair path (fake repair call); seed stability (same seed → same cards); fake library sampling; v8 prompt
    snapshot; `apply_direction` on every example spec; UI mirror on the shared fixtures; `test_drafting.py` end to
    end with the fake engine (three distinct cards, best fit selected, notes); a one-click (19.10) draft uses the
    selected card.

## Acceptance criteria

- [ ] Drafts from a requirement (static and dynamic) carry three filled direction cards; the theme, home order, hero
      layout, section forms and rhythm come from the selected card, the one with the best fit.
- [ ] Every card passes contrast in light and dark; failures are fixed within the hue or fall back to the UI UX Pro
      Max palette, with a note.
- [ ] Every draft passes the difference test (after at most 2 repair rounds and the code fallback).
- [ ] The same draft and seed give the same cards; a new seed gives new ones.
- [ ] The fake engine draws varied cards from the concept library; the test-doubles doc lists it.
- [ ] Python and UI apply a card identically (shared fixtures).
- [ ] The 20.1 report meets the direction targets with the fake engine; numbers in the Status note.
- [ ] Dynamic: the golden set has two dynamic requirements; their drafts pass the difference test, and every page of
      each direction (data pages on mock data) passes the design check; the dynamic example specs pass it in the six
      tone combinations.
- [ ] Draft time with a real engine is measured only on the epic's final check (needs the user's yes).

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `cd agent-ui && pnpm exec tsc --noEmit && pnpm
lint`, `make design-diversity ARGS=--screenshots`, `make up` with the fake engine: a spa requirement drafted twice
shows six directions with at least four hero layouts, and one click generates the selected one.

## Status
