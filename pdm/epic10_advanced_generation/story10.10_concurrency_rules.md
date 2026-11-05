# Story 10.10 — Capacity, no-overlap and unique-together rules

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-07, FR-34 · **Depends on:** 10.4

## User story

As a spec author, I want the rules that break under concurrent requests (a full workshop, a double-booked room, a
second booking by the same user) generated from templates and enforced by the database, so that two requests at the
same moment cannot both succeed.

## Why

Today these go to the engine as custom rules, and a check-then-write in a use case lets two concurrent requests both
pass. They are common in booking, stock and scheduling apps, and each has a known correct shape.

## Acceptance criteria

- [ ] New rule kinds in the `rules` plugin (BackendSpec `RuleKind`, additive):

| Kind | Example | Enforced by | Rejection |
|---|---|---|---|
| `capacity` | a workshop's active bookings ≤ `workshop.capacity` | use case locks the parent row (`SELECT … FOR UPDATE`) then counts, in one transaction | 409 `CAPACITY_REACHED` |
| `noOverlap` | a room's bookings never overlap in `[startsAt, endsAt)` | Postgres exclusion constraint (`btree_gist`, `tstzrange … &&`) in the migration; the violation is mapped | 409 `OVERLAP` |
| `uniqueTogether` | one booking per (user, workshop) | unique constraint across the fields; `IntegrityError` mapped with `details.fields` | 409 `DUPLICATE` |

- [ ] Each kind takes a filter of which records count (e.g. `status != CANCELLED`), checked by the validator.
- [ ] Template tests include **concurrent** requests (two sessions at once): exactly one succeeds.
- [ ] A full parent's `allowedActions` has no `create:<child>`; the 409s carry their code and `details.fields` in
      `x-bga.errors`; scenarios cover the last seat, a full workshop, an overlap and a duplicate; so the app can show
      "full" and the rejection on its field ([22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [ ] The drafter maps "no double booking", "limited seats", "only once per user" to these kinds instead of
      `custom`.

## Status

**Planned (2026-11-04).** Added with Checkpoint E.
