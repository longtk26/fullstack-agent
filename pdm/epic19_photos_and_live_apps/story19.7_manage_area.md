# Story 19.7 — Operation coverage and the Manage area

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-32 · **Depends on:** 19.6

## User story

As a user of a dynamic app, I want every operation of my API reachable from the UI: the designed screens cover
the main journeys, and a generated Manage area covers the rest, so that nothing the backend can do is hidden.

## Evidence

The measured run used 7 of 13 operations: `card.get`, `card.update`, `card.delete`, `deck.update`, `deck.delete`,
`reviewLog.list` had no screen.

## Steps

1. **Coverage.** Pure function `uncovered_operations(frontend_spec, contract) -> list[str]`: operations no data
   binding, form (submit or `load`), action, `Stats` item or journey step (19.8) references. Suggested home:
   `modules/shared/domain/frontend_spec/coverage.py`, exported like the other helpers.
2. **Manage area.** Pure function `add_manage_area(frontend_spec, contract) -> (spec, notes)`, deterministic, no
   engine. For each entity with uncovered operations, using only the operations that exist:
   - `/manage` index page: a card per entity (title, description, link);
   - `/manage/<plural>`: `DataTable` on the list operation with all declared `controls`, row actions view / edit /
     delete, a "New" link to the create page;
   - `/manage/<plural>/new`: `Form` on the create operation;
   - `/manage/<plural>/[id]`: `DetailView` on the get operation with edit / delete actions and, for each uncovered
     custom operation whose path takes this entity's id, an action (a form section for its request body when it
     has required fields the record cannot supply);
   - `/manage/<plural>/[id]/edit`: `Form` with `load` (get) and submit (update);
   - custom operations without an entity id in their path: an `ActionBar` (no body) or a `Form` (body) on the
     entity's list page;
   - one header navigation link "Manage" to `/manage`.
   Titles, labels and columns come from entity and field names (humanised), field types choose the formats
   (`date`, `datetime`, `badge` for enums, `image` for image fields). Pages use ids prefixed `manage-` and routes
   under `/manage`, so the function is **idempotent** (it replaces its own pages, never touches others).
3. **Operations that need sign-in.** Operations with `auth` or a policy are left out while generated frontends
   have no login; each gets an assumption note ("`x.delete` needs sign-in, which generated frontends do not have
   yet").
4. **Where it runs.**
   - Drafting (dynamic): after the autofix of 18.3, before `check_draft`; its notes become assumptions.
   - Generation: for a submitted pair (not from a draft, or edited after drafting), in `validate_inputs` /
     `build_contract`, before the frontend plan, when `options.frontend.manageArea` is true (default true; the
     generation form gets a switch "Generated Manage area").
5. **Pair check.** New warning `FE_OPERATION_UNUSED` for any operation still uncovered (sign-in ones included, with
   the reason); shown in the draft review and the report.
6. **Review UI.** The spec review groups the Manage pages (collapsed by default, labelled "generated") with a
   toggle to drop the area for this draft.
7. Tests: coverage on the measured case's pair (rebuild it as a test fixture: Deck, Card, ReviewLog,
   ContactMessage, 13 operations); the Manage area for an entity with full CRUD, with only list + create, with a
   custom operation by id and one without; idempotence; sign-in operations left out with notes; the generated
   spec validates and passes the pair check.

## Acceptance criteria

- [x] After drafting or before generation, every operation that does not need sign-in is reachable from the UI.
- [x] The Manage area is deterministic, idempotent, uses only existing operations, and can be switched off.
- [x] Sign-in operations are reported, not hidden silently.
- [x] `FE_OPERATION_UNUSED` appears in the review and the report for whatever stays uncovered.
- [x] The review shows the generated pages as a group with a toggle.

## Verify

`make lint`, `make test`, `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint`, `make up` with the fake engine:
dynamic `project-tracker-dynamic` + `two-entity` COMPLETED with a working Manage area (create, edit, delete on the
mock API and on the live API after the switch).

**Checkpoint B after this story:** stop for review.
