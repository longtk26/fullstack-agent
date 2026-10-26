# Epic 7 — Artifacts & preview container

## Overview

Package everything a human or the future Integration Agent needs (ZIP, OpenAPI, manifest, report), serve it
through authenticated artifact APIs, and, as you asked, **start each successfully generated backend as its own
long-running Docker container** that clients and the UI's API explorer can call.

**Requirements:** §3.5, FR-14, FR-16, FR-17, NFR 8.1 ("no auto deploy to production": previews are local-only)

## Preview topology

```
 host 127.0.0.1:18000-18099 ──▶ bga-preview-<gen>  (image bga-gen-<gen>:latest built from backend.zip)
                         │  env: DB_URL, JWT_SECRET (derived per preview), CORS_ORIGINS=<UI origin>, SEED_FILE
                         ▼  network bga-preview-net-<gen>
                       bga-preview-db-<gen>  postgres:18, volume bga-preview-db-<gen> (kept until the preview is deleted)
```

## Stories

| # | Story | Depends on |
|---|---|---|
| 7.1 | [Artifact packaging & manifest (`package_artifacts`)](story7.1_package_artifacts.md) | 6.2 |
| 7.2 | [Artifact API](story7.2_artifact_api.md) | 7.1 |
| 7.3 | [Preview container deployment](story7.3_preview_deployment.md) | 7.1, 6.1 |
| 7.4 | [Preview lifecycle management](story7.4_preview_lifecycle.md) | 7.3 |

## Epic acceptance

- After COMPLETED: `backend.zip`, `openapi.json`, `manifest.json` and `report.json` are downloadable, and
  `curl http://localhost:<port>/tasks` works against the running preview container (routes use the spec's paths).
- Unzipping `backend.zip` and following its README starts the backend on its own (DoD §10 step 13).

**Status (2026-10-26):** all four stories done; acceptance verified on `make up` with the fake engine (see 7.3 and
7.4). The ZIP-starts-on-its-own check is covered by every preview, whose image is built from `backend.zip` alone.
