# Story 10.11 — Many-to-many and one-to-one relations from templates

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-04, FR-30 · **Depends on:** 10.0b

## User story

As a spec author, I want tags, members and profiles (many-to-many and one-to-one relations) generated like
one-to-many ones, with no engine call, and editable in the app's forms.

## Why

`backend/codegen.py`'s `database_gaps` sends every one-to-one relation and every link model to the engine, so a spec with
tags or members is never CRUD-only.

## Acceptance criteria

- [ ] Many-to-many: the link model (composite primary key, both foreign keys with `ondelete`, optional extra
      columns), its migration, and operations to list, add and remove related records
      (`GET|POST /projects/{id}/members`, `DELETE /projects/{id}/members/{userId}`); responses carry summaries of the
      related records (10.0b), loaded in one query per page.
- [ ] One-to-one: a unique foreign key; the parent's response embeds the child's summary; creating a second child is
      409.
- [ ] `database_gaps` no longer names these relations; the examples with them make no engine call for their models.
- [ ] The contract marks link fields (`x-bga.source: reference`, `many: true`) and the mocks' fixtures hold link
      records (the multi-select picker and chips: [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [ ] Contract and codegen snapshots for both kinds; template tests for add, remove, duplicate add (409) and delete
      cascades.

## Status

**Planned (2026-11-04).** Added with Checkpoint E.
