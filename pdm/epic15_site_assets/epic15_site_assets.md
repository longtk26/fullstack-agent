# Epic 15 — Site images & illustrations

## Overview

Today every FrontendSpec asset renders as a **placeholder**: a themed gradient panel with the alt text as its
accessible label. This epic gives static sites and dynamic apps real images without requiring a new provider or
API key:

| Source | Good for | Key / cost |
|---|---|---|
| **`generate`** — SVG drawn by the code engine (Claude Code / Antigravity) | hero illustrations, empty states, backgrounds, patterns, simple logos | none beyond the engine call (recorded in usage) |
| **`upload:<id>`** — a file the user uploads | photos, the real logo, team pictures | none |
| **`https://…`** — a link | images already hosted on a CDN | none |
| **`placeholder`** — today's panel | drafts | none |
| `generate` + `kind: "photo"` — raster image from an image API (optional, 15.5) | photo-like pictures | provider key, cost per image, opt-in |

Generated SVGs use the **theme's colour variables** (`var(--primary)`, `var(--accent)`, …), never hex values, so
they follow light/dark mode and recolour when the theme changes (Epic 16) without being drawn again. They are
code: committed in the frontend repository, diffable, and checked for safety before they are built.

Icons are not generated: the base already ships `lucide-react` (`source: "lucide:<Name>"`).

**Requirements:** FR-28 (site assets) — requirements v1.3

```
 FrontendSpec.assets[]
   source "generate"     ─▶ generate_assets (one batched engine call) ─▶ src/assets/svg/<id>.svg
   source "upload:<id>"  ─▶ copied from the upload store ───────────────▶ public/assets/<id>.<ext>
   source "https://…"    ─▶ rendered as a remote <img>
   source "lucide:<Name>"─▶ lucide-react icon
   source "placeholder"  ─▶ themed panel (today)
                                     │
     codegen (deterministic, owned): asset registry + <AssetImage> + one TSX component per SVG
                                     │
     frontend:assets check: safe · valid · theme colours · accessible · referenced
                                     └── still failing after repair ─▶ that asset falls back to placeholder,
                                                                       COMPLETED_WITH_WARNINGS
```

Frontend lane after this epic: `plan_frontend → scaffold_frontend → generate_assets → generate_frontend →
validate_frontend ⇄ repair_frontend`.

## Stories

| # | Story | Depends on |
|---|---|---|
| 15.1 | [Asset sources in the FrontendSpec](story15.1_asset_sources.md) | 12.1, 13.1 |
| 15.2 | [SVG illustrations from the code engine](story15.2_svg_illustrations.md) | 15.1, 13.3 |
| 15.3 | [Asset checks & placeholder fallback](story15.3_asset_checks.md) | 15.2, 13.4 |
| 15.4 | [Uploaded & linked images](story15.4_uploads_and_links.md) | 15.1, 13.5, 9.7a |
| 15.5 | [AI raster images (optional)](story15.5_raster_images.md) | 15.3, 8.2 |

## Epic acceptance

- `examples/frontend-specs/static-landing.json` with its hero and work images set to `generate` → with the fake
  engine, the static site shows the golden SVG illustrations instead of panels, in the theme's colours in light
  and dark mode; `frontend:assets` passed; the frontend manifest lists each asset with its file and hash.
- An unsafe SVG (a fake-engine variant with `<script>` and an external `href`) is caught by `frontend:assets`,
  repaired, or replaced by the placeholder with the generation ending `COMPLETED_WITH_WARNINGS`.
- An uploaded logo and photo appear in the static export and in the dynamic preview, and the downloaded ZIP
  builds on its own with them.
- Stories 15.1–15.4 need no new API key.

## Status (2026-10-30)

15.1–15.4 done on `feat/epic15-site-images`; 15.5 (raster images from an image API) not started, only if asked. Epic
acceptance on `make up` with the fake engine: the static landing shows the golden drawings in the theme's colours,
`frontend:assets` passed, the manifest lists each asset with its file and hash; an unsafe drawing (fake
`unsafe_assets`) is caught, repaired or replaced by its placeholder with `COMPLETED_WITH_WARNINGS` (tests); an uploaded
logo and photo are in the static export, the dynamic preview shows the logo, and the ZIP builds on its own. No new API
key.

Drafts draw their images (2026-10-30, after review): a drafted site has no placeholders. `draft_frontend_spec@v3` asks
the engine for `source: "generate"` with a prompt for every image (an editorial illustration when the requirement asks
for photography), and `drafting.draw_images` turns any placeholder it still left into a drawing (prompt from the alt
text, style from the chosen direction), up to the limit of 12, noted in the assumptions. Hand-written specs keep an
explicit `placeholder`; a drawing that fails its checks after the repair still shows its placeholder.
