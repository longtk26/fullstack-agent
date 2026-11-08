# Adding design plugins

How to add a new layout or look to the dynamic app kit, one at a time, so generated apps keep getting more varied.
Backlog: [Epic 30](../../pdm/epic30_design_plugins/epic30_design_plugins.md). Background: [Epic 23](../../pdm/epic23_app_design/epic23_app_design.md)
(the design space) and [design-checks.md](design-checks.md) (the measuring tools).

> **Status (2026-11-08):** the registry, the starter templates and the `design-plugin-*` commands arrive with
> Stories 30.2 and 30.3. Until then, follow [Before the registry](#before-the-registry): the same rules, more files to
> touch.

## What a design plugin is

A design plugin is **one prepared option** the drafter can choose for an app: a shell, a list view, a record layout,
a home, a filter style, a card anatomy, a style recipe or a font pairing. It changes **how** the same screens are
presented, never **what** they do: bindings, operations, forms and permissions stay exactly as code planned them.

It is not a **feature plugin** (`agent-api/templates/plugins/`, Epic 10: auth, storage, payments, …). Feature
plugins add backend behaviour and its UI; design plugins only present.

The rule behind all of it (Epic 23's D1): **the model chooses from prepared options, code checks them, the kit builds
them.** No model-written layout or CSS ever reaches an app.

```
 requirement ─▶ draft_app (model picks plugin names per axis)
                   │
                   ▼
 complete_design (code): is it ready? are its `needs` met by the contract? else its `fallback` + a note
                   │
                   ▼
 app.json design ─▶ kit: design-registry.ts (generated) ─▶ the plugin's component / CSS
```

## Kinds

| Kind | What it decides | Props contract (kit) | Examples today |
|---|---|---|---|
| `shell` | the app's frame and navigation | `TShellProps` (nav, user menu, children) | `sidebar`, `topbar`, `topbar-tabs`, `rail` |
| `list-view` | how a list of records is shown | `TViewProps` (section, entity, records, design) | `table`, `cards`, `media-grid`, `feed`, `board`, `calendar` |
| `detail-view` | how one record's page is arranged | `TDetailProps` (section, entity, record, design) | `record`, `media`, `profile` |
| `home` | the first screen after sign-in | `THomeProps` | `dashboard`, `feed`, `catalogue`, `agenda`, `bento` |
| `filters` | how list filters are offered | `TFiltersProps` | `toolbar`, `chips`, `facets`, `search-first` |
| `card` | the anatomy of one record in grid views (30.4) | `TCardProps` (record, roles, size) | `stacked` (today's) |
| `recipe` | surfaces, borders, shadows, radius, headings, motion (CSS only) | none: CSS over `data-slot` | the 12 of Story 23.7 |
| `font-pairing` | heading / body / mono fonts and the type scale (30.6) | none: the theme writes it | |

Pick the smallest kind that does the job. A new card anatomy is a `card`, not a new `list-view`; a new shadow style
is a `recipe`, not a new card.

## The folder

```
agent-api/templates/design/<kind>/<name>/
  plugin.json        descriptor (below)
  <Name>.tsx         the component (not for recipe / font-pairing)
  <name>.css         recipe and card styles (optional for other kinds)
  fixture.json       the design values that select this plugin on the kind's fixture app
  preview.png        written by `make design-plugin-check`; shown in the review's Design panel
```

### `plugin.json`

```json
{
  "kind": "list-view",
  "name": "shelves",
  "status": "draft",
  "label": "Shelves",
  "choose": "Records with a picture, grouped by a category people browse: one horizontal row per group.",
  "archetypes": ["catalogue", "storefront", "learning"],
  "needs": { "mediaField": true, "groupField": true },
  "fallback": "media-grid",
  "exports": ["Shelves"],
  "marker": "shelves"
}
```

| Field | Rule |
|---|---|
| `name` | kebab-case, describes the pattern (`shelves`, `split-panel`), never a product or brand |
| `status` | `draft` until `make design-plugin-check` passes; only `ready` plugins are offered |
| `choose` | one or two sentences for the model: **when** this fits, in terms of the data and the people using it. It goes into the prompt as is, so keep it short and domain-neutral |
| `archetypes` | where it is a candidate; the prompt shows only candidates of the app's archetype |
| `needs` | what the contract must have (`imageField`, `mediaField`, `dateField`, `statusFlow`, `dateSort`, `groupField`, `enumOrReferenceFilter`, `minRecords`, …). Add a new key only with its check function in the registry |
| `fallback` | a `ready` plugin of the same kind used when `needs` are not met |
| `exports` | component names the folder exports (the generated `design-registry.ts` imports them) |
| `marker` | the `data-bga-*` value the component puts on its root, so the report can fingerprint it |
| `guards` | recipes: products it must never be used for (health, finance, children's products, …) |
| `family`, `prefers` | recipes: `quiet` / `soft` / `bold`; the card and density it looks best with (a tie-breaker) |

## Add a plugin, step by step

1. **Pick a gap.** Run `make app-design-report` and read its "similar pairs" and "unused" lists, or take the top
   entry of the plugin backlog (Story 30.8's Status). Write down in one sentence what it adds that no plugin has.
2. **Start it.** `make design-plugin-new KIND=<kind> NAME=<name>` copies the kind's starter.
3. **Write the descriptor**: `choose`, `archetypes`, `needs`, `fallback`. If you need a new `needs` key, add its check
   in the registry first, with a test.
4. **Build the component** against the kind's props contract:
   - shadcn components from the kit and theme tokens only (`bg-card`, `text-muted-foreground`, `--radius`, …); no
     hard-coded colours, fonts or sizes in px for text;
   - every state: loading (the kit's skeletons), empty, error, one record, many records, long text;
   - 375 px first, then wide screens; no horizontal page scroll (an intentional scroll strip is fine, with keyboard
     access);
   - keyboard and focus: every interactive element reachable, a visible focus ring, a logical order;
   - motion only through the kit's motion presets, off under `prefers-reduced-motion`;
   - the `marker` on the root element; the existing `data-bga-section` / `data-bga-action` markers kept (the tour and
     the evaluation use them).
5. **Fixture.** Set the design values that select the plugin in `fixture.json`; make sure the fixture app meets the
   `needs` (and add a second fixture that does not, to see the fallback).
6. **Check.** `make design-plugin-check NAME=<name>`: 375 / 1440 px, light / dark, in every ready recipe; contrast on
   the real composite; keyboard; reduced motion and transparency; all states. Fix until the table is all pass; look at
   the screenshots yourself as well.
7. **Promote.** Set `"status": "ready"`. `make test` runs the registry checks (fallback exists, exports exist, fixture
   builds).
8. **Measure.** `make app-design-report`: the fingerprint count should go up, or the plugin should show up where the
   gap was.
9. **Record it.** One line in the plugin backlog (what, why, the report's number before and after), then commit:
   `feat(design): <kind> <name>`.

A plugin a day is the right size. If it takes longer, it is probably two plugins, or it needs a new `needs` key or a
contract feature first; split that out.

## Never

- Copy a specific product's look, name, logo, icons or screens. Plugins are patterns many products share.
- Add CSS or layout the model writes, or a plugin whose output depends on the model's free text.
- Filter or hide records in a plugin; visibility is the backend's (Epic 23's D7).
- Change bindings, forms or actions from a plugin; it only arranges what the section already has.
- Remove or rename a `data-bga-*` marker the tour, the evaluation or the report reads.
- Mark a plugin `ready` without a clean `make design-plugin-check`.
- Add a font that is not bundled (`frontend_spec/fonts.py`; a new font is `make frontend-base` + `make runner-node`).
- Write a plugin around one sample app's domain; describe `choose` by the data's shape and who uses it.

## Before the registry

Until Story 30.2 lands, a new value of the design space is added by hand in these places (and the same gates apply,
through `make design-check-app` and `make app-design-report`):

| Kind | Files to change |
|---|---|
| any | the literal in `agent-api/src/modules/shared/domain/frontend_spec/app.py` (`Shell`, `ListView`, `DetailView`, `HomeView`, `FiltersStyle`, `Recipe`); the choice prose in the current `agent-api/prompts/draft_app/v<N>.md` (new prompt version); the type in the kit's `components/app/app.ts` (`TEntityDesign`, the app design type); `agent-api/scripts/app_design_proto/` if the harness should offer it; schema snapshots (`UPDATE_SNAPSHOTS=1`) |
| `shell` | `SHELLS` and `ARCHETYPES` in `agent-api/src/orchestrator/frontend/app/design.py`; `AppShell.tsx` |
| `list-view` | `VIEWS` and the `needs` checks in `complete_design` (`design.py`); `list_features` if it needs list features from the API; a component and the dispatch in `RecordsView` (`views.tsx`); `AppList.tsx` when it changes paging or controls |
| `detail-view` | `design.py`; `AppDetail.tsx` |
| `home` | `ARCHETYPES` / `home_entity` in `design.py`; `AppPage.tsx` (dashboard, bento) or `AppList.tsx` (feed, catalogue, agenda) |
| `filters` | `design.py`; `AppList.tsx` (`Controls`) |
| `recipe` | `RECIPES`, `FAMILIES`, `STYLE_RECIPES`, `STYLE_WORDS` and guards in `agent-api/src/orchestrator/frontend/app/recipes.py`; a `/* recipe: <name> */ … /* end */` block in `recipes.css` next to it |
| fonts | `agent-api/src/modules/shared/domain/frontend_spec/fonts.py`, then `make frontend-base` and `make runner-node` |

Tests to extend: `agent-api/tests/test_app_design.py` (choices and fallbacks), `test_app_recipes.py` (recipes),
`test_app_design_report.py` (report), plus the kit's `tsc` and lint. A change to shared frontend code must keep
`tests/test_static_golden.py` passing.
