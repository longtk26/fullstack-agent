# Story 15.4 — Uploaded & linked images

**Epic:** [15 — Site images & illustrations](epic15_site_assets.md) · **Requirements:** FR-28, §8.1 · **Depends on:** 15.1, 13.5, 9.7

## User story

As a user, I want to use my own logo and photos — uploaded or already hosted — in the generated site.

## Acceptance criteria

- [ ] `POST /api/v1/uploads` (multipart, one file): PNG, JPEG, WebP, SVG. Type detected from the content (magic
      bytes / XML root), not the file name. Limits: `UPLOAD_MAX_MB` (default 5) per file, `UPLOAD_QUOTA_MB`
      (default 200) per user; over the limit → 413 with the limit in `details`.
- [ ] Raster images are re-encoded with Pillow (metadata such as EXIF/GPS stripped, longest side ≤ 2 560 px);
      SVGs must pass the 15.3 safety rules. Width, height and sha256 are recorded.
- [ ] Table `uploads` (id `upl_…`, owner, filename, mime, bytes, width, height, sha256, created_at); files under
      `ARTIFACT_ROOT/uploads/<owner>/<id>.<ext>`. `GET /api/v1/uploads`, `GET /api/v1/uploads/{id}/content`,
      `DELETE /api/v1/uploads/{id}`; other users' uploads → 404. Same file uploaded twice → same row (by sha256).
- [ ] Creating a generation checks every `upload:<id>` in the FrontendSpec against the user's uploads
      (`FE_UNKNOWN_UPLOAD`). `scaffold_frontend` copies them to `public/assets/<id>.<ext>` (owned files);
      `AssetImage` renders `<img>` with width and height (no layout shift) and `loading="lazy"` except above the
      fold. `layout.header.logo: "asset:logo"` works with an uploaded logo.
- [ ] Linked images (`https://`): rendered as `<img src>` with `referrerPolicy="no-referrer"`; never fetched by the
      sandbox (it is offline), and tests do not depend on them loading. The generated README lists external
      images.
- [ ] Uploads referenced by a generation are kept as long as its artifacts; unreferenced uploads are deleted after
      `UPLOAD_RETENTION_DAYS` (default 30).
- [ ] UI (FrontendSpec tab, 9.7): an **Assets** panel — drag-and-drop upload, thumbnails, each asset's source, a
      button that sets `source: "upload:<id>"` on an asset or adds a new one.
- [ ] Tests: type sniffing (a `.png` that is really HTML is refused), EXIF stripped, quota, ownership, scaffold
      copies the files, ZIP builds with them.
- [ ] Out of scope: downloading linked images into the project.
