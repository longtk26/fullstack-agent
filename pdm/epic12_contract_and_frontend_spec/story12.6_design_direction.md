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

- [ ] **Design data, vendored:** the UI UX Pro Max CSVs we use (`products`, `ui-reasoning`, `colors`, `typography`,
      `landing`, `styles`) are copied into the agent at a pinned commit, with their MIT licence and a
      `SOURCE.json` (repo, commit, date). `make design-data` refreshes them. Their scripts are not copied or run.
- [ ] **Match:** a deterministic ranker (BM25 over product keywords and names, our own code) turns the requirement
      into the top 3 product types. The drafting engine gets those 3 design briefs (pattern, palette, font pairing,
      anti-patterns) in its prompt and picks one, or keeps the top match. Brand words in the requirement win over the
      data (12.4).
- [ ] **Fill the theme from the data, not from the model:** the chosen row fills `theme.colors` (primary, secondary,
      accent, background, foreground, muted, destructive) and `theme.typography` (heading / body pairing, only
      pairings inside the 17.7 font set). `theme.style`, `radius` and `density` come from a mapping table from the
      data's styles to our 5 presets (e.g. Minimalism & Swiss → `minimal`/`sm`; Soft UI → `playful`/`lg`; data-dense
      → `dashboard`/`compact`). Effects our renderer does not draw (glass, neumorphism, 3D) are not copied.
- [ ] **Page structure:** the landing pattern's section order becomes the home page's default sections from our
      catalogue (e.g. *Hero-Centric + Social Proof* → Hero, Features, Testimonials, CallToAction, ContactInfo), with
      17.7 variants (e.g. Hero `split` for a product, `banner` for a restaurant). Every requirement feature still maps
      to a page or section (12.4); the pattern only fills order and gaps.
- [ ] **Recorded in the spec:** optional `theme.direction` {`productType`, `pattern`, `palette`, `fontPairing`,
      `source`: `ui-ux-pro-max@<sha>`}. Additive, still FrontendSpec 1.0; the renderer ignores it.
- [ ] **Alternatives:** the draft result carries 2 alternative directions (theme + section order). The review (9.7b)
      shows them as swatch cards; switching one replaces the theme and the home page's section order with no engine
      call. Edited sections and content are kept.
- [ ] **Design notes:** the chosen row's anti-patterns and key effects are listed with the assumptions (e.g. "avoid:
      neon colours, harsh animations"), so the user sees why the draft looks the way it does.
- [ ] **Checks:** the filled theme passes the contrast checks of `frontend_theme.py` in light and dark; a direction
      whose derived tokens fail AA is skipped for the next match. Unit tests: a spa, a restaurant, a SaaS, a shop and a
      portfolio requirement each get a stable product type, palette and section order.
- [ ] Static and dynamic modes only. Backend-only drafts skip this step.
- [ ] With the fake engine, a catalogue-only static draft still renders with no engine call.

## Technical notes

- Ranking is ours (a small BM25 over the CSV rows, about 100 lines), so it is testable and needs no extra
  dependency. The UI UX Pro Max repo moves fast: pin, refresh on purpose, re-run the ranking tests after a refresh.
- Taste Skill is not used as a step (random art direction, browser critique loop, network photo fetch: see the
  research note). Its page rules feed the 17.7 checklist and the drafter's copy rules (12.4).
- Epic 16 can reuse the alternatives later ("try another direction" as a spec-edit revision).

**Status:** planned (2026-10-30).
