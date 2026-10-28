# Story 16.2 — Spec edits: theme, content & assets

**Epic:** [16 — Site revisions & feedback](epic16_site_revisions.md) · **Requirements:** FR-29 · **Depends on:** 16.1, 15.1

## User story

As a user, I want to change my site's colours, fonts and texts and see the result live, quickly and without paying
for an engine call.

## Acceptance criteria

- [ ] `kind: "spec"` takes a JSON Patch limited to: `/theme/**`; `/content/**`; `/assets/*` (`source`, `alt`,
      `prompt`, `style`, `decorative`); `/layout/header/**` and `/layout/footer/**` (logo, texts, navigation labels and links to existing pages);
      `/pages/*/title`, `/pages/*/seo/**`, `/pages/*/sections/*/content/**`. Other paths → 400
      `REVISION_PATCH_NOT_ALLOWED` with the allowed list (structural changes need feedback, 16.3, or a new
      generation).
- [ ] With the section renderer (17.2), the allow-list also covers page structure: `/pages/*/sections/**` (add,
      remove, reorder and nest catalogue sections, switch a section to another catalogue component). Pages and
      routes stay fixed.
- [ ] The patched spec is validated (12.1; 12.5 in dynamic mode) before the job is queued: errors → 422; warnings
      such as `FE_LOW_CONTRAST` are returned for the UI to show.
- [ ] `apply_revision` recomputes the plan (routes and components must stay equal, otherwise rejected) and
      regenerates only the affected owned files with the scaffold's code: `globals.css`, `src/content/*.json`,
      `src/config/site.ts`, the asset registry; no engine call. Changing a generated asset's prompt or style
      redraws only that asset (15.2, cache).
- [ ] Fast validation: install skipped when the lock file is unchanged; with the renderer (17.2) no code changes,
      so a spec-only revision runs build, routes and tests only. Target: under 2 minutes for a theme change on `static-landing`.
- [ ] UI **theme editor** on the generation page: preset, colour pickers for the tokens, fonts, radius, light/dark,
      with contrast warnings. Changes show **live** in the preview before saving (the agent UI sends the CSS
      variables to the preview through the inspector channel, 16.4); **Save** creates the revision.
- [ ] UI **content editor**: section texts and page titles in a form generated from the spec.
- [ ] Tests: patch path allow-list; theme patch regenerates only `globals.css`; content patch only the content JSON;
      a patch that changes routes is rejected.
