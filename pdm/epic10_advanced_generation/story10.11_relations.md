# Story 10.11 — Many-to-many and one-to-one relations from templates

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-04, FR-30 · **Depends on:** 10.0b

## User story

As a spec author, I want tags, members and profiles (many-to-many and one-to-one relations) generated like
one-to-many ones, with no engine call, and editable in the app's forms.

## Why

`backend/codegen.py`'s `database_gaps` sends every one-to-one relation and every link model to the engine, so a spec with
tags or members is never CRUD-only.

## Acceptance criteria

- [x] Many-to-many: the link model (composite primary key, both foreign keys with `ondelete`, optional extra
      columns), its migration, and operations to list, add and remove related records
      (`GET|POST /projects/{id}/members`, `DELETE /projects/{id}/members/{userId}`); responses carry summaries of the
      related records (10.0b), loaded in one query per page.
- [x] One-to-one: a unique foreign key; the parent's response embeds the child's summary; creating a second child is
      409.
- [x] `database_gaps` no longer names these relations; the examples with them make no engine call for their models.
- [x] The contract marks link fields (`x-bga.source: reference`, `many: true`) and the mocks' fixtures hold link
      records (the multi-select picker and chips: [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [ ] Contract and codegen snapshots for both kinds; template tests for add, remove, duplicate add (409) and delete
      cascades.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`; the snapshot criterion is met by unit tests (see deviations).

- **Models from templates**: a many-to-many relationship's link model (composite primary key of its two foreign keys,
  each `ON DELETE CASCADE`, no domain entity) and `Relationship(link_model=…)` on both sides; a one-to-one parent's
  side is one record (`sa_relationship_kwargs={"uselist": False}`), the child's foreign key unique. `database_gaps`
  names neither any more, so these models make no engine call; the link columns carry API names (`projectId`).
- **One-to-one**: the parent's response embeds the child's `{id, label}` summary (`model.children`; the repository's
  `references()` loads them with one `IN` query per page; `References` now holds labels or summaries); creating a
  second child is 409 (the unique foreign key). The contract's schema, examples, `presented_record` and the MSW
  `present()` show it too (`x-bga.entities[...].children`).
- **The `relations` plugin** (`orchestrator/plugins/relations.py`): per link model, `GET /<parents>/{id}/<children>`
  (a page of `{id, label}` summaries in one query, plus the total), `POST` (`{<child>Id}`; 404 parent, 400
  `REFERENCE_NOT_FOUND` child, 409 `DUPLICATE`) and `DELETE …/{<child>Id}` (404 when not related); signed in with
  auth. Template tests: relate, list, unrelate (and again, 404), relate twice 409 and an unknown record 400, and
  deleting the parent removes its links (`ON DELETE CASCADE`), seeded with the CRUD tests' own helpers.
- **Contract**: the routes with errors and scenarios (already related, unknown child, not related, unknown parent);
  the add body's field is `x-bga.source: reference` with `many: true` and the child's list operation;
  `x-bga.entities[Parent].links`; the link records are fixtures (`ProjectMemberLink`) and seeded. A one-to-one child's
  fixtures leave one parent free, its create succeeds there, and "second <child>" is a 409 scenario.

**Deviations:**

- Parent records do not embed their many-to-many related records; the list route answers them, a page at a time.
- The snapshot criterion is covered by `tests/test_relations.py` (models, repository, routes, contract) rather than new
  golden files; the existing plan and codegen snapshots were updated for `children: []` and the `References` alias.

**Verified:** `make lint`; `tests/test_relations.py` (4); `make test` (all pass after the snapshot updates and the
one-to-one gap assertion); `BGA_SANDBOX_TESTS=1` for a projects / members / profiles spec through the workflow
(`test_a_backend_with_many_to_many_and_one_to_one_relations_passes_its_tests`): every check passes on the first try,
no engine call for the models, 30 template tests, 26 scenarios, 16 operations matching. `make up`, then a fake-engine
backend generation of it (`gen_01M6NBQV8JBM3V9MTMR40GJ6X2`): a member answers `profile: null`, then its profile's
summary; a second profile is 409; relating Ada and Bob is 201, Ada again `DUPLICATE`; the list pages (total 2, limit
1); unrelating Bob leaves 1; deleting the project leaves the members.
