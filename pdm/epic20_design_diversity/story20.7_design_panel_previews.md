# Story 20.7 — Design panel: rendered previews, squint view, concept-driven photos

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-24, FR-18 · **Depends on:** 20.4, 19.3

## User story

As a user reviewing a draft, I want to see each direction as my real home page, side by side, and pick one by how it
looks, not by swatches and a description, so that I choose with confidence; and I want the photos to match the
direction I pick.

## Context

- Review UI: `agent-ui/src/features/specs/components/DesignPanel.tsx` (one card per direction: swatches, palette,
  fonts, preset / radius / hero, home order, avoid list, "Use this direction"), used by
  `features/generations/components/NewGenerationView.tsx`; applying uses `lib/design-direction.ts`
  (`applyDirectionToText`).
- Design Theater: a tool's stated design rationale is often not what it builds, so the preview must be the rendered
  page.
- Rendering without the engine: `scaffold_frontend` + build in `bga-runner-node` (~20–40 s for a static site). The
  preview container for static sites is nginx serving the export (13.5).
- Photos: made at the end of the draft with the selected direction's `photoStyle` (19.3,
  `PHOTO_STYLES_BY_PRESET` in `design_direction.py` and the UI mirror); regenerate endpoint
  `POST /api/v1/spec-drafts/{id}/assets/{assetId}/regenerate`.
- One click (19.10) skips the review; this story changes only the review path.

## Steps

1. **Direction previews.** After a draft succeeds (static and dynamic), a background job renders the home page of each
   of the three directions: apply the card to the draft spec, scaffold, build, screenshot at 1440 × 900 and
   390 × 844 (light, reduced motion) with the same Playwright setup as `design-check.mjs`; store the PNGs as files
   of the draft (`spec_drafts.design.previews`, paths under the draft's storage, cleaned with the draft). Dynamic
   drafts render the home page on mocks. The job does not block the draft or one click; the panel shows "rendering"
   until ready. With the fake engine the job runs too (it uses no engine).
2. **API.** `GET /api/v1/spec-drafts/{id}/design/previews/{index}?size=desktop|mobile` (owner only, others 404)
   returns the image; the draft DTO says which previews exist.
3. **Panel.** The three directions side by side (stacked on narrow screens): the preview image (desktop / mobile
   toggle), the concept line, the tone as five small scales, fonts, palette, hero layout, icon and motion style,
   "gives up", the draft's pick, and "Use this direction". A **squint** toggle shows all previews in greyscale and
   blurred, to compare structure. Applying keeps pages, copy and photos (as today).
4. **Edited specs.** If the user edits the spec after the previews were made, the previews show "may differ from your
   edits" (no re-render on every keystroke); a "Refresh previews" button re-runs the job.
5. **Photo style from the direction.** `photoStyle` comes from the card (concept, tone and key visual: e.g. a
   "darkroom print" concept → "high-contrast black and white, grain, deep shadows") instead of
   `PHOTO_STYLES_BY_PRESET`; the preset table stays the fallback. Same rule in the UI mirror. Switching direction in
   the review does not regenerate photos; it offers "Regenerate photos in this style (N photos, ~$X)" using the
   existing regenerate endpoint (cost from the API, as 19.3).
6. Tests: preview job (fake engine, sandbox-marked: three PNGs written, owner-only endpoint, cleanup with the draft);
   DTO; panel (type check; a component test if the UI has them); photo style from a card (Python and UI on shared
   fixtures); the regenerate offer computes count and cost.

## Acceptance criteria

- [ ] After a draft, each direction's real home page is rendered (desktop and mobile) without an engine call and
      shown in the Design panel; the draft and one click are not delayed by it.
- [ ] The squint view shows the three previews in greyscale for structure comparison.
- [ ] Previews of an edited spec are marked and can be refreshed.
- [ ] Photo style follows the chosen card; switching direction offers to regenerate photos with the count and cost.
- [ ] Owner-only access to previews; previews are deleted with the draft.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint`,
`make up` with the fake engine: draft a spa site in the Requirement tab, see three rendered previews appear, use the
squint view, switch direction, and generate.

## Status
