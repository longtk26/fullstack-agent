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

- [ ] BackendSpec field types `file` and `image` (additive) with `accept` (MIME types) and `maxSize`; the column
      stores the object key; `x-bga.source: upload` (10.0b).
- [ ] An `IObjectStorage` port with an S3 adapter (`boto3`, `endpoint_url` from env; empty endpoint = AWS S3), in
      `src/libs/storage/` and `infrastructure/adapters/`; a `files` module with `POST /files/presign`.
- [ ] Create and update check the key exists with the allowed type and size (use-case pre-check hook); keys are
      scoped to the generation's bucket and a per-entity prefix; with 10.3, to the uploading user.
- [ ] Responses add a signed read URL per file field (`<field>Url`, response-fields hook); expiry from env.
- [ ] Env: `STORAGE_ENDPOINT`, `STORAGE_PUBLIC_ENDPOINT`, `STORAGE_BUCKET`, `STORAGE_REGION`, `STORAGE_ACCESS_KEY`,
      `STORAGE_SECRET_KEY`, `STORAGE_URL_EXPIRE_SECONDS`; `.env.ex` without values.
- [ ] Template tests against a local MinIO: presign, upload, create with the key, wrong type and oversize rejected,
      missing object rejected.

Infrastructure:

- [ ] One shared MinIO container started by the agent worker (like previews), bound to `127.0.0.1`; one bucket per
      generation, created at preview and sandbox start, removed with the generation.
- [ ] Bucket CORS allows the frontend preview's origin to `PUT`.
- [ ] URLs are signed with the **browser-visible** endpoint (`STORAGE_PUBLIC_ENDPOINT`), not the in-network host.

Frontend (dynamic mode):

- [ ] An upload field (drag and drop, progress, image preview, replace and remove) in the 10.0a kit; images show in
      lists and details through the signed URL.
- [ ] MSW answers presign and the `PUT` and keeps the file as a blob URL.

## Status

**Planned (2026-11-04).**
