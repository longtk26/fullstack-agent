# Story 13.3 — Page & component generation

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-25 · **Depends on:** 13.2, 3.2

## User story

As the frontend lane, I want each page generated from its plan entry with the nextjs-skills conventions, so
that the site matches the spec and the code matches the skill.

## Acceptance criteria

- [x] Engine calls batched per page (shared components first), with the `nextjs-skills` skill installed in the
      workspace (like 3.4), prompt `generate_frontend_page` quoting the plan entry, theme and the contract
      operations it may use.
- [x] Outside-in build: the shell (`layout.tsx` from `FrontendSpec.layout`) first, then pages, then leaf components.
- [x] Data only through the generated client + React Query hooks named in the plan; forms with RHF + Zod from
      the request schema; explicit loading, empty and error states from `sections[].states`.
- [x] Never: hard-coded colours, `import * as React`, tokens in local storage, calls to URLs outside the client,
      edits to overlay-owned files (checked in 13.4).
- [x] Commit `node:generate_frontend`.

**Status (2026-10-27):** done. Node `generate_frontend` (`src/orchestrator/frontend_nodes.py`), prompts
`generate_frontend_shell/v1`, `generate_frontend_page/v1`, project rules `prompts/frontend_conventions.md`.
Notes: one engine call for the shell and the shared components, then one per page; pages are server components
exporting `metadata` and render client components for data. The engine works in the frontend repository with
`nextjs-skills` installed (`.claude/skills` / `.agents/skills`) and the frontend rules in `CLAUDE.md` / `AGENTS.md`.
Verified with the fake engine (golden frontends for `static-landing` and `project-tracker-dynamic`); real
engines have not been run on the frontend lane yet.
