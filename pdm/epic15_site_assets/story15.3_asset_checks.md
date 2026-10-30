# Story 15.3 — Asset checks & placeholder fallback

**Epic:** [15 — Site images & illustrations](epic15_site_assets.md) · **Requirements:** FR-25, FR-28, §8.1 · **Depends on:** 15.2, 13.4

## User story

As the agent, I want every SVG checked before it is built into a site, so that a drawing can never run code,
leak requests or break the theme — and a bad drawing never fails the whole generation.

## Acceptance criteria

- [x] New frontend check `assets` (stored as `frontend:assets`), pure Python on the files, runs before `build`.
      SVGs are parsed with `defusedxml` (no entity expansion, no external entities). Rules:
  - **safe:** no `script`, `foreignObject`, `iframe`, `image`, `embed`, `object`; no `on*` attributes; `href` /
    `xlink:href` only to `#fragments`; no `url(...)` except `url(#id)`; no `@import`; no `data:` URIs;
  - **valid:** root `<svg>` with a `viewBox` matching the declared aspect ratio (±2 %), ≤ 30 KB, ≤ 2 000 elements;
  - **theme:** fill / stroke / stop colours only `var(--<allowed>)`, `currentColor`, `none`, `transparent`
    (same token rule as the `design-tokens` convention);
  - **accessible:** the converted component has a `<title>` or `aria-hidden` (decorative).
- [x] Uploaded SVGs (15.4) go through the same rules at upload time, except the theme rule.
- [x] **Referenced:** after build, every asset used by a section appears on its route (`data-bga-asset="<id>"`;
      static: in `out/**/index.html`; dynamic: asserted by the generated Playwright smoke test). Declared but
      unused assets → warning.
- [x] Failures go to the repair loop scoped to the failing SVG files (prompt `repair_frontend` with an asset
      section). After `FRONTEND_ASSET_REPAIR_LIMIT` (default 1) failed attempts the asset **falls back to
      `placeholder`** in the registry, the check reports warning `FE_ASSET_FALLBACK`, and the generation ends
      `COMPLETED_WITH_WARNINGS` if nothing else failed. An asset problem never fails the frontend lane.
- [x] The report and the Assets gallery show which assets fell back and why.
- [x] Tests with hostile samples: `<script>`, `onload`, external `href`, `data:` image, CSS `url(https://…)`,
      a billion-laughs entity, a 5 MB path, hex colours; each is reported with its rule and file.

**Status:** done (2026-10-30), on `feat/epic15-site-images`.

- Check `frontend:assets` (before `build`, also in the static runner): safe, valid, theme and accessible rules on
  every drawing (`svg_assets.check_svg`, defusedxml with DTDs and entities forbidden); `<style>` and animation
  elements are also refused (CSS and `set` can carry what the attribute rules catch). Unused assets and fallbacks
  are warnings (`severity`), never failures.
- Failures carry their file, so they reach the digest and `repair_frontend` (prompt `v2` with an asset section);
  after the repair the drawings are converted again and their owned hashes recorded (`redraw_after_repair`), so the
  17.5 auto-fix does not undo the engine's fix. At the start of `validate_frontend`, a drawing still failing after
  `FRONTEND_ASSET_REPAIR_LIMIT` (1) repairs, or with no repair attempt left, falls back: files removed, registry on the
  placeholder, `fallback` in the plan and manifest, warning `FE_ASSET_FALLBACK`, event `frontend.asset.fallback`, and
  the job ends `COMPLETED_WITH_WARNINGS` ("Images shown as placeholders: …", code `ASSET_FALLBACK`). An asset never
  fails the lane.
- **Referenced:** the generated Playwright smoke test asserts `[data-bga-asset="<id>"]` on every route where the
  asset is always on the page (`visibleRoutes`: section content and static collections, not data states, not inside
  Tabs), in static and dynamic mode alike; it also only looks for visible text now (a drawing's `<title>` repeats its
  caption).
- Tests: twelve hostile samples (script, onload, external href, `data:` image, CSS `url(https://…)` in an attribute
  and in `style`, billion laughs, a 6 MB path, hex and rgb colours, a wrong viewBox, foreignObject), uploads without
  the theme rule, an unsafe drawing repaired then falling back (COMPLETED_WITH_WARNINGS), a repaired drawing used.
- Deviation: "referenced" runs in the smoke test (both modes) instead of reading `out/**/index.html`, so dynamic and
  static share one rule and hidden content (empty states, closed tabs) is not demanded.
