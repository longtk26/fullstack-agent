# Story 22.8 — Design checks, measurement and switch-over

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-36 · **Depends on:** 22.7

## User story

As the user of the agent, I want to see the new app flow beat the old one on real requirements before the old one is
removed from dynamic mode.

## Steps

1. **Measure** (with the user's yes, paid engine for drafts only): book club, flashcards, project-tracker and
   workshop-bookings on both flows (`DYNAMIC_FRONTEND=app` and `legacy`): draft time and calls, frontend lane time and
   engine calls, operations reachable, id inputs, design-check findings.
2. **Screenshots** of each app's list, detail, form and dashboard in light and dark at 375 px and 1440 px, side by
   side with the legacy flow, for the user's review.
3. **Switch-over**, after the user accepts: remove the legacy dynamic path (trees, direction cards, Manage area and
   journey drafting for dynamic specs); keep everything static uses. Old dynamic generations still open and download.
4. **Docs**: requirements, `agent-api/CLAUDE.md`, the backlog and the agent UI's mode description.

## Acceptance criteria

- [x] The measurement table is in this story's Status, with the run ids.
- [x] The user accepted the screenshots. (The user waived them: "only need test on app, don't need to show image side
  by side to me. Because i would like remove legacy way", 2026-11-06.)
- [x] After the switch-over, `DYNAMIC_FRONTEND` is gone; dynamic drafts use the app flow; static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`; `make up`, one static and one dynamic generation on the
fake engine.

## Status

**Done (2026-11-06).** The user chose the switch-over with the app flow as the default and asked for the legacy way
to be removed completely, with no side-by-side screenshots and no comparison runs of the legacy flow (step 2 waived;
step 1 measured on the fake engine, below; the epic's one Antigravity run is the end-to-end check).

Measurement (fake engine and code, no paid calls; the legacy column is the hand-written dynamic examples the legacy
flow drafted from, now `agent-api/tests/fixtures/pair-specs/`):

| App | Flow | Operations | Unreachable | Id inputs | Pickers | Pair issues |
|---|---|---|---|---|---|---|
| flashcards | legacy | 15 | 6 (`card.update`, `deck.create/update/delete`, `reviewLog.create/list`: the Manage area's) | 1 (`deckId`) | 0 | — |
| flashcards | app | 19 (+4 dashboard aggregates) | 0 | 0 | 1 | 0 |
| project tracker | legacy | 10 | 2 (`task.get`, `task.update`) | 0 | 0 | — |
| project tracker | app | 13 (+3 aggregates) | 0 | 0 | 1 | 0 |
| corner shop | legacy | 8 | 2 (`cartItem.update/delete`) | 0 | 0 | — |
| corner shop | app | 8 | 0 | 0 | 1 | 0 |
| workshop bookings | app only (Story 22.7) | 28 (10 of plugins) | 0 | 0 | 1 | 0 |

Draft calls: the app flow makes one engine call (`draft_app@v1`) per draft; the legacy flow made one draft call, one
per designed page and one for the chrome (7–13 for these apps), plus direction-card repairs. The app flow's frontend
lane makes no engine call. Live runs on the fake engine (`make up`): see the verification below; design checks of the
app kit are Stories 22.4–22.7's (`make design-check-app`, the app and plugin walks).

Verification (2026-11-06): `make lint`, `make test` (0 failures), the frontend and preview sandbox tests
(`BGA_SANDBOX_TESTS=1`, 14 passed); `make up`, then on the fake engine the flashcards app
(`gen_01M6QKXVCGPMJS866EJXK3VDAY`, COMPLETED in 169 s, the live app walk 21/21) and the Northwind static site
(`gen_01M6QKXVC2JP6PYNTN8SHAATV4`, COMPLETED in 20 s, every page served).

The epic's one Antigravity run (the user's "Soccer Pitch Bookings" requirement: players sign up, book and pay;
staff confirm or cancel; no double booking; players see only their own bookings) **failed in drafting**:
`gen_01M6QM5T7P2MC0F6GJ28M4BJFP`, draft `10951828-…`, 181 s, two calls (`draft_app@v1` 110 s, `repair_spec@v3`
68 s, about $0.23), "The engine wrote no spec". Antigravity's own session logs show why: `draft_app@v1` still said
"Do not add authentication, sign-in or user accounts" (written in 22.2, before the plugin frontends) while the
requirement has players and staff; the model went looking for a `Player` / `Staff` entity, tried to read the repo's
`package.json` outside its directory, the CLI refused the read and, in print mode, ended the run with nothing written;
the repair round (`DRAFT_FILE_MISSING`) did the same. Fixed:
- `draft_app@v2`: sign-in and roles (`auth`, never an entity for the people who sign in), `policies` (role,
  ownership), status flows (`transition`, `immutableAfter`), `image` / `file` fields, `payments`, many-to-many; "never
  open a file outside the current directory; always write all three files". Its BackendSpec example is
  `specs/workshop-bookings.json` (every plugin; backend drafts keep `specs/shop.json`) and workshop bookings joins the
  outline examples. Snapshots `tests/fixtures/prompts/draft_app.v2{,.inline}.md`.
- A draft whose engine wrote no BackendSpec fails with the check's reason ("The draft has no backend-spec.json (after
  1 repair(s))") instead of "The engine wrote no spec".
With the user's yes, a second run on `draft_app@v2` (`gen_01M6QP98WECNXD12B4A9EMDZ03`, draft `5152215b-…`, 588 s)
**drafted a valid app** (292 s, 22 agent turns, 845K input tokens) after one repair (293 s, a CLI error at its end;
its errors: 16 × `UNKNOWN_FIELD_REF` "No field 'p'", 'i', 't', … from one mistake, a no-overlap `scope` written as
the string `"pitchId"`), then failed in code: the rules plugin crashed building the contract (`KeyError: 'path'`;
`entry`, the contract operation, was overwritten in the concurrency loop when one operation has both a status rule
and a concurrency rule). The draft cost $0.53 for 1.3M input / 69K output tokens: every agent turn re-sends what it
read. Fixed with the user (2026-11-06):
- The `entry` bug (`refusal`), with a test of a status flow next to a no-overlap rule
  (`tests/test_concurrency_rules.py`).
- **Drafting is API-only**: only an engine that drafts (`ICodeEngine.drafts`: the Gemini API engine, the fake) may
  draft; a CLI draft engine is a 422 (`EngineRegistry.check_draft_engine`); the UI's draft engine picker lists only
  those. A draft's repairs run on the same API engine; code and its repairs stay on the CLI engines.
- **Structured output** for app drafts on the API engine (`drafting/answer_schema.py`, `EngineRequest.response_schema`
  → `responseJsonSchema`): the three files with their keys, types, enums and required fields, rule params typed per
  kind (a `scope` is a list); the examples and both recorded Antigravity drafts validate against it; a 400 for the
  schema retries once without it.
- **Code fixes** before any check (`fix_backend_defaults`): a field list written as one string becomes a list, an
  entity without a primary key gets `id`; the validator reports a string `scope` once (`RULE_PARAMS_INVALID`), not
  per letter. Tests: `tests/test_structured_drafts.py`, `tests/test_draft_engines.py`.

The third run, drafted on the Gemini API and coded by Antigravity (`gen_01M6QREW4Q9CQ7KYP1EV8X38GY`, draft
`32a2ce28-…`), **COMPLETED in 212 s**, every lane COMPLETED including the live integration:

| Soccer draft | Engine | Calls | Model turns | Input tokens | Output tokens | Draft time | Repairs | Cost |
|---|---|---|---|---|---|---|---|---|
| run 1 (`draft_app@v1`) | Antigravity | 2 | 28 | 643K | 23K | 181 s, no spec | 1 | $0.23 |
| run 2 (`draft_app@v2`) | Antigravity | 2 | 43 | 1.31M | 69K | 585 s | 1 | $0.53 |
| run 3 (v2, structured) | Gemini API | 1 | 1 | 6,875 | 13,870 | **82 s** | **0** | **$0.06** |

Run 3's draft: roles `player` / `staff`, policies `staffOnly` and `ownBookings` (ownership), a `transition` flow, a
`immutableAfter` lock, a `noOverlap` rule per pitch, payments, a photo, a dashboard of bookings per pitch this week and
revenue by surface (two aggregates added by code). The model still wrote `scope` as a string; the code fix made it a
list (a note on the draft), so no repair ran. The backend was fully templated (no Antigravity call). Live checks: the
app walk 15/15 as staff; the plugin walk's sign-up, sign-in guard and wrong-password steps (its other steps are the
workshop example's); and against the API: a player's booking 201 (PENDING, UNPAID, `pay`), an overlapping one 409
`OVERLAP`, a player sees only their own bookings (2 of 5), a player's confirm 403, staff confirm 200, checkout 201,
an edit after cancelling 409 `RESOURCE_LOCKED`, no token 401.

Open: the booking form asks for `startsAt`, `endsAt`, `surface` and `amount`, fields the model added so the
no-overlap rule and the revenue chart have their data; they should be derived (from date, start time and hours; the
pitch's surface; hours × hourly price). The BackendSpec has no computed fields yet (backlog). Whether Gemini enforced
the answer schema or refused it (and the engine retried without it) is not recorded outside the deleted draft
directory; the engine's event says which.

What was removed:
- `DYNAMIC_FRONTEND` / `config.dynamic_frontend` (config, compose, `.env.example`); `drafting/app.app_flow` is every
  dynamic draft.
- From drafting: the dynamic branches of `drafts.py` (Manage area, pair fixes, the last-resort prune, the trees'
  backend completion, the dynamic example), `drafting/pair_fixes.py`, `trees.complete_backend_for_trees`, the dynamic
  text of the fact pack.
- The Manage area (`coverage.add_manage_area` / `remove_manage_area`, the `manageArea` option of the API and the UI,
  the summary panel's Manage group and "Drop area").
- Journeys: the FrontendSpec field and models, their validation, coverage, consistency check, codegen (with the dead
  smoke and form test generators), the frontend `journeys` check, the live journeys stub, backend completion's
  journey matching, the UI's journey summary, results and badge. A stored spec with an empty `journeys` list still
  validates (the validator drops the key).
- Dynamic tree bindings (`tree_bindings` contract branch, `derive_operations`, `aggregate_id`), the renderer's
  API-bound sections (`_record_schema` moved to codegen, `_detail_links`, operation columns), the planner's dynamic
  component domains and hooks, custom components' dynamic render test and operation / journey inputs.
- The fake engine's golden dynamic frontend (`golden/frontend/corner_shop`), the shop's hand-written custom
  components, the dynamic draft fixtures' FrontendSpecs; `examples/frontend-specs/*-dynamic.json`; the UI's example
  pair offer.
- A dynamic FrontendSpec without `project.flow: "app"` is `FE_APP_FLOW` (hint: draft the app again from its
  requirement), and `plan_frontend` refuses it. Old dynamic generations still open and download (their files and
  artifacts are stored); re-running one needs a new draft.

Deviations:
- **Static golden refreshed** (`UPDATE_SNAPSHOTS=1`): the drafted static spec no longer carries `"journeys": []`
  (autofix wrote it); its two FrontendSpec digests per example changed, every rendered file is byte for byte the
  same. The site schema digest (`frontend-spec.site.digest.md`) lost the `Journey*` types the same way.
- Kept, as inert for static sites: the renderer overlay's TypeScript branches for API bindings (`site.ts`,
  `use-section-records.ts`, the forms and actions); changing them would change every static site's files. Prompts
  keep their `mode == "dynamic"` blocks (`draft_frontend_spec@v10`, `draft_tree@v1`), now unreachable;
  `complete_backend@v5` and `generate_custom_component@v5` are rendered with empty journeys and operations.
- Custom components (Story 17.3) are a static site's feature now; their tests use a static shop of three custom
  components (`tests/fixtures/frontend-specs/shop-static.json`). Evicting a cached component after a failed build
  only happened in the dynamic lane (static sites have no validation node); its test is gone.
- Tests of shared dynamic machinery (lanes, previews, contract, pair check) run on apps of the app flow
  (`tests/generation_helpers.app_pair`; `dashboard=False` keeps an example's BackendSpec as it is), or on the old
  hand-written specs marked as apps where only the pair check reads them. Where a test needed the frontend lane to be
  slow or fail inside an engine call, it is slow or fails in its validator (`SlowFrontendValidator`).
- `check_draft` reports `MODE_MISMATCH` first whenever the declared mode is another one (a dynamic spec in a static
  draft is now invalid for that reason alone).
