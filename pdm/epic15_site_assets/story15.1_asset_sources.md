# Story 15.1 — Asset sources in the FrontendSpec

**Epic:** [15 — Site images & illustrations](epic15_site_assets.md) · **Requirements:** FR-22, FR-28 · **Depends on:** 12.1, 13.1

## User story

As a user writing a FrontendSpec, I want to say for each image whether it should be drawn for me, uploaded,
linked or left as a placeholder, so that the generated site has real pictures where I need them.

## Example

```json
"assets": [
  { "id": "hero", "kind": "illustration", "source": "generate",
    "alt": "Designer's desk with sketches and a coffee cup", "style": "flat, geometric, two-tone",
    "aspectRatio": "16:9" },
  { "id": "logo", "kind": "logo", "source": "upload:upl_01J…", "alt": "Northwind Studio" },
  { "id": "dots", "kind": "pattern", "source": "generate", "decorative": true },
  { "id": "mail", "kind": "icon", "source": "lucide:Mail", "decorative": true },
  { "id": "office", "kind": "image", "source": "https://cdn.example.com/office.jpg", "alt": "Our office" }
]
```

## Acceptance criteria

- [x] `Asset` gains (all optional, additive — `specVersion` stays `"1.0"` and existing specs validate unchanged):
  - `source`: `placeholder` (default) | `generate` | `upload:<uploadId>` | `lucide:<IconName>` | an `https://` URL;
  - `kind` adds `illustration`, `pattern`, `logo` (keeps `image`, `icon`, `video`, `file`);
  - `prompt` (what to draw; defaults to `alt`), `style` (free text, ≤ 200 chars), `aspectRatio`
    (`16:9` | `4:3` | `1:1` | `3:4` | `21:9`; default per kind), `decorative` (no alt needed, rendered `aria-hidden`).
- [x] New issue codes: `FE_ASSET_ALT_REQUIRED` (non-decorative asset without `alt`), `FE_INSECURE_URL` (`http://`
      or another scheme), `FE_UNKNOWN_ICON` (name not exported by the base's `lucide-react`),
      `FE_UNSUPPORTED_ASSET_SOURCE` (`generate` on `video` / `file`); warning `FE_TOO_MANY_GENERATED_ASSETS`
      (more than `FRONTEND_MAX_GENERATED_ASSETS`, default 12). `upload:` ids are checked against the user's uploads
      when the generation is created (`FE_UNKNOWN_UPLOAD`, 15.4).
- [x] JSON Schema regenerated (`make schema`); the UI editor picks it up.
- [x] The planner adds `assets[]` to the frontend plan: id, source, render mode (`svg-component` | `public-file` |
      `remote` | `icon` | `placeholder`), target file, the routes that use it; snapshots updated.
- [x] Codegen (owned files): `src/assets/index.ts` (registry: id → render mode, alt, decorative, aspect ratio) and
      `src/components/assets/AssetImage.tsx`, which renders each mode and sets `data-bga-asset="<id>"`. Pages keep
      writing `<AssetImage asset="asset:hero" />`; the golden frontends drop their own `AssetImage`.
- [x] Examples: `static-landing` uses `generate` for the hero and work images and keeps one placeholder;
      `project-tracker-dynamic` adds a `generate` empty-state illustration.
- [x] Tests: schema and validator cases for every new code; planner snapshot; registry codegen snapshot.

**Status:** done (2026-10-30), on `feat/epic15-site-images`.

- `Asset` gains `source` (placeholder, generate, `upload:<id>`, `lucide:<Icon>`, `https://`), kinds `illustration`,
  `pattern`, `logo`, and `prompt`, `style`, `aspectRatio`, `decorative` (`frontend_spec/assets.py`: source kinds,
  render modes, default ratio per kind). Existing specs validate unchanged.
- Codes: `FE_ASSET_ALT_REQUIRED`, `FE_INSECURE_URL` (`http://`, `data:` and any other scheme),
  `FE_UNKNOWN_ICON` (names from the base's lucide-react 1.62, `templates/nextjs_base/lucide-icons.txt`, written by
  `scripts/frontend-base.sh`), `FE_UNSUPPORTED_ASSET_SOURCE` (generate on video, file and icon; unknown sources),
  `FE_TOO_MANY_GENERATED_ASSETS` (warning above 12), `FE_UNKNOWN_UPLOAD` (malformed id here; ownership at creation,
  15.4).
- The plan lists each asset with `render` (`svg-component` / `public-file` / `remote` / `icon` / `placeholder`), its
  files, `routes` and `visibleRoutes` (15.3). Codegen writes `src/assets/index.ts` (`asset_registry.py`); the overlay
  has `src/components/assets/AssetImage.tsx` (every mode, `data-bga-asset`); the library's `sections/AssetImage`
  re-exports it and the corner-shop golden dropped its own.
- Examples: `static-landing` draws `hero` and `work-1`, keeps `work-2` as a placeholder; `project-tracker-dynamic`
  draws an `empty-projects` illustration, shown through the new optional `states.emptyImage`.
- Deviations: `make schema` only exports the BackendSpec; the FrontendSpec schema is served live by the API, so the
  editor picks the new fields up without a regeneration. The validator's limit of 12 generated assets is a domain
  constant (`MAX_GENERATED_ASSETS`); `FRONTEND_MAX_GENERATED_ASSETS` exists in the config but the validator does not
  read it.
