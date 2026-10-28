# Story 17.2 — Section renderer for static sites

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-25 · **Depends on:** 17.1, 13.2

## User story

As a user generating a static website, I want my site built from the spec in a minute or two, without waiting
for the code engine to write every page.

## Acceptance criteria

- [ ] The Next.js overlay ships a section library (`src/components/sections/<Name>.tsx`, one per catalogue
      entry, nextjs-skills conventions, theme tokens only), a registry `component name → component`, and
      `PageRenderer` / `SectionRenderer`; `SectionRenderer` renders layout nodes by recursing into `children`.
      Every rendered section carries the 16.4 markers (`data-bga-section="<pageId>/<sectionId>"`,
      `data-bga-component`), so a click in inspect mode maps to one node of the spec.
- [ ] Codegen writes `src/content/site.json` (the normalized pages and sections) and one thin route file per page
      (`src/app/<route>/page.tsx` → `<PageRenderer pageId=…/>` plus `metadata` from `seo`). Route files instead
      of a catch-all route keep file routing, the `routes` check and per-page metadata.
- [ ] For a static spec that uses only catalogue sections, `generate_frontend` makes **no engine call**; the
      node still runs, records `engineCalls: 0` and commits `node:generate_frontend`.
- [ ] The library is tested in our repo (unit render test per section with sample props from 17.1, plus the
      existing build of the golden sites), not per generation; the frontend checks still run on the generated
      site, and `conventions` treats the library and generated files as overlay-owned.
- [ ] Unknown section components are still handed to the engine (17.3); the fake engine and golden frontend for
      `static-landing` are updated.
- [ ] Status note records frontend-lane time for `static-landing` before and after.

**Status:** open.
