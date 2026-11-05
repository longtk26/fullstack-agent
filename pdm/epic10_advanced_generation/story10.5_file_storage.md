# Story 10.5 — File storage (MinIO, signed URLs)

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-34 · **Depends on:** 10.1

## User story

As a user of a generated app, I want to attach files and images to records (a product photo, a receipt), uploaded
straight to object storage, so the backend never streams file bytes; as a developer, I want to move to S3 by
changing env vars only.

## Design

```
browser ── POST /files/presign {filename, contentType, size} ──▶ backend   (checks type and size)
        ◀── {uploadUrl, key, expiresAt} ───────────────────────
browser ── PUT uploadUrl (file bytes) ─────────────────────────▶ MinIO
browser ── POST /products {…, photo: key} ─────────────────────▶ backend   (HEAD key: exists, right type and size)
        ◀── {…, photo: key, photoUrl: <signed GET>} ────────────
```

## Acceptance criteria

Backend (the `storage` plugin):

- [x] BackendSpec field types `file` and `image` (additive) with `accept` (MIME types) and `maxSize`; the column
      stores the object key; `x-bga.source: upload` (10.0b).
- [x] An `IObjectStorage` port with an S3 adapter (`boto3`, `endpoint_url` from env; empty endpoint = AWS S3), in
      `src/libs/storage/` and `infrastructure/adapters/`; a `files` module with `POST /files/presign`.
- [x] Create and update check the key exists with the allowed type and size (use-case pre-check hook); keys are
      scoped to the generation's bucket and a per-entity prefix; with 10.3, to the uploading user.
- [x] Responses add a signed read URL per file field (`<field>Url`, response-fields hook); expiry from env.
- [x] Env: `STORAGE_ENDPOINT`, `STORAGE_PUBLIC_ENDPOINT`, `STORAGE_BUCKET`, `STORAGE_REGION`, `STORAGE_ACCESS_KEY`,
      `STORAGE_SECRET_KEY`, `STORAGE_URL_EXPIRE_SECONDS`; `.env.ex` without values.
- [x] Template tests against a local MinIO: presign, upload, create with the key, wrong type and oversize rejected,
      missing object rejected.

Infrastructure:

- [x] One shared MinIO container started by the agent worker (like previews), bound to `127.0.0.1`; one bucket per
      generation, created at preview and sandbox start, removed with the generation.
- [x] Bucket CORS allows the frontend preview's origin to `PUT`.
- [x] URLs are signed with the **browser-visible** endpoint (`STORAGE_PUBLIC_ENDPOINT`), not the in-network host.

