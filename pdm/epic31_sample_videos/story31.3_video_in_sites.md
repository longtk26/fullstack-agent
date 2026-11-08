# Story 31.3 — Videos in static sites

**Epic:** [31 — Sample videos](epic31_sample_videos.md) · **Requirements:** FR-45, FR-33 · **Depends on:** 31.1, 31.2

## User story

As a user whose site is about something people watch, or whose site would gain from a moving first screen, I want the
drafted site to show real videos in fitting places, credited, light to load and easy to pause, so that the site feels
real without me uploading videos.

## Context

- `AssetKind` includes `video`; the validator only accepts uploaded videos; the section library has no video section;
  hero layouts (Epic 20) take an image or a drawing; trees refuse `video` / `iframe` (`frontend_spec/trees.py`).
- Epic 27: a photo asset becomes a hotlinked URL plus `credit` (`images/stock.stock_site_photos`); `Asset.credit` is
  code-only. Motion presets and reduced motion: Epic 20's `theme.motion`, `MotionRoot.tsx`.

## Steps

1. **Asset:** `kind: "video"` assets gain `source: "youtube"` (`id`, `title`, `poster`) and `source: "pexels"` (`url` of
   the chosen file, `poster`, `width`, `height`, `duration`), each with `credit`; these fields are code-only and left
   out of the drafting schemas. The draft writes `source: "search"` with a `query`, a `place` (`watch` or `background`)
   and an optional `duration`; `stock_site_videos` resolves it through the providers in the place's order (the epic's
   table). With no result the asset becomes a placeholder, a section that needs it is dropped and a hero falls back to
   its image, each with a note.
2. **`Video` section** (section library, typed props in `section_props.py`): one featured video with a heading and a
   short text, or a grid of two to six videos with titles; variants follow the theme tokens; added to the catalogue
   and the drafting prompt as "only when the requirement has something to watch".
3. **YouTube facade** (`components/assets/VideoEmbed.tsx` in the overlay): the poster with a play button, the title and
   the credit; on click it swaps in the `youtube-nocookie.com/embed/<id>?autoplay=1` iframe with a title, an `allow`
   list and `referrerpolicy`; keyboard operable; no YouTube request before the click. Without JavaScript it is a link
   to the video.
4. **Pexels in a `Video` section:** a native `<video controls preload="metadata">` with the poster and the credit.
5. **Hero background video** (`components/assets/BackgroundVideo.tsx`): a `background` option on the hero layouts that
   put text over media; `<video muted loop playsinline autoplay>` with the poster shown first, a visible pause / play
   button, a scrim that keeps the hero text at AA contrast on the worst frame (checked on sampled frames by the design
   check), paused and showing the poster under `prefers-reduced-motion` and when the browser asks to save data (D9);
   the credit in the hero's corner. Only Pexels files are used here.
6. **Trees:** a tree may use the library's `VideoEmbed` or `BackgroundVideo` as a data component bound to a video
   asset; raw `iframe` / `video` stay refused (D8).
7. **Credits:** the README lists each video (title or description, author or channel, link); the design checklist
   gains the facade's and the background video's rules.
8. Tests: resolution with both recorded responders (order per place, fallback to the other provider, both empty); the
   section's and the hero's props; the renderer's output; the tree rule; static golden snapshots unchanged for sites
   without videos.

## Acceptance criteria

- [ ] A static draft of a requirement about something to watch shows real embedded videos with credits; a draft whose
      hero suits motion gets a background video that can be paused and stays still under reduced motion.
- [ ] No YouTube request happens before a user clicks play.
- [ ] Without the providers the site builds as today.
- [ ] `make design-check-fixture` passes with the `Video` section and a background-video hero (`--motion`).

## Verify

`make test`, `make design-check-fixture ARGS="--motion"`, `make up` with one static draft.

## Status

Proposed 2026-11-08.
