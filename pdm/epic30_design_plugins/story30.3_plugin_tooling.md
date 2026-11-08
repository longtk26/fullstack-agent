# Story 30.3 — Tooling to add a plugin in a day

**Epic:** [30 — Design plugins](epic30_design_plugins.md) · **Requirements:** FR-44 · **Depends on:** 30.2

## User story

As the person adding design plugins day by day, I want a command that starts a plugin from its kind's template and a
command that checks it the way the gates require, so that each new plugin is quick to make and safe to offer.

## Steps

1. **`make design-plugin-new KIND=<kind> NAME=<name>`**: copies `templates/design/_starter/<kind>/` (a descriptor
   with `status: "draft"`, a component implementing the kind's props contract, a fixture) into the new folder.
2. **Fixtures:** each kind has a synthetic fixture app (BackendSpec + outline) that meets every `needs` key of the
   kind; a plugin's fixture is a small override of it (the design values that select the plugin).
3. **`make design-plugin-check NAME=<name>`**: builds the fixture on mocks in the Node runner and runs the gates (D6):
   375 / 1440 px, light / dark, in every `ready` recipe (or, for a recipe, on every kind's fixture); keyboard and
   focus order; AA contrast on the composite; reduced motion and reduced transparency; loading, empty and error states
   (the mocks' switches); a screenshot `preview.png` written into the folder. Prints a pass / fail table.
4. **Promotion:** a plugin becomes `ready` only by editing its descriptor after a clean check; CI's registry test runs
   the check's fast part (descriptor, fallback, exports exist, fixture builds) for every plugin.
5. **The guide** (`docs/development/design-plugins.md`): kinds, descriptor fields, props contracts, steps, gates,
   naming, what never to do; kept in sync with the starter templates.
6. Tests: the starter of each kind passes the fast checks as generated; the check's result parsing.

## Acceptance criteria

- [ ] A new plugin of any kind can be started, built, checked and promoted with the two commands and the guide.
- [ ] A plugin with a failing gate cannot be `ready` (the registry test refuses it).

## Verify

`make design-plugin-new KIND=card NAME=try`, `make design-plugin-check NAME=try`, `make test`.

## Status

Proposed 2026-11-08.
