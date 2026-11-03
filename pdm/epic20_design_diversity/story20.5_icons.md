# Story 20.5 — Icons

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-22 · **Depends on:** 20.4, 15.1

## User story

As a user, I want icons that mean what the text says and that suit my site's direction (thin and quiet, bold and
filled, or deliberately none), so that sections are easier to scan and the site does not look like every other
generated site.

## Context

- Today: the pinned base ships `lucide-react` 1.62; an asset may be `lucide:<Name>`, checked against
  `templates/nextjs_base/lucide-icons.txt` (written by `scripts/frontend-base.sh`) with `FE_UNKNOWN_ICON`
  (`frontend_spec/assets.py`, `validator.py`). **No library section draws an icon**: `FeatureItem` has no `icon`
  (17.1 left it for Epic 15).
- Lucide keeps per-icon metadata (`tags`, `categories`) in its repository; Phosphor (`@phosphor-icons/react`, MIT)
  has six weights (thin, light, regular, bold, fill, duotone) through a `weight` prop and an SSR entry for server
  components.
- Matching words to icon *file names* by embeddings is fragile (research note: "handshake" → `dash-circle`); rank
  over tags and categories instead. `design_direction.py` already has a small BM25 (`Bm25`) to reuse.
- Rules (oil-ui): one set per site; stroke follows text weight; icon 1–1.25× the font size, aligned on the visual
  centre; no icon on every heading; editorial directions may use numbers or characters instead.
- Decision Q23: add Phosphor.

## Steps

1. **Spec.** Optional `icon` on `FeatureItem`, `StatsItem`, ContactInfo items and Pricing plan features: a reference
   `lucide:<Name>` / `phosphor:<Name>`, or an **intent** `intent:<words>` (e.g. `intent:fast delivery`) that the
   drafter writes. `theme.icons` = `{set: "lucide" | "phosphor" | "none", weight: "thin" | "light" | "regular" |
   "bold" | "fill" | "duotone", treatment: "plain" | "tile"}` (optional; default `lucide` / `regular` / `plain`).
   `lucide` supports `thin` / `light` / `regular` / `bold` through `strokeWidth` (1 / 1.5 / 2 / 2.5); `fill` and
   `duotone` need Phosphor (validator suggests it).
2. **Base.** Add `@phosphor-icons/react` (exact pin) with `make frontend-base`; `frontend-base.sh` also writes
   `icon-index.json` next to `lucide-icons.txt`: for both sets, every icon name with its tags and categories (Lucide
   from its metadata at the pinned version; Phosphor from its package metadata). Not copied into projects.
3. **Resolver** (`frontend_spec/icons.py`): `resolve_icon(intent, set) -> name` ranks the set's index (name words ×2,
   tags, categories) with the shared BM25; `closest_icon(name, set)` for unknown names. Drafting resolves every
   `intent:` to a real reference before validation and notes unresolved ones (they render nothing). The validator
   warns on an unknown name with `Closest icon: …`.
4. **Library.** An `Icon` component in the renderer reads `theme.icons` and the reference: imports only the icons a
   site uses (the generated registry lists them, like fonts in `fonts.ts`), sizes 1–1.25× the text it sits with,
   stroke from the weight, `aria-hidden` (decorative; the text carries the meaning), `tile` = a small rounded square
   in the muted tone. Features (cards, list, ledger), Stats, ContactInfo and Pricing draw it when present. With
   `set: "none"` nothing is drawn and Features `list` / `ledger` show numbers.
5. **Direction.** The card (20.4) gets `icons` from the tone: refined and light → thin / light; heavy or playful →
   bold / fill / duotone; raw or editorial → often `none`. The fact pack and prompt version (`draft_frontend_spec`
   next version) ask for icon intents on items where an icon helps scanning, never on every heading. The fake
   engine fills intents from item titles.
6. **Custom components.** The `generate_custom_component` prompt (next version) gets the site's set, weight and the
   rules; isolated checks fail on an import from another icon package.
7. **Checklist.** `DESIGN_CHECKLIST.md`: icon rules and how the library keeps them.
8. Tests: resolver cases (e.g. "fast delivery" → a truck or zap icon, "secure payment" → a lock or shield; at least
   20 cases from the golden requirements); unknown name suggestion; spec typing; per-site icon imports; the fixture
   renders every set / weight / treatment; sandbox build offline; `design-check.mjs` with icons.

## Acceptance criteria

