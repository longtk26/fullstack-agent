# Story 15.3 — Asset checks & placeholder fallback

**Epic:** [15 — Site images & illustrations](epic15_site_assets.md) · **Requirements:** FR-25, FR-28, §8.1 · **Depends on:** 15.2, 13.4

## User story

As the agent, I want every SVG checked before it is built into a site, so that a drawing can never run code,
leak requests or break the theme — and a bad drawing never fails the whole generation.

## Acceptance criteria

- [ ] New frontend check `assets` (stored as `frontend:assets`), pure Python on the files, runs before `build`.
      SVGs are parsed with `defusedxml` (no entity expansion, no external entities). Rules:
  - **safe:** no `script`, `foreignObject`, `iframe`, `image`, `embed`, `object`; no `on*` attributes; `href` /
    `xlink:href` only to `#fragments`; no `url(...)` except `url(#id)`; no `@import`; no `data:` URIs;
  - **valid:** root `<svg>` with a `viewBox` matching the declared aspect ratio (±2 %), ≤ 30 KB, ≤ 2 000 elements;
  - **theme:** fill / stroke / stop colours only `var(--<allowed>)`, `currentColor`, `none`, `transparent`
    (same token rule as the `design-tokens` convention);
  - **accessible:** the converted component has a `<title>` or `aria-hidden` (decorative).
- [ ] Uploaded SVGs (15.4) go through the same rules at upload time, except the theme rule.
- [ ] **Referenced:** after build, every asset used by a section appears on its route (`data-bga-asset="<id>"`;
      static: in `out/**/index.html`; dynamic: asserted by the generated Playwright smoke test). Declared but
      unused assets → warning.
- [ ] Failures go to the repair loop scoped to the failing SVG files (prompt `repair_frontend` with an asset
      section). After `FRONTEND_ASSET_REPAIR_LIMIT` (default 1) failed attempts the asset **falls back to
      `placeholder`** in the registry, the check reports warning `FE_ASSET_FALLBACK`, and the generation ends
      `COMPLETED_WITH_WARNINGS` if nothing else failed. An asset problem never fails the frontend lane.
- [ ] The report and the Assets gallery show which assets fell back and why.
- [ ] Tests with hostile samples: `<script>`, `onload`, external `href`, `data:` image, CSS `url(https://…)`,
      a billion-laughs entity, a 5 MB path, hex colours; each is reported with its rule and file.
