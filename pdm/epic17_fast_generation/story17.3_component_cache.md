# Story 17.3 — Custom components: parallel engine calls & component cache

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30 · **Depends on:** 17.2

## User story

As a user, I want components the catalogue cannot express generated quickly, and a component that was already
generated and tested reused instead of written and tested again.

## Acceptance criteria

- [ ] A custom component (a `components[]` entry used by a section) needs a props schema in the spec; the engine
      gets one call per component with its description, `uses`, props schema and the conventions, and writes one
      file with a default export. Calls run **in parallel** (bounded by a new setting `ENGINE_CONCURRENCY`, default 3), each in
      its own scratch copy of the frontend repo; only the component's file is taken back.
- [ ] Each new component passes **isolated checks** before it is used: typecheck, lint, conventions and a render
      test with sample props generated from its schema. Failing ones go through the normal repair loop; one that
      still fails falls back to the closest catalogue section with a warning (never fails the generation).
- [ ] **Cache key** = sha256 of the canonical JSON of {props schema, `uses`, normalized description, base lock
      sha (`overlay.json` `lockSha256`), overlay version, prompt version}. The component's name is not part of the
      key: cached files are stored as `src/components/custom/<key>.tsx` and the generated registry maps the
      spec's name to them. Engine and model are recorded, not keyed.
- [ ] Only components that passed their isolated checks are stored (`component_cache` table + files under
      `ARTIFACT_ROOT/cache/components/<key>/`, with source generation, engine, hits, last used). A hit copies the
      files, skips the engine call and the isolated checks, and emits `component.cache_hit`; the site-level
      checks (build, routes, smoke) still run.
- [ ] A cached component that breaks the site build is evicted and regenerated once. Changing the base, overlay
      or prompt version makes old entries miss on their own; an admin endpoint purges the cache.
- [ ] Usage (8.x) shows cache hits and the engine time they saved; a report lists the most reused custom
      components as candidates for the catalogue.
- [ ] `shop-dynamic`: 3 engine calls on the first run, 0 on the second.

**Status:** open.
