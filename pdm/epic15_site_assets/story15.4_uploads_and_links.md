# Story 15.4 — Uploaded & linked images

**Epic:** [15 — Site images & illustrations](epic15_site_assets.md) · **Requirements:** FR-28, §8.1 · **Depends on:** 15.1, 13.5, 9.7a

## User story

As a user, I want to use my own logo and photos — uploaded or already hosted — in the generated site.

## Acceptance criteria

- [x] `POST /api/v1/uploads` (multipart, one file): PNG, JPEG, WebP, SVG. Type detected from the content (magic
      bytes / XML root), not the file name. Limits: `UPLOAD_MAX_MB` (default 5) per file, `UPLOAD_QUOTA_MB`
      (default 200) per user; over the limit → 413 with the limit in `details`.
- [x] Raster images are re-encoded with Pillow (metadata such as EXIF/GPS stripped, longest side ≤ 2 560 px);
      SVGs must pass the 15.3 safety rules. Width, height and sha256 are recorded.
- [x] Table `uploads` (id `upl_…`, owner, filename, mime, bytes, width, height, sha256, created_at); files under
      `ARTIFACT_ROOT/uploads/<owner>/<id>.<ext>`. `GET /api/v1/uploads`, `GET /api/v1/uploads/{id}/content`,
      `DELETE /api/v1/uploads/{id}`; other users' uploads → 404. Same file uploaded twice → same row (by sha256).
- [x] Creating a generation checks every `upload:<id>` in the FrontendSpec against the user's uploads
      (`FE_UNKNOWN_UPLOAD`). `scaffold_frontend` copies them to `public/assets/<id>.<ext>` (owned files);
      `AssetImage` renders `<img>` with width and height (no layout shift) and `loading="lazy"` except above the
      fold. `layout.header.logo: "asset:logo"` works with an uploaded logo.
- [x] Linked images (`https://`): rendered as `<img src>` with `referrerPolicy="no-referrer"`; never fetched by the
      sandbox (it is offline), and tests do not depend on them loading. The generated README lists external
      images.
- [x] Uploads referenced by a generation are kept as long as its artifacts; unreferenced uploads are deleted after
      `UPLOAD_RETENTION_DAYS` (default 30).
- [x] UI (FrontendSpec tab, 9.7a): an **Assets** panel — drag-and-drop upload, thumbnails, each asset's source, a
      button that sets `source: "upload:<id>"` on an asset or adds a new one.
- [x] Tests: type sniffing (a `.png` that is really HTML is refused), EXIF stripped, quota, ownership, scaffold
      copies the files, ZIP builds with them.
- [x] Out of scope: downloading linked images into the project.

**Status:** done (2026-10-30), on `feat/epic15-site-images`.

- `uploads` module: `POST /api/v1/uploads` (multipart; PNG, JPEG, WebP, SVG sniffed from the content), `GET`,
  `GET /{id}/content` (served with `Content-Security-Policy: default-src 'none'` and `nosniff`), `DELETE`; other users'
  uploads → 404. Limits `UPLOAD_MAX_MB` (5) and `UPLOAD_QUOTA_MB` (200) → 413 with the limit in `details`. Pillow
  re-encodes rasters (orientation applied, EXIF/GPS dropped, ≤ 2 560 px, decompression-bomb guard); SVGs must pass
  the 15.3 rules without the theme rule. The same content again returns the same upload (200). Table `uploads`
  (migration `a1c5e9f3b7d2`), files under `UPLOAD_ROOT/<owner>/<id>.<ext>`.
- Creating a generation refuses `upload:<id>` assets that are not the user's (422, `FE_UNKNOWN_UPLOAD` per asset).
  `scaffold_frontend` copies them to `public/assets/<asset id>.<ext>` (owned) with width, height and sha256 into the
  registry; `AssetImage` renders `<img>` with width and height, `loading="lazy"` except the hero and the logo;
  `layout.header.logo` is shown in both shells. Links render with `referrerPolicy="no-referrer"`, are never fetched,
  and the generated README lists them. The worker prunes uploads older than `UPLOAD_RETENTION_DAYS` (30) that no saved
  FrontendSpec names.
- UI: an **Images** card next to the FrontendSpec editor: drag-and-drop or pick files, thumbnails, size and quota,
  "Use for…" an existing asset (`source: "upload:<id>"`) or a new asset, delete.
- Verification (`make up`, fake engine): static landing with an uploaded logo (header) and photo (work page) plus the
  two drawings: COMPLETED in 33 s, every frontend check passed, the preview serves `/assets/logo.png` and
  `/assets/work-2.jpg`; the downloaded `frontend.zip` installs offline and builds on its own with them. Dynamic tracker
  with the uploaded logo: COMPLETED, the preview shows the logo. Browser: the Assets gallery and the Images panel.
- Deviations: uploads live under `UPLOAD_ROOT` (`.data/uploads`, mounted read-write in the API and the worker), not
  `ARTIFACT_ROOT/uploads`: the API mounts the artifacts read-only. Dedupe uses the sha256 of the uploaded bytes.
- Found and fixed on the way: the static preview's nginx sent absolute redirects with its container port
  (`/work` → `localhost:8080/work/`), now `absolute_redirect off`; the Results tab of a static generation crashed
  (`manifest.api` read for a manifest without a backend).
