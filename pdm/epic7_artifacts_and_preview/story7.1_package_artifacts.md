# Story 7.1 — Artifact packaging & manifest (`package_artifacts`)

**Epic:** [7 — Artifacts & preview](epic7_artifacts_and_preview.md) · **Requirements:** FR-16, FR-17 · **Depends on:** 6.2

## User story

As a consumer (human or Integration Agent), I want standardized artifacts with a manifest, so that I can use
the backend without reading its source.

## Acceptance criteria

- [x] Artifacts written to `$ARTIFACT_ROOT/<gen>/` and registered in `artifacts` (sha256, size):
  - `backend.zip`: project without `.venv`, `__pycache__`, `.git`, `.bga/` internals, `.env`, or the engine skill and
    context copies (`.claude/skills/`, Antigravity equivalents). The template's `CLAUDE.md` is kept. Deterministic file order and mtimes.
  - `openapi.json`: exported in 6.2 (the implemented API, not the plan).
  - `manifest.json`: see below.
  - `report.json` + `report.md`: per-check results, durations, repair history, engine usage and cost totals.
  - `plan.json`, `spec.json` (original), `repair-<n>.patch` (already produced earlier, linked here).
- [x] `manifest.json` (versioned `manifestVersion: "1.0"`):
      `{generationId, generatorVersion, templateRef, architecture: "fastapi-skills-hexagonal", specVersion,
        framework: "fastapi", engine, createdAt,
        api: {openapiArtifactId, basePath: "/api/v1"},
        operations: [{operationId, method, path, auth: none|jwt, policy?, requestSchema?, responseSchema, statusCodes[]}],
        auth: {type, loginOperationId?, registerOperationId?, tokenType: "bearer"}?,
        env: [{name, required, secret, description}],
        artifacts: {source, openapi, manifest, report},
        validation: {syntax, lint, deps, startup, migration, conventions, tests, openapi},
        modules: [{name, entity, path}],
        frontendBindings: [...]?  (from 2.5, when the spec was imported from a site JSON),
        unresolved: [{specPath, reason}], assumptions: [...]}`
- [x] Manifest `operations` are derived from the exported OpenAPI (source of truth) and cross-checked with the spec.
- [x] Idempotent: re-running the node overwrites the same files with identical hashes.
- [x] Sets status COMPLETED and emits `artifact.created` events.

**Status (2026-10-26):** done (`src/orchestrator/packaging.py`, `nodes.package_artifacts`). Deviations and notes:
- `backend.zip` has no top-level folder; our `bga-conventions` section is stripped from `CLAUDE.md`/`AGENTS.md`
  (the file is dropped when nothing else is left). ZIP entries use fixed mtimes and modes, so the bytes are
  reproducible; artifact ids are reused per name, so re-packaging gives identical hashes (tested).
- `api.basePath` is `""`: generated routes are mounted at the spec's paths (`/tasks`, not `/api/v1/tasks`).
- Extra fields: `overlayVersion`, `project`, `contractProblems` (the 6.2 parity result; empty when COMPLETED) and
  `api.source` = `openapi` or `plan` (sandbox disabled → no exported OpenAPI, operations come from the plan).
- `env[]` comes from the generated `.env.ex` (comments = descriptions) and the generated config (fields without
  a default = required).
- New artifact `seed.json` (spec `seed[]` → `scripts/seed.py` format, missing ids/timestamps filled
  deterministically) feeds the preview (7.3). `validation-<n>.json` reports are artifacts too.
- The generated app now logs one JSON line per request (`src/libs/middlewares/access_log.py`, overlay v2) for
  the preview request log (7.3).
