# Story 20.9 — Content-led pages: sections from the requirement, not from a template

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-24 · **Depends on:** 20.4, 20.8

## User story

As a user, I want my site's pages and sections to come from what I described: a bakery gets its menu, hours and
story; a law firm its team and how a case works; no FAQ, testimonials or "Explore …" buttons unless I gave something
for them, so that the site feels made for me and not like the same template every time.

## Context

- Why every site has the same sections today:
  - `prompts/draft_frontend_spec/v7.md` tells the engine to "build the home page from [the brief's] sections, in its
    order"; the brief's sections come from `PATTERN_SECTIONS` in `orchestrator/design_direction.py` (fixed landing
    orders such as Hero → Features → Testimonials / Stats → Faq → CallToAction);
  - its copy rules say that when the requirement gives no testimonials, figures or prices "but a section needs
    them", the engine writes generic sample content, so template sections are kept and filled;
  - switching direction (12.6, 20.4) only reorders and restyles the sections the engine wrote;
  - the catalogue has about ten marketing sections (20.8 adds seven);
  - nothing checks repeated headings or CTA labels ("Explore Dishes", "Why choose us").
- The fake engine copies one example spec per keyword (`engines/fake_engine.py`, `DRAFT_FIXTURES`), so section
  variety can only be measured with a real engine. The rules here are tested with fixture drafts; the numbers come
  from the epic's final check.
- 20.4 introduces `draft_frontend_spec@v8` (direction cards). This story's prompt changes go into the same version
  if both are implemented in one go, otherwise into v9.

## Steps

1. **Content first in the prompt.** The drafting prompt (v8 / v9) replaces "build the home page from the brief's
   sections" with:
   - list what the requirement actually gives (offer, people, places, prices, hours, process, story, proof,
     questions, policies) and give each a section that shows it best, using the whole catalogue including 20.8's
     sections;
   - **a section only exists when its content does.** Testimonials, client logos, Stats and Pricing only with real
     content from the requirement; FAQ only when the requirement holds questions or policies a visitor needs
     (booking rules, delivery, payment), written from them; otherwise the question goes to `unresolved` and the
     section is left out. This replaces v7's "write clearly generic sample content" rule: a missing section is
     recorded as an assumption ("add testimonials when you have them"), not filled with samples;
   - no section "because landing pages have one"; the category's usual order (from the fact pack, 20.4) is the
     pattern to move away from, not a checklist;
   - the requirement's must-haves are marked (`notes.json`: `design.required: [sectionId]`).
2. **Each direction composes the home page.** The engine writes the home page's candidate sections once, all with
   real content (the **pool**). Each direction card (20.4) adds `home: [sectionId]`: an ordered subset of the pool
   that keeps every required section, plus the hero layout. Sections a direction leaves out are kept in
   `spec_drafts.design.pool`, so switching directions restores them; the applied spec holds only the chosen ones.
   Inner pages are written once and shared by all directions. The difference test (20.4) adds: any two directions
   differ in home composition (set or order of the first three sections).
3. **Copy against stock phrases.** Prompt rules: CTA labels say the requirement's main action with its object
   ("Book a table", "See this week's menu"); headings say something specific to the business. A list of stock
   phrases (`frontend_spec/copy_rules.py`: e.g. "Explore …", "Discover …", "Unlock …", "Elevate …", "Why choose us",
   "Welcome to …", "Our services", "Get started today", a lone "Learn more") is given to the engine as phrases to
   avoid, and the validator warns `FE_DESIGN_RULE` with the phrase and its path. Drafting runs one repair round for
   these warnings (the existing repair loop, prompt `repair_spec`), then keeps the rest as notes.
4. **Templates out of `design_direction.py`.** `PATTERN_SECTIONS` is no longer used to order pages; it stays only
   to describe the category default in the fact pack and for the 20.1 trope measure. `apply_direction` applies
   `home` from the card; the UI mirror does the same.
5. **Measures** (added to 20.1's report; real-engine numbers on the final check):
   - section frequency: share of drafts containing each section type, overall and per type of business;
   - home composition similarity between different requirements (Jaccard of section-type sets, and the first three
     in order);
   - repeated copy: headings and CTA labels that appear in more than one site of the golden set, and stock phrases
     per site.
   Targets (written into the epic's table): an optional section (Faq, Testimonials, Stats, Pricing, CallToAction)
   appears only when the requirement gives content for it; no single optional type in more than 40% of drafts across
   the golden set; mean home-composition Jaccard between different requirements ≤ 0.5; 0 stock phrases left after
   repair.
6. Tests (fixture drafts and the fake engine; no real engine): prompt snapshot; a requirement without questions gets
   no Faq (fixture notes + validation); `required` sections kept by every direction; pool and switching restore
   left-out sections (Python and UI on shared fixtures); difference test on home composition; stock-phrase warnings
   and the repair round; the measure functions.

## Acceptance criteria

- [ ] The drafting prompt builds sections from the requirement's content; no section without real content; missing
      proof and questions become assumptions or unresolved items, not sample content.
- [ ] Each direction has its own home composition from the pool, keeps the required sections, and switching
      directions restores left-out sections.
- [ ] `PATTERN_SECTIONS` no longer orders pages.
- [ ] Stock phrases are avoided by the prompt, flagged by the validator and repaired once.
- [ ] The report measures section frequency, home-composition similarity and repeated copy; the targets are in the
      epic and checked on the final check (real engine, needs the user's yes).

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `cd agent-ui && pnpm exec tsc --noEmit && pnpm
lint`, `make up` with the fake engine: switching directions on a draft changes the home page's sections and order and
restores them when switching back.

## Status
