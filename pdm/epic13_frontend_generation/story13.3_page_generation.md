# Story 13.3 — Page & component generation

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-25 · **Depends on:** 13.2, 3.2

## User story

As the frontend lane, I want each page generated from its plan entry with the nextjs-skills conventions, so
that the site matches the spec and the code matches the skill.

## Acceptance criteria

- [ ] Engine calls batched per page (shared components first), with the `nextjs-skills` skill installed in the
      workspace (like 3.4), prompt `generate_frontend_page` quoting the plan entry, theme and the contract
      operations it may use.
- [ ] Outside-in build: the shell (`layout.tsx` from `FrontendSpec.layout`) first, then pages, then leaf components.
- [ ] Data only through the generated client + React Query hooks named in the plan; forms with RHF + Zod from
      the request schema; explicit loading, empty and error states from `sections[].states`.
- [ ] Never: hard-coded colours, `import * as React`, tokens in local storage, calls to URLs outside the client,
      edits to overlay-owned files (checked in 13.4).
- [ ] Commit `node:generate_frontend`.