- [x] Features, Stats, ContactInfo and Pricing items can show an icon, styled by `theme.icons`.
- [x] Phosphor is in the pinned base; icons install and render offline; only used icons are bundled.
- [x] Intents resolve to real icons through the tag index; drafts have 0 `FE_UNKNOWN_ICON` warnings.
- [x] Each direction card carries an icon style derived from its tone; `none` is used and shows numbers instead.
- [x] Custom components use the site's set and weight.
- [x] The checklist covers icons; the design check passes.

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `make frontend-base` + `make runner-node`,
`BGA_SANDBOX_TESTS=1 make test`, `node scripts/design-check.mjs`, `make up` with the fake engine: a drafted site shows
icons in its Features in the selected direction's style; switching to a direction with `none` removes them.

## Status

**Done (2026-11-03)**, on `feat/epic20-design-diversity`, with 20.6 (prompt `draft_frontend_spec@v9`).

- **Spec:** `icon` on Features, Stats and Pricing items (`section_props.IconRef`: `lucide:<Name>`, `phosphor:<Name>`
  or `intent:<words>`); `theme.icons` = `{set, weight, treatment}` (`schema_v1.IconStyle`, optional; absent: Lucide,
  regular, plain). The validator warns `FE_UNKNOWN_ICON` (with `Closest icon: …`) for an icon the site's set cannot
  draw, and `FE_DESIGN_RULE` for Lucide with `fill` / `duotone`.
- **Base:** `@phosphor-icons/react` 2.1.10 (exact pin, lock-only add as for the fonts; `frontend-base.sh` installs it
  too); `scripts/icon-index.mjs` writes `templates/nextjs_base/icon-index.json` (1,908 Lucide icons from
  `lucide-static`'s tags, 1,512 Phosphor icons from `@phosphor-icons/core`'s tags and categories; not copied into
  projects). `overlay.json` regenerated, `make runner-node` rebuilt.
- **Resolver** (`frontend_spec/icons.py`): BM25 over each set (name words ×2, tags, categories; shared ranker moved
  to `src/libs/search`), the intent's last word weighted ×2, a curated map of ~150 business words to drawable objects
  (hours → clock, haircut → scissors, clients → users), whole-name and short-name preference. 26 golden-set intents
  are tested in both sets; all examples' fake intents resolve in both.
- **Per set at generation:** items keep their reference or intent; `frontend_renderer` resolves them to the site's
  set when `site.json` is written (a switch of direction re-resolves, nothing is rewritten in the spec) and
  `icons.ts` imports only the used icons, one module each (`lucide-react/icons/<file>`,
  `@phosphor-icons/react/dist/ssr/<Name>`), plus six library marks.
- **Library:** `sections/Icon.tsx` (decorative, 1.25 × the text, stroke widths 1 / 1.5 / 2 / 2.5 for Lucide, weight
  prop for Phosphor, `tile` treatment). Features (cards, list in place of the numeral, ledger), Stats (cards,
  figures, inline), Pricing (plan name); ContactInfo, Location, Pricing and Comparison draw their marks (mail, phone,
  map pin, clock, check, minus) in the site's set through `Icon glyph`. With `none` content icons and decorative
  marks are left out and lists show numbers.
- **Direction:** `design_tone.icon_style(tone)` (table in its docstring); a card may name `icons`; fill / duotone
  move to Phosphor with a note. Prompt v9 asks for `intent:<a concrete object>` on items where an icon helps
  scanning, never on headings. The fake writes intents from item titles (`with_icon_intents`).
- **Custom components:** `generate_custom_component@v5` (cache key bumped): icons only through `Icon`; the isolated
  checks reject `lucide-react` / `@phosphor-icons/react` imports.
- **Verification:** `make test` and `make lint` green; `tests/test_icons_and_motion.py`. `make design-check-fixture
  ARGS="--combos --motion"`: 6 combinations × 126 views (Phosphor duotone tiles, Lucide light, none, …), 0 failures
  (`.data/shots/phaseD-combos/`). Diversity report: `FE_UNKNOWN_ICON` 0 across 14 fake drafts.
- **Deviations:**
  - Icons are not resolved in the draft but when the site is generated, against the site's current set, so
    switching direction (another set) keeps every icon right.
  - ContactInfo has no items; its fixed marks follow the set instead of an `icon` field. Steps keep their numbers.
  - UI chrome (menu, theme toggle, error alert) stays Lucide, like the base's primitives.
  - The resolver adds a curated word → object map to the tag index: tags alone matched "email" to an inbox and
    "opening hours" to a folder.

