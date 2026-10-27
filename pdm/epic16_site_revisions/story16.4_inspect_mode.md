# Story 16.4 — Inspect mode in the preview

**Epic:** [16 — Site revisions & feedback](epic16_site_revisions.md) · **Requirements:** FR-18, FR-29, §8.1 · **Depends on:** 16.3, 9.9

## User story

As a user looking at my generated site, I want to click a part of the page and leave a comment on it, instead of
describing where it is.

## Acceptance criteria

- [ ] Every section root carries `data-bga-section="<pageId>/<sectionId>"` and `data-bga-component="<Name>"`
      (assets already carry `data-bga-asset`, 15.1); a new convention rule `section-markers` checks it, so engine
      code cannot drop them.
- [ ] Overlay client component `Inspector`, **inert by default**. It activates only inside an iframe, after a
      `postMessage` handshake from the allowed agent-UI origin. The preview container supplies that origin at
      runtime (dynamic: runtime config; static: `/runtime-config.json` written when the container starts); a
      downloaded ZIP has none, so the inspector stays inert.
- [ ] Inspect on: hovering outlines a section with its component name; a click sends `{ page, section, component,
      rect }` to the agent UI, which opens a comment box anchored there; Escape leaves inspect mode.
- [ ] Messages are checked by origin in both directions; the inspector reads no cookies or storage and makes no
      network requests.
- [ ] The same channel applies live theme variables for the theme editor (`bga:theme`, 16.2).
- [ ] UI: an **Inspect** toggle on the frontend preview (generation page and App tab, 9.9); comments show as pins
      and collect in a pending list; **Apply N comments** submits one feedback revision (16.3).
- [ ] Tests: marker rule; origin checks (wrong origin ignored); Playwright test on a golden frontend that clicks a
      section and receives the message.
