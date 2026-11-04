# Story 21.3 — Guard rails for designed pages

**Epic:** [21 — Designed pages](epic21_designed_pages.md) · **Depends on:** 21.2

## User story

As the operator, I want a designed page to be checked and repaired by code before it renders, so that a free tree
cannot bypass the theme, hide content, link nowhere or blow up the build.

## Scope (`frontend_spec/trees.py`)

- `classify`: elements, shadcn primitives, Lucide icons (from the icon index), library sections, data components,
  removed types (`script`, `iframe`, `style`, `form`, `input`, `video`, …), unknown types.
- `check_tree` (the validator's `_check_trees`): node and depth limits (errors), unknown pages (error), unknown
  assets, missing alt, more than one `h1`, palette and arbitrary colours, `fixed`, unknown / removed types
  (warnings), data components' collections and fields on static sites, `Metric` / `Chart` / `RecordForm` /
  `RecordAction` props; page CSS imports, external URLs, `position: fixed`.
- `fix_trees` (run by `autofix_frontend_spec`): unknown wrappers unwrapped (children kept), removed types dropped,
  offending classes stripped (the chrome may stick), foreign image sources → placeholder assets, missing alt → `""`,
  links to unknown pages → home, page CSS scoped (`[data-page="<id>"]`) and cleaned; every change is a note.

## Acceptance criteria

- [x] A tree with palette colours, `fixed`, a script, an unknown wrapper, a foreign image and a dead link renders
      after the fixes, and every fix is noted.
- [x] A tree over the node or depth limit, or with an unknown asset, is an error (the page keeps its sections).
- [x] `sample.json`'s 811-node site passes the rules after the fixes (16 warnings, 36 notes, no errors).

## Status

**Done (2026-11-04)**. Tests: `tests/test_trees.py` (classification, rules, fixes, CSS scoping, collections and
fields of data components). Deviation: the CSS property allowlist is minimal (blocked imports, external and data
URLs, expressions, `position: fixed`); raw colours in CSS are a warning, not stripped, so patterns keep working.
