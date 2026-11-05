# Story 22.1 — Separate flows and a static guard

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-36, FR-21 · **Depends on:** Epic 21

## User story

As the user of the agent, I want the dynamic app frontend changed without any risk to static sites, so that the work
on apps never makes a static site worse.

## Problem

Static and dynamic share the draft prompt (`draft_frontend_spec@v10`), direction cards, tree drafting
(`drafting/trees.py`, `config.frontend_trees`), the renderer and the overlay's `common` and `renderer` files. A fix
for one mode lands in the other, and nothing would notice.

## Steps

1. **Static golden.** For each static example (`static-landing`, `street-food-static`) and one static requirement on
   the fake engine: draft, then render, and record a digest of every output file (FrontendSpec, `site.json`, page
   files, CSS) in `tests/fixtures/static-golden/`. A test fails when any digest changes; `UPDATE_SNAPSHOTS=1` updates
   them only with a note in the story that changed them.
2. **Mode switch in drafting.** `drafts.py` sends a dynamic draft to `drafting/app.py` (new) when
   `DYNAMIC_FRONTEND=app` and keeps today's path for static mode and for `DYNAMIC_FRONTEND=legacy` (default `legacy`
   until 22.4 is done, then `app`). Tree drafting and direction cards run for static only in the new path.
3. **Mode switch in the frontend lane.** The frontend planner and renderer pick the app screens for dynamic specs made
   by the new flow (`project.flow: "app"`, additive), and today's path otherwise.
4. **Where new code goes.** Dynamic-only orchestrator code in `orchestrator/frontend/app/`, prompts in
   `prompts/draft_app/`, overlay files in `templates/nextjs_overlay/files/dynamic/app/`. Edits to shared files
   (renderer, `common` overlay, section components) are allowed only when the static golden stays the same.
5. **Docs.** `agent-api/CLAUDE.md` gets the rule and the layout; `docs/development/test-doubles.md` lists the switch.

## Acceptance criteria

- [ ] The static golden test exists and passes on `main` before any other change of this epic.
- [ ] `DYNAMIC_FRONTEND=legacy` gives today's dynamic draft and frontend lane unchanged (the existing tests pass).
- [ ] `DYNAMIC_FRONTEND=app` reaches the new path (an empty outline renders a shell with no screens, for now).
- [ ] The switch, the `project.flow` field and the code layout are documented.

## Verify

`make lint`, `make test ARGS=tests/test_static_golden.py`, then `make test`.

## Status

**Planned (2026-11-05).**
