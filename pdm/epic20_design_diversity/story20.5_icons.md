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

- [ ] Features, Stats, ContactInfo and Pricing items can show an icon, styled by `theme.icons`.
- [ ] Phosphor is in the pinned base; icons install and render offline; only used icons are bundled.
- [ ] Intents resolve to real icons through the tag index; drafts have 0 `FE_UNKNOWN_ICON` warnings.
- [ ] Each direction card carries an icon style derived from its tone; `none` is used and shows numbers instead.
- [ ] Custom components use the site's set and weight.
- [ ] The checklist covers icons; the design check passes.

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `make frontend-base` + `make runner-node`,
`BGA_SANDBOX_TESTS=1 make test`, `node scripts/design-check.mjs`, `make up` with the fake engine: a drafted site shows
icons in its Features in the selected direction's style; switching to a direction with `none` removes them.

## Status
