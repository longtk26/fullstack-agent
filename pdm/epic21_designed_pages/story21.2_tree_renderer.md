# Story 21.2 — Tree renderer

**Epic:** [21 — Designed pages](epic21_designed_pages.md) · **Depends on:** 17.2, 20.5, 20.6

## User story

As a user, I want a page the engine designed as an element tree to render through the same pipeline as section
pages (no engine call, theme tokens, icons, motion, light and dark), so that designed pages cost seconds and keep
the design system.

## Scope

- FrontendSpec: `pages[].tree` + `css`, `layout.chrome` / `footerTree` (`TreeNode`; a page has sections or a tree).
- `frontend_renderer.tree_site`: every node classified (`element`, `image`, `icon`, `link`, `primitive`,
  `section`, `data`), images → assets, icons → the site's set, `Link` targets → routes, library sections rendered
  through `SectionRenderer` (with `data` / `form` bindings), data components bound; page CSS scoped.
- Overlay `renderer/tree/`: `TreeRenderer.tsx` (a client component: the data map is a client module), `primitives.ts`
  (Tabs, Sheet, Badge, Button, Card, Separator, Accordion, Table, Avatar), copied only for sites with trees
  (`plan["trees"]`); `PageRenderer` renders the tree inside `[data-page]` with its `<style>`; `SiteShell` renders a
  chrome / footer tree instead of its own header / footer; `MotionRoot` reveals `[data-animate]` nodes and the
  motion CSS moves them (`fade-up/down/left/right`, `scale-in`, `--animate-delay`).
- The planner adds the tree primitives, `input` and `chart` to the shadcn list and the sections used inside trees
  (plus `Form`, for `RecordForm`) to the library files.

## Acceptance criteria

- [x] A tree page renders without an engine call, in every theme preset, light and dark.
- [x] Icons, library sections and `Link`s inside a tree use the site's icon set, sections and routes.
- [x] `animate` nodes reveal with the site's motion feel and are visible without JavaScript or with reduced motion.
- [x] Section-only sites get no tree renderer files and render exactly as before.

## Status

**Done (2026-11-04)**, on `feat/story18.10-api-drafts`. The section-library fixture gained a `/designed` page
(elements, a Tabs primitive, icons, a Faq node, `Metric`, `Chart`, `CollectionStrip`, `CollectionBrowser` with
controls); it builds in the Node sandbox (typecheck, build, routes pass) and `make design-check-fixture` screenshots
it with the other pages. Found and fixed on the way: a server component importing the client-side data map got client
references instead of components (every data node rendered as a bare fragment), so `TreeRenderer` is a client
component. Tests: `tests/test_trees.py`, `tests/test_section_renderer.py` (designed page), planner snapshots
(`trees: false` on section sites).
