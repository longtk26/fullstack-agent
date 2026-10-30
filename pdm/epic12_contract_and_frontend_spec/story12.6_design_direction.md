# Story 12.6 — Design direction for drafted sites

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-24, FR-22 · **Depends on:** 12.4, 17.7
**Planned:** right after 12.4 (agreed 2026-10-30). Research: [docs/research/design-skills.md](../../docs/research/design-skills.md).

## User story

As a user who describes a site in plain language, I want the draft to come with a design that suits the kind of site
I described (colours, fonts, page structure), and a few alternatives I can switch between in the review, so the first
version already looks designed instead of generic.

## Why

12.4 lets the drafter pick a theme preset and colours from brand words. With no brand words, every draft gets the
same `minimal` look, and hex values that the model invents are not checked for contrast. The renderer (Epic 17) now
turns a good spec into a good site with no engine call, so the theme and section choices in the spec decide how good
the site looks.

## Acceptance criteria

- [x] **Design data, vendored:** the UI UX Pro Max CSVs we use (`products`, `ui-reasoning`, `colors`, `typography`,
      `landing`, `styles`) are copied into the agent at a pinned commit, with their MIT licence and a
      `SOURCE.json` (repo, commit, date). `make design-data` refreshes them. Their scripts are not copied or run.
- [x] **Match:** a deterministic ranker (BM25 over product keywords and names, our own code) turns the requirement
      into the top 3 product types. The drafting engine gets those 3 design briefs (pattern, palette, font pairing,
      anti-patterns) in its prompt and picks one, or keeps the top match. Brand words in the requirement win over the
      data (12.4).
- [x] **Fill the theme from the data, not from the model:** the chosen row fills `theme.colors` (primary, secondary,
      accent, background, foreground, muted, destructive) and `theme.typography` (heading / body pairing, only
      pairings inside the 17.7 font set). `theme.style`, `radius` and `density` come from a mapping table from the
      data's styles to our 5 presets (e.g. Minimalism & Swiss → `minimal`/`sm`; Soft UI → `playful`/`lg`; data-dense
      → `dashboard`/`compact`). Effects our renderer does not draw (glass, neumorphism, 3D) are not copied.
- [x] **Page structure:** the landing pattern's section order becomes the home page's default sections from our
      catalogue (e.g. *Hero-Centric + Social Proof* → Hero, Features, Testimonials, CallToAction, ContactInfo), with
      17.7 variants (e.g. Hero `split` for a product, `banner` for a restaurant). Every requirement feature still maps
      to a page or section (12.4); the pattern only fills order and gaps.
- [x] **Recorded in the spec:** optional `theme.direction` {`productType`, `pattern`, `palette`, `fontPairing`,
      `source`: `ui-ux-pro-max@<sha>`}. Additive, still FrontendSpec 1.0; the renderer ignores it.
- [x] **Alternatives:** the draft result carries 2 alternative directions (theme + section order). The review (9.7b)
      shows them as swatch cards; switching one replaces the theme and the home page's section order with no engine
      call. Edited sections and content are kept.
- [x] **Design notes:** the chosen row's anti-patterns and key effects are listed with the assumptions (e.g. "avoid:
      neon colours, harsh animations"), so the user sees why the draft looks the way it does.
- [x] **Checks:** the filled theme passes the contrast checks of `frontend_theme.py` in light and dark; a direction
      whose derived tokens fail AA is skipped for the next match. Unit tests: a spa, a restaurant, a SaaS, a shop and a
      portfolio requirement each get a stable product type, palette and section order.
- [x] Static and dynamic modes only. Backend-only drafts skip this step.
- [x] With the fake engine, a catalogue-only static draft still renders with no engine call.

## Technical notes

- Ranking is ours (a small BM25 over the CSV rows, about 100 lines), so it is testable and needs no extra
  dependency. The UI UX Pro Max repo moves fast: pin, refresh on purpose, re-run the ranking tests after a refresh.
- Taste Skill is not used as a step (random art direction, browser critique loop, network photo fetch: see the
  research note). Its page rules feed the 17.7 checklist and the drafter's copy rules (12.4).
- Epic 16 can reuse the alternatives later ("try another direction" as a spec-edit revision).

**Status:** done (2026-10-30), on `feat/story12.6-design-direction` (stacked on 17.7).

- Fix (2026-10-30, Epic 15 branch): brand colours with a background now bring their own text and surface colours.
  The data's `foreground` / `secondary` / `muted` were made for its own background (a requirement naming near-black,
  off-white and orange got dark-pink text); now text is near-black or white for the brand's background and the
  surfaces are the brand's `secondary` (or a step off its background), and a dark brand background sets the dark
  scheme. The engine may name `secondary` and `muted` too (`draft_frontend_spec@v3`).

