# Story 23.7 — Style recipes and three looks

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-33 · **Depends on:** 23.6

## User story

As a user drafting an app, I want three looks to choose from (glass, soft, brutalist, …) that suit my product and
stay readable, so that my app has its own character without breaking its screens.

## Context

- `app_theme` (`drafting/app.py`) keeps colours, fonts, radius and density only; `STYLE_PRESETS`
  (`design_direction.py`) flattens 88 UI UX Pro Max styles to five presets; `theme.py` has `SURFACES`.
- The style survey the user shared lists 32 styles; most fit apps as tokens and CSS (Tier 1) or kit variants
  (Tier 2). Illustrations, 3D and parallax (Tier 3) are out of scope.

## Steps

1. **Recipes** (`frontend/app/recipes.py` + `globals.css` layers in the app overlay). A recipe sets surface tokens
   (card, sidebar, header, dialog: background, border, shadow, blur), backdrop (plain, soft gradient, mesh, grain),
   radius scale, border weight, shadow style, heading treatment (weight, case, tracking), icon style (line, filled,
   duotone), motion preset (Epic 20's presets: hover, press, entrance), and the light and dark values. Twelve recipes
   to start:

   | Recipe | From the survey | Tier | Guard |
   |---|---|---|---|
   | `minimal` | Minimalism, Flat | 1 | — |
   | `swiss` | Swiss / International | 1 | — |
   | `material` | Material, raised surfaces | 1 | — |
   | `enterprise` | Corporate, data-dense | 1 | — |
   | `soft` | Neumorphism (soft UI) | 1 | adds a 1 px border and a visible focus ring (soft shadows alone fail contrast) |
   | `clay` | Claymorphism | 1 | — |
   | `glass` | Glassmorphism, Liquid Glass | 2 | solid surfaces under `prefers-reduced-transparency` and where the backdrop is busy; contrast checked over the worst backdrop pixel |
   | `aurora` | Aurora, gradient mesh | 2 | gradient on the backdrop only, never behind text |
   | `brutalist` | Neo-Brutalism | 2 | — |
   | `neon` | Cyberpunk / neon, dark first | 2 | not for health, finance, children's products |
   | `playful` | Y2K, Frutiger Aero | 2 | not for enterprise, legal, health |
   | `editorial` | Editorial / magazine | 1 | — |

   Tier 2 recipes need kit hooks: a backdrop layer in `AppShell`, an offset-shadow variant for buttons and cards,
   translucent surfaces with `backdrop-filter`.
2. **Theme for apps.** `app_theme` carries the recipe (`theme.recipe`) and the tokens it sets; Epic 22's D3 limit is
   lifted for apps only. Colours and fonts still come from the direction; a recipe may adjust them (e.g. `neon`
   forces dark first).
3. **Three looks.** From the brief's `looks` (23.6) code builds three themes. Each passes the AA contrast check on
   its real composite (light and dark), the recipe's guard against the product (`styles.csv` "Do Not Use For"), and a
   **difference test**: any two looks differ in recipe and in at least one of hue family or heading font. A failing
   look is replaced by code from the allowed recipes (no second model call). The first look is applied; one click
   (19.10) still works.
4. **Review.** The draft review shows the three looks as cards (name, swatches, fonts, a small rendered sample of a
   card and a button in the recipe); picking one changes the theme only.
5. **Checks.** `design-check-app` runs every recipe on one fixture app at 375 / 1440 px, light / dark; it checks
   contrast on rendered pixels, focus visibility, reduced motion and reduced transparency.
6. Tests: recipe tokens, guards, the difference test, look replacement, theme for apps vs static (static unchanged).

## Acceptance criteria

- [ ] Twelve recipes render on the kit in light and dark with no design-check failure.
- [ ] Every draft has three looks that pass contrast, guards and the difference test; replacements are noted.
- [x] Picking a look in the review changes only the theme; bindings and screens are byte for byte the same.
- [x] Reduced motion and reduced transparency are honoured in every recipe.
- [ ] The report's similarity drops below the 23.1 baseline toward the epic's target.
- [x] Static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make design-check-app ARGS=--all-recipes`,
`make app-design-report`.

## Status

**Implemented (2026-11-06), on the fake engine and mocks.**
- **Twelve recipes** in `frontend/app/recipes.css` (one block each over the kit's `data-slot` components and
  `data-bga-*` hooks: surfaces, backdrop, borders, shadows, radius, headings; reduced motion and reduced transparency
  honoured); code appends only the app's recipe to its `globals.css` (`recipe_css`, `:root` after the theme's tokens,
  so nothing flashes and static sites are untouched).
- **Three looks** (`recipes.complete_looks`, run by `draft_app` and the report): the requirement's style words first
  (`style_words`), the brief's, then UI UX Pro Max's styles for the ranked products (`recommended_looks`), guards
  (no neon or toy look for health, finance, legal products unless asked) and a range (three quiet looks get a bolder
  third: Story 23.0's finding). `design.recipe` is the user's pick (the review's App design card); `first_recipe`.
- Verified: `tests/test_app_recipes.py`; the golden apps build with their looks, 0 failures.

Deviations: contrast is not yet measured on the rendered composite per recipe, and the twelve-recipe sweep in light
and dark waits for the final check (`make design-check-app` per recipe); looks change surfaces, not typefaces (fonts
stay the direction's).
