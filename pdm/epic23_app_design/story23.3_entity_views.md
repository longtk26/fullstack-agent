# Story 23.3 — Field roles and entity views

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-36 · **Depends on:** 23.2

## User story

As a user of a generated app, I want records shown the way the product needs: videos as a grid of thumbnails with
title, channel and views, posts as a feed, people as profiles, and invoices as a table.

## Context

- `AppList.tsx` has two views (`table`, `cards` from the outline's `listStyle`); `AppDetail.tsx` one.
- A card doesn't know which field is the image, the title or the price: the outline has `list_fields` and
  `display_field` only.

## Steps

1. **Field roles** in the outline's entity (`AppEntity.roles`, optional): `media`, `title`, `subtitle`, `meta`
   (up to 3), `badge`, `stat`, `price`, `avatar`. Code checks each against the BackendSpec field type (`media` and
   `avatar` an image or file field, `price` a money or number field with a currency, `badge` an enum or a status,
   `stat` a number) and fills missing roles from the types (the display field is the title, the first image is the
   media). A role that doesn't fit is dropped with a note.
2. **List views** (`AppEntity.view`, replaces `list_style`; `cards` stays accepted): `table` (today; a `media`
   field becomes a thumbnail column), `cards` (today, laid out by role), `media-grid` (16:9 or square media, title,
   meta line, badge on the media), `feed` (one column, avatar and subtitle, media below, stats row). Each view is a
   presentation of the same `AppList` section: same operation, parameters, paging, row actions and
   `allowedActions`.
3. **Detail views** (`AppEntity.detail_view`): `record` (today), `media` (large media on top, title and meta, actions,
   then fields and child tabs), `profile` (avatar, name, stats, child tabs).
4. **Planner.** `screens.py` copies the view and roles into the section's content (`content.view`,
   `content.roles`); bindings unchanged. Default view per archetype when the outline names none.
5. **Kit.** The views, each with skeleton loading, empty and error states, paging ("Load more" for `feed` and
   `media-grid`, pages for `table`), keyboard focus on cards, and images through the signed read URL (22.7) with a
   placeholder when none.
6. Tests: role checks and filling per field type, planner output with views (bindings byte for byte as before),
   kit render tests per view, snapshots.

## Acceptance criteria

- [x] The news feed shows posts as a feed, the video library as a media grid, the project tracker as a table,
      each from the same `AppList` binding as before (pair check: 0 issues).
- [x] A role on a field of the wrong type is dropped with a note; missing roles are filled from the types.
- [x] Row actions, role filtering and `allowedActions` work the same in every view.
- [ ] No design-check failures for any view at 375 / 1440 px, light / dark; images without a value show a
      placeholder, not a broken image.
- [x] Static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make design-check-app`, the app walk on the news feed
and the video library, `make app-design-report`.

## Status

**Done (2026-11-06), on the fake engine and mocks** (no paid call in this epic, per the user).
- **Field roles and views in the design** (`AppEntityDesign`: `view`, `detailView`, `roles`, `filtersStyle`; one place
  for apps and areas, not `AppEntity.view` as planned). Code checks each role against the field's type (an image for
  `media`/`avatar`, a number for `stat`/`price`, a name or a parent for `title`), keeps a field in one role (title,
  media, avatar, price, stat, badge, subtitle, meta, in that order) and fills the media from the first image.
- **Kit** (`views.tsx`): `MediaGrid`, `Feed`, `RoleCards`, placeholders in the title's colour (never a broken image),
  `RecordsView` dispatch; tables and plain cards stay the AppList's; `AppDetail` gains the `media` and `profile` details.
  Every view presents the same AppList section (operation, params, row actions, `allowedActions`).
- Feeds read newest first: code adds the date sort to the list (`list_features`) and the kit asks for `-<date>`.
- Verified: `tests/test_app_design.py`, the golden apps' builds on mocks (news feed as a feed, video library and
  courses as media grids, 0 design-check failures at 1440 px light).

Deviations: found on the golden apps, a parent's foreign key may be a title (a bookmark titled by its post); the design
check ran at 1440 px light only (375 px and dark wait for the final sweep with the user's real test).
