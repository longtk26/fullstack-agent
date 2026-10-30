# Story 15.2 — SVG illustrations from the code engine

**Epic:** [15 — Site images & illustrations](epic15_site_assets.md) · **Requirements:** FR-28 · **Depends on:** 15.1, 13.3

## User story

As a user generating a website, I want the agent to draw the illustrations my pages need, in my theme's colours,
without an extra image service or API key.

## Acceptance criteria

- [x] New frontend-lane node `generate_assets` between `scaffold_frontend` and `generate_frontend`; it is skipped
      (lane step marked skipped, no engine call) when no asset has `source: "generate"` with an SVG kind
      (`illustration`, `pattern`, `logo`, `image`).
- [x] **One engine call** for all generated assets of the job, prompt `generate_assets/v1`, quoting for each asset
      its id, kind, prompt/alt, style, aspect ratio, and the theme's colour **variable names** (`--primary`,
      `--primary-foreground`, `--accent`, `--secondary`, `--muted`, `--foreground`, `--background`) — never hex
      values, so the drawing follows light/dark mode and later theme edits.
- [x] Engine scope: it may write only `src/assets/svg/<id>.svg` for the requested ids; any other change is
      reverted and reported (event `frontend.asset.out_of_scope`).
- [x] Drawing rules in the prompt (enforced by 15.3): `viewBox` matching the aspect ratio, ≤ 30 KB, flat shapes and
      paths, colours only from the variables above plus `currentColor` / `none` / `transparent`, opacity allowed,
      no text (copy belongs in the page), no embedded raster images, fonts, scripts or external references.
- [x] Deterministic conversion after the engine call: each SVG → `src/components/assets/generated/<Name>.tsx`
      (JSX attribute names, `<title>` from `alt`, `role="img"` or `aria-hidden` when decorative, `className`
      passthrough). Converted components and SVG sources are owned files (`.bga/owned.json`), so later engine
      edits are flagged by the `owned-files` convention.
- [x] Cache: key = sha256(prompt version, engine, kind, prompt/alt, style, aspect ratio); results stored under
      `ARTIFACT_ROOT/asset-cache/`. Resume, re-runs and revisions (Epic 16) reuse cached drawings; event
      `frontend.asset.ready { id, cached }` per asset.
- [x] The engine call is a model call in usage and traces under node `generate_assets` (8.2); commit
      `node:generate_assets`.
- [x] Artifacts: SVGs are inside `frontend.zip`; `frontend_manifest.assets[]` lists id, source, file, sha256, cached.
- [x] UI: the Results tab shows an **Assets** gallery (each asset on the theme background, light and dark, with
      source and size).
- [x] Fake engine: golden SVGs for the `static-landing` and `project-tracker-dynamic` assets (listed in
      `docs/development/test-doubles.md`).
- [x] Tests: conversion snapshots (attributes, title, decorative), cache hit/miss, scope enforcement.

**Status:** done (2026-10-30), on `feat/epic15-site-images`.

- Node `generate_assets` (`frontend_assets.py`) between `scaffold_frontend` and `generate_frontend`; skipped when no
  asset is generated. Cache first (`ARTIFACT_ROOT/asset-cache/<key>.svg`, key = sha256 of prompt version, engine, kind,
  prompt, style, aspect ratio), then **one** engine call (`generate_assets/v1`) for the misses, in a scratch
  directory holding only `.bga/assets.json`: only the requested `src/assets/svg/<id>.svg` come back, anything else is
  discarded and reported (`frontend.asset.out_of_scope`). Only drawings that pass the 15.3 checks are cached.
- `svg_assets.svg_to_tsx`: JSX attribute names, `<title>` from `alt` + `role="img"` (or `aria-hidden` when
  decorative), ids prefixed with the asset id, `className` passthrough; it also drops anything the safe rule forbids.
  Drawings, components and the registry are owned files (`.bga/owned.json`); events `frontend.asset.ready
  {id, cached}` / `frontend.asset.missing`; usage and traces through `run_engine`; commit `node:generate_assets`.
- `frontend_manifest.assets[]`: id, source, render, file, sha256, cached (and fallback). The Results tab has an
  **Assets** gallery: each drawing as an `<img>` with the plan's light and dark tokens filled in, its source and size;
  then uploads, links, icons and placeholders. `GET /generations/{id}/files?source=frontend` reads `frontend.zip`.
- Fake engine: golden drawings (`engines/golden/assets/`), `FakeStep.golden_assets` / `unsafe_assets`
  (test-doubles.md). Tests: conversion snapshot, decorative, hostile input dropped, cache miss then hit (no engine
  call), scope, skip.
