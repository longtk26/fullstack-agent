# Story 17.2 — Section renderer for static sites

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-25 · **Depends on:** 17.1, 13.2

## User story

As a user generating a static website, I want my site built from the spec in a minute or two, without waiting
for the code engine to write every page.

## Acceptance criteria

- [x] The Next.js overlay ships a section library (`src/components/sections/<Name>.tsx`, one per catalogue
      entry, nextjs-skills conventions, theme tokens only), a registry `component name → component`, and
      `PageRenderer` / `SectionRenderer`; `SectionRenderer` renders layout nodes by recursing into `children`.
      Every rendered section carries the 16.4 markers (`data-bga-section="<pageId>/<sectionId>"`,
      `data-bga-component`), so a click in inspect mode maps to one node of the spec.
- [x] Codegen writes `src/content/site.json` (the normalized pages and sections) and one thin route file per page
      (`src/app/<route>/page.tsx` → `<PageRenderer pageId=…/>` plus `metadata` from `seo`). Route files instead
      of a catch-all route keep file routing, the `routes` check and per-page metadata.
- [x] For a static spec that uses only catalogue sections, `generate_frontend` makes **no engine call**; the
      node still runs, records `engineCalls: 0` and commits `node:generate_frontend`.
- [x] The library is tested in our repo (unit render test per section with sample props from 17.1, plus the
      existing build of the golden sites), not per generation; the frontend checks still run on the generated
      site, and `conventions` treats the library and generated files as overlay-owned.
- [x] Unknown section components are still handed to the engine (17.3); the fake engine and golden frontend for
      `static-landing` are updated.
- [x] Status note records frontend-lane time for `static-landing` before and after.

**Status (2026-10-29):** done.

- Library: overlay part `templates/nextjs_overlay/files/renderer` — `layout/SiteShell` (header-footer or blank,
  theme toggle) + `MobileNav`; `renderer/PageRenderer`, `SectionRenderer`, `site.ts`; `sections/` with the ten
  content sections (from the golden static components, typed by 17.1), `CardGrid` / `List` / `DataTable` for
  content collections, the layout nodes `Columns` / `Stack` / `Grid` / `Tabs` (nested sections drop their own
  padding and page width), and helpers (`AssetImage`, `CtaLink`, `records.ts`, `nested.ts`).
- `orchestrator/frontend_renderer.py`: `renderer_gaps` (the plan gets `rendering: renderer | engine` and
  `rendererGaps`), and the generated, owned files `src/content/site.json`, `src/components/renderer/registry.ts`
  (only the sections the site uses), `src/components/sections/types.ts` (17.1) and one route file per page.
  `generate_frontend` emits `frontend.rendered` (shown in the UI log) and records
  `{pages, sections, rendering: "renderer", engineCalls: 0}`.
- **Deviations:** the library is its own overlay part and the scaffold copies only the sections a site uses (plus
  the helpers), so a site carries no unused code and needs no extra shadcn primitives; the registry is generated
  per site for the same reason. The whole frontend falls back to the engine path when anything is outside the
  library (dynamic mode, forms, custom components, `DetailView`, route parameters, the sidebar shell); rendering
  part of a page and generating the rest is 17.3. Instead of a Vitest render test per section, the fixture
  `tests/fixtures/frontend-specs/section-library.json` uses every library section and layout node (nested three
  deep); the sandbox test builds it and Playwright renders every page with no console errors. The smoke test's
  expected text now comes from sections visible on load (a `Tabs` node shows its first child only).
- Fake engine: `static-landing` needs no engine, so its golden frontend (`golden/frontend/static_landing`) is
  removed; a fake static run makes no engine call and no repair.
- **Timings** (`make up`, Docker Desktop):

  | `static-landing` | before | after |
  |---|---|---|
  | engine calls | 6 (shell + 5 pages) | 0 |
  | `generate_frontend` | 1,173 s real engine (Antigravity) / 3 s fake | 0 s |
  | repairs | 1 (226 s real, a conventions finding in an engine-written section) | 0 |
  | end to end | ~25 min real / 86 s fake (with 17.5) | **44 s** (any engine; none is called) |

  `section-library.json` (17 sections, three pages, nested layouts): 42 s end to end, 0 engine calls.
- Verified: `make test` plus every sandbox test (`BGA_SANDBOX_TESTS=1`, 441 passed; the one failure,
  `test_broken_project_reports_structured_failures`, predates Epic 17 — `model_dump()` of a `datetime` since Epic 8
  — and is fixed with `mode="json"` as `write_report` does), lint, `tsc`; `make up`: `static-landing` and
  `section-library` COMPLETED, previews served, every page rendered with its `data-bga-section` markers and no page
  errors (screenshots under `.data/shots/`).
