# Story 9.7b — FrontendSpec review aids

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-18, FR-21, FR-22 · **Depends on:** 9.7a, 12.4

> Split from 9.7 on 2026-10-27. Mode cards, the FrontendSpec editor with live validation and example loading,
> the dynamic pair with its consistency list, and submit are in [9.7a](story9.7a_generate_frontend_from_ui.md);
> those criteria below are ticked there and kept here for context.

## User story

As a user starting a new generation, I want to be asked first whether I want a static site, a dynamic web app or
only an API, and then review what will be built (pages, theme, components) before I submit.

## Acceptance criteria

- [ ] `/generations/new` starts with a mode choice (cards):
  - **Static website** — "pages only, no backend": FrontendSpec input, no contract.
  - **Dynamic web app** — "frontend + backend, generated in parallel": FrontendSpec + BackendSpec + contract.
  - **Backend API only** — today's flow (9.2).
  The choice is kept in the URL (`?mode=`) and the draft store.
- [ ] Requirement tab drafts the specs for the chosen mode (12.4) from typed text or a `.md` / `.txt` file (9.2)
      and shows assumptions / unresolved items to acknowledge.
- [ ] After a static or dynamic draft, a **Design** panel shows the chosen direction and its 2 alternatives (12.6)
      as cards with colour swatches, font names and section order; picking one replaces the theme and the home
      page's section order with no engine call (added 2026-10-30).
- [ ] FrontendSpec tab: Monaco editor bound to the FrontendSpec JSON Schema with live validation (12.1, 12.5 in
      dynamic mode); a summary panel shows **page count and route list**, **theme** (colour swatches, fonts,
      radius, light/dark), the **component catalogue** (with which pages use each) and, in dynamic mode, the
      operations each page uses.
- [ ] Dynamic mode shows both editors (FrontendSpec, BackendSpec) and a read-only contract preview; consistency
      errors are marked in the editor that must change.
- [ ] Options per lane; submit is disabled while any spec or consistency error exists.
