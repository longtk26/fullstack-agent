# Story 30.2 — The design plugin registry

**Epic:** [30 — Design plugins](epic30_design_plugins.md) · **Requirements:** FR-44 · **Depends on:** 30.1

## User story

As the person adding a layout or a look, I want to add one folder and have the schema, the prompt, the checks and the
kit pick it up, so that a new option is a small, safe change.

## Context

- Today's values: `Archetype`, `Shell`, `ListView`, `DetailView`, `HomeView`, `FiltersStyle`, `Recipe`
  (`frontend_spec/app.py`); `ARCHETYPES`, `SHELLS`, `VIEWS`, the `needs` checks in `complete_design`
  (`frontend/app/design.py`); `RECIPES`, `FAMILIES`, `STYLE_RECIPES`, `STYLE_WORDS` (`frontend/app/recipes.py`) and
  the recipe blocks of `recipes.css`; the choice prose in `prompts/draft_app/v5.md`; `RecordsView` (`views.tsx`),
  `AppDetail.tsx`, `AppShell.tsx`, `AppPage.tsx` in the kit.
- Feature plugins already copy only what an app uses (`files.frontend_plugins`, `plugins_ts`).

## Steps

1. **Descriptor** (`plugin.json`, validated by a Pydantic model `DesignPluginDescriptor`):
   `kind`, `name`, `status` (`ready` / `draft`), `label`, `choose` (one or two sentences: when to choose it, shown to
   the model), `archetypes` (where it is a candidate), `needs` (typed: `imageField`, `dateField`, `statusFlow`,
   `dateSort`, `enumOrReferenceFilter`, `mediaField`, `groupField`, `minRecords`, …), `fallback` (a plugin of the same
   kind), `exports` (component names), `css` (recipe and card plugins), `guards` (recipes: products it must not be
   used for, from today's `neon` / `playful` rules), `family` (recipes), `marker` (its `data-bga-*` value).
2. **Loader** (`frontend/app/design_registry.py`): reads `templates/design/**/plugin.json` once, checks that every
   `fallback` exists and is `ready`, and exposes per kind the names, descriptors and `needs`.
3. **Generated from the registry:** the literals in `frontend_spec/app.py` (built from the ready names at import; the
   schema snapshot changes when a plugin is added); the answer schema's enums; the prompt's choice lists (a
   `{{DESIGN_CHOICES}}` block rendered from `choose`, new prompt version); `complete_design`'s checks (one function per
   `needs` key, shared); the kit's `src/components/app/design-registry.ts` (imports only the plugins the app uses, maps
   names to components; the kit's dispatchers read it).
4. **Move today's values in** (no visual change): 4 shells, 6 list views, 3 detail views, 5 homes, 4 filter styles,
   12 recipes become plugins; their components move from `views.tsx`, `AppDetail.tsx`, `AppShell.tsx` into their
   folders; `recipes.css` blocks into their recipe folders. Archetype defaults stay in `design.py`, naming plugins.
5. **Guard:** a registry test fails when a plugin's name appears in a hand-written list in `src/` or the kit.
6. Tests: the loader (missing fallback, unknown `needs`, draft plugins not offered); the generated literals and
   prompt block; every golden app's `app.json` and screenshots unchanged (`make design-check-app`, the report's
   fingerprints equal the baseline); static golden test unchanged.

## Acceptance criteria

- [ ] Every value of today's design space is a plugin folder; no hand-kept list of them remains.
- [ ] The golden apps render the same before and after (fingerprints equal, design check clean).
- [ ] An app's bundle contains only the plugins it uses.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (kit), `make test`, `make design-check-app`, `make app-design-report`.

## Status

Proposed 2026-11-08.