The upload field and its mocks are in [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md).

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`.

- **Spec**: field types `file` and `image` (additive) with `accept` (MIME types, `image/*` allowed) and `maxSize`
  (bytes; defaults: images png/jpeg/webp/gif up to 5 MB, files any type up to 10 MB). The planner makes them
  `VARCHAR(512)` string columns that hold the object key and carry `column.file` (kind, accept, maxSize, prefix
  `<entity>/<field>`); a key never becomes a record's label.
- **The `storage` plugin** (`orchestrator/plugins/storage.py`, `templates/plugins/storage`, `boto3==1.40.0`, baked
  into the runner): `src/libs/storage/` (the `IObjectStorage` port, the `S3ObjectStorage` adapter, `ObjectStorageDep`,
  `signed_url`, `check_upload` / `check_declared` / `new_key`, a generated `catalog.py` of `FILE_RULES`); its own
  `files` module with `POST /files/presign` (`{entity, field, contentType, size, filename}` → `{key, uploadUrl,
  method, headers, expiresIn}`; signed in with 10.2, keys under the caller's folder). Create and update check a sent
  key (pre-check hook): under the field's prefix (the caller's folder when the record has an owner, 10.3), uploaded,
  an allowed type, not too large: 400 `FILE_NOT_FOUND`, 422 `FILE_TYPE_NOT_ALLOWED` / `FILE_TOO_LARGE` with the field.
  Responses add `<field>Url`, a signed read URL (response-fields hook). At startup the app creates its bucket and its
  CORS rule for `CORS_ORIGINS` (app-startup hook; an unreachable store is logged, not fatal).
- **Env**: `STORAGE_ENDPOINT` (empty: AWS S3), `STORAGE_PUBLIC_ENDPOINT` (what browsers reach; URLs are signed for
  it), `STORAGE_BUCKET`, `STORAGE_REGION`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_URL_EXPIRE_SECONDS`;
  `.env.ex` lists them without values.
- **Template tests**: the plugin's presign, upload with `httpx` and read back through the signed URL, wrong type,
  too large, unknown field; per create operation a key never uploaded, an uploaded file of the wrong type and one too
  large. Generated payloads put a real object in the bucket (`tests/storage.py: uploaded(...)`), and the generic
  update test does not pick a file field.
- **Contract**: request properties `x-bga.source: upload` with the presign operation, accept and maxSize; responses'
  `<field>Url`; `x-bga.entities[...].fileFields`; `files.presign` with its errors and scenarios (success, wrong type,
  too large, unknown field); a "<field> not uploaded" scenario per create; fixtures hold keys under the prefix, and
  `x-bga.storage.objects` lists them so the smoke check uploads each first (through the app's own storage library).
- **Infrastructure**: one shared store `bga-storage` (`src/sandbox/object_store.py`), started on first use by the
  worker or a test run, API on `127.0.0.1:9100`, data in the `bga-storage-data` volume, root credentials derived
  from `JWT_SECRET` and read back from the running container (so the worker and test runs share it). It joins a
  sandbox's internal network (when the project has `src/libs/storage`) or a preview's network as `storage`, and
  leaves it before the network is removed; one bucket per sandbox (`bga-sbx-<gen>`) and preview (`bga-preview-<gen>`),
  removed with them by a one-shot runner container on `bga-storage-net`; dropping preview data empties the bucket.
- **Fixed on the way**: the conventions check expected every module to have a repository (the `files` module has
  none).

**Deviations:**

- The store is **RustFS** (`rustfs/rustfs:1.0.1`, S3-compatible, MinIO-like), not MinIO: MinIO's community images are
  no longer published (Docker Hub: repository gone; quay.io: login required). The generated app speaks plain S3, so
  MinIO, AWS S3 or any S3-compatible server works by env alone.
- The bucket and its CORS rule are created by the app at startup rather than by the worker; one rule per bucket,
  from the app's `CORS_ORIGINS`.
- Root credentials are shared by every bucket (local previews and sandboxes only); a per-bucket user is not created.
- Previews seed the fixtures' keys, but not the objects themselves: their URLs answer 404 until something is
  uploaded (the smoke check does upload them). Placeholder files for previews belong with 22.7's upload field.

**Verified:** `make lint`; `tests/test_storage.py` (6); `make test` (all pass after the schema digest update);
`BGA_SANDBOX_TESTS=1` for a storage generation through the workflow, open and signed in
(`test_a_backend_with_file_fields_passes_its_tests_and_scenarios[open|signed-in]`): every check passes on the first
try (open: 41 template tests including presign, upload and read against the store, 25 scenarios); the store leaves
the job network and the sandbox buckets are gone afterwards. `make up`, then a fake-engine backend generation of the
storage spec (`gen_01M6N5F0V2PS3ME692ABG93HWB`): on its preview a presign answers a URL on `localhost:9100`, a PUT
from this machine uploads, a task created with the key returns `attachmentUrl`, which reads the same bytes; a PNG
for the PDF field is `FILE_TYPE_NOT_ALLOWED`, 2 MB is `FILE_TOO_LARGE`, a key never uploaded is 400
`FILE_NOT_FOUND`, and the browser preflight from `http://localhost:3100` is allowed.
