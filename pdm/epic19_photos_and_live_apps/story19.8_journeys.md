# Story 19.8 — Journeys and domain operations

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-32, FR-2 · **Depends on:** 19.6, 19.7

## User story

As a user, I want my requirement turned into the journeys my users take, and the backend to get the operations
those journeys need (not only CRUD), so that the generated app does what I asked, such as studying the cards due
today and scheduling the next review.

## Evidence

The vocabulary requirement produced a pure-CRUD BackendSpec: `Card` has `intervalDays`, `dueDate` and
`repetitionCount`, but no operation lists the due cards or schedules a review; the study screen could only create a
`ReviewLog`.

## Steps

1. **`journeys` in the FrontendSpec** (optional, additive), `frontend_spec/schema_v1.py`:
   `journeys: [{id, title, goal, steps: [Step]}]`, a step being one of
   - `{do: "visit", page}`
   - `{do: "open", section, record?: "first" | <index>}` (follow a record's link)
   - `{do: "submit", section, values: {field: value}}` (a form)
   - `{do: "action", section, action, record?: "first" | <index>}` (19.6 actions / ActionBar)
   - `{do: "expect", section, text? | count? | changed?: {field, record?}, live?: bool}`
   `live: true` marks an expectation only the real backend can meet (e.g. `dueDate` moved forward); mocks skip it.
   Values may use `$unique` (replaced by a unique string per test run).
2. **Validation.** Pages, sections, forms and actions a step names exist; `submit` names a form section; `action`
   names an action of that section; values are form fields. Pair check: the operations behind the steps exist.
   Journey operations count as covered (19.7).
3. **Domain operations in the BackendSpec.** No schema change (custom operations exist: `type: "custom"`,
   `request`, `response`, `description`, `rules`). The draft prompt requires, for every journey step that CRUD
   cannot do, a custom operation whose `description` states the behaviour precisely enough to implement and test
   (inputs, the rule, outputs, errors), and the list `filters` / `sort` / `search` the screens need.
4. **Draft prompt `draft_frontend_spec/v7.md`** (dynamic mode; copy of v6): write the journeys first (2–5, the
   product's core loop first; for "learn vocabulary like Anki": browse decks, add cards, study due cards with
   ratings that reschedule them, see progress), then the BackendSpec (CRUD + domain operations), then the
   FrontendSpec: journey screens designed, using 19.6 sections; the Manage area (19.7) covers the rest, so do not
   design admin screens. Switch `drafting.py`.
5. **`complete_backend/v2.md`** (copy of v1): each custom operation implements its `description` exactly, and gets
   API tests derived from the description and from the journeys that use it (`tests/modules/<module>/`), so the
   backend lane's checks catch a wrong schedule before integration. Pass the journeys that touch a module into the
   prompt context. Switch `backend_codegen` / the node that renders it.
6. **Custom components** (`generate_custom_component` latest version + 1): the prompt context gets the journeys that
   use the component and the operations it must call (`useOperationMutation`), so the study screen calls
   `card.review` instead of only showing cards.
7. **Golden pair** `examples/frontend-specs/flashcards-dynamic.json` + `examples/specs/flashcards.json`: decks,
   cards (`front`, `back`, `example`, `intervalDays`, `ease`, `dueDate`, `repetitionCount`), review logs; domain
   operations `card.listDue` (GET, filter `deckId`, due on or before today), `card.review` (POST
   `/cards/{id}/review`, body `{rating: again|hard|good|easy}`, SM-2 rules in the description, returns the updated
   card), `deck.stats` (GET `/decks/{id}/stats`: total, due today, learned); journeys for browse, add, study and
   progress; the study page uses `DetailView` + `ActionBar` (ratings) or a custom component. The fake engine
   writes a correct `card.review` for it (list it in `docs/development/test-doubles.md`).
8. **Review UI.** The draft review shows the journeys (title, goal, steps as a numbered list with the page /
   section / operation each touches), read-only; journey problems from the validator appear next to the step.
9. Tests: schema and validator (each step kind, unknown references, `$unique`); the pair check; prompt snapshots
   (v7, complete_backend v2); the golden pair validates; a fake dynamic generation of the golden pair COMPLETES with
   `card.review` implemented and its API tests passing.

## Acceptance criteria

- [ ] FrontendSpec accepts `journeys`; their references are validated against the spec and the contract.
- [ ] Dynamic drafts write journeys first and add domain operations with implementable descriptions.
- [ ] Custom operations are implemented with API tests derived from their descriptions and journeys.
- [ ] Custom components know the journeys and operations they serve.
- [ ] Golden flashcards pair added; a fake generation of it COMPLETES.
- [ ] The review shows journeys.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint`,
`make up` with the fake engine: the flashcards pair COMPLETED; in the live preview, rating a due card moves its due
date.