- **Data:** `agent-api/design_data/ui-ux-pro-max/` holds the six CSVs, the MIT `LICENSE` and `SOURCE.json` (commit
  `28b3b8dee8c9…`, the one the research note read). `make design-data [COMMIT=<sha>]` (`scripts/design-data.sh`)
  refreshes them; only data is fetched.
- **Ranking** (`orchestrator/design_direction.py`, no LLM): BM25 over product type (×3) and keywords (×2) with a light
  suffix stripper, on the requirement's **lead** (title + first plain paragraph; `**Key:** value` lines skipped),
  falling back to the full text. Page copy and field lists matched unrelated short keyword lists (Northwind's
  full text ranked "White Noise & Ambient Sound" first), so only the lead decides.
- **Directions:** product row → palette (`colors.csv`: primary, accent, background, foreground, muted,
  destructive; `secondary` = the data's muted, see deviations), a font pairing ranked from `typography.csv` among
  pairings inside the 17.7 set with a text face for the body, `style` / `radius` / `density` from our table of the
  data's styles (effects are not copied; a serif heading on a minimal style → `editorial`), and the home order +
  hero variant from our table of landing-pattern parts (`PATTERN_SECTIONS`). Dark palettes set `colorScheme: dark`,
  otherwise the spec's light / dark choice is kept. Every direction passes the contrast pairs (text on background,
  card, primary, secondary at 4.5; muted text at 3.0) in light and dark; 11 of 192 rows fail and are skipped.
- **Alternatives:** other product types scoring ≥ 50 % of the best on ≥ 2 terms (shop → E-commerce Luxury,
  Marketplace), otherwise variations of the best (its secondary styles in turn, the next font pairing, another hero
  layout), so a spa gets three spa looks rather than "Book & Reading Tracker".
- **Drafting:** static / dynamic drafts from a requirement write `.bga/design.md` (three briefs with the landing
  rows' section order and CTA placement) and use prompt `draft_frontend_spec@v2`. The engine names a brief in
  `notes.json` (`design.productType`, optional `brandColors` / `brandFonts`); the runner then fills the theme
  (+ `theme.direction`), orders the home page and sets the hero variant (`apply_direction`), before validation.
  Brand values are merged into all three directions. The draft keeps `design = {selected, directions}` (new JSONB
  column `spec_drafts.design`, migration `f2b8c4d6e1a3`); the direction, anti-patterns and key effects are added to
  the assumptions after the engine's notes. Backend drafts and imported sites get none.
- **Review (9.7b Design panel):** in the side panel of `/generations/new`, for the draft the editor was filled
  from: one card per direction (swatches, palette, fonts and pairing, preset / radius / hero, home order, avoid
  list, "draft's pick" / "in the editor"). "Use this direction" rewrites the editor's FrontendSpec
  (`lib/design-direction.ts`, same rules as the Python): theme, home order, hero variant; pages and content stay.
- **Verification:** `make test` (new `tests/test_design_direction.py`: vendored data and pin; spa, restaurant,
  SaaS, shop and portfolio each get a stable product type, primary colour, home order and hero; every direction
  passes contrast and uses bundled fonts; a failing row is skipped; alternatives; lead; apply and reorder; brand;
  notes. `test_drafting.py`: v2 prompt, design stored and applied, the engine's pick and brand colours, backend
  drafts without design, a drafted static site still plans `rendering: "renderer"`). `make up` with the fake engine:
  a spa draft through the API (Beauty/Spa/Wellness Service, pink palette, Playfair Display / Inter, banner hero,
  design notes), the Design panel in the browser (Playwright: switching to the second direction rewrote theme and
  hero, kept pages and copy, no validation errors), and a static generation from the draft: COMPLETED in 23 s with
  0 engine calls. UI: `tsc --noEmit` and `eslint` clean.
- **Deviations:**
  - The data's `Secondary` brand colour is not used: our `secondary` token is shadcn's neutral surface and the
    17.7 checklist allows one accent, so `secondary` = the data's muted.
  - Landing patterns: products name composite patterns ("Feature-Rich Showcase + Social Proof") that do not match
    `landing.csv` rows one to one, so the home order comes from our table of pattern parts; matching `landing.csv`
    rows (name or alias) only add their section order and CTA placement to the brief.
  - The data has no "design studio" keywords: Northwind's requirement ranks "Photography Studio", not "Creative
    Agency".
  - The home order lists the pattern's sections; the draft only reorders the sections the engine wrote (it never
    adds sections without content), so a switch can leave a pattern section out.
