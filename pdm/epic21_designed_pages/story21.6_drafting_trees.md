# Story 21.6 — Drafting designed pages

**Epic:** [21 — Designed pages](epic21_designed_pages.md) · **Depends on:** 18.10, 20.4, 21.3

## User story

As a user, I want every page of a drafted site designed by the engine from its content and the chosen direction, so
that the first draft already looks like a designed site, not a template.

## Scope

- `prompts/draft_tree/v1.md`: one request per page (and one for the chrome) with the page's content outline (its
  sections), the direction brief (concept, tone, fonts, colours, surfaces, icons, motion), the pages (for links),
  the collections (fields and a sample record) and assets, the allowed node types, the data components and the
  rules the checks enforce; inline mode answers with `{"files": {"trees/<page>.json": {"tree", "css"}}}`, a CLI
  engine writes the file.
- `orchestrator/tree_drafting.py` + the draft flow: after the spec is valid and the direction applied, the pages are
  designed (in parallel on an API engine, `FRONTEND_TREE_CONCURRENCY`), the trees read, repaired by the rules and
  applied; a page whose tree still fails keeps its sections; a dynamic app's BackendSpec gains the operations the
  trees need (21.5); if the draft no longer validates with the trees, every tree is dropped with a note.
- `FRONTEND_TREES` (default true) turns it off for a section-only draft (the comparison of 21.1).
- The fake engine composes trees from the sections (`fake_trees.py`), varied by the seed, so fake drafts and
  `make up` render designed pages.

## Acceptance criteria

- [x] A static draft designs every page; the chrome stays the shell's when the engine writes none.
- [x] A dynamic draft designs its pages and binds every data component to an operation of its contract.
- [x] A broken tree costs only its page; a draft that would not validate keeps its section pages.
- [ ] With a real engine: the designed pages pass the design check and read as designed (21.1 measures this).

## Status

**Done (2026-11-04)** for the flow and the fake engine; the real-engine measurement is 21.1. Tests:
`tests/test_tree_drafting.py` (the prompt, the fake composer, a static and a dynamic draft with trees, broken trees,
the backend completion). The tests keep `FRONTEND_TREES=false` by default (`tests/conftest.py`) so the draft tests'
call counts stay as before; the tree tests opt in.

**Fix (2026-11-04)**, from the first real draft (`1d4ef7a2…`, Gemini API): every `draft_tree` call was refused
before the request ("drafts specs only"), because the API engine's `DRAFT_PURPOSES` lacked `draft_tree`, so all
pages kept their sections. Added, with an end-to-end test of a designed static draft through the mocked API
(`test_gemini_api_engine.py`); the earlier tests drafted trees only with the fake engine.
