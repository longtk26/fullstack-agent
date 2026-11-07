# Story 23.13 — The requirement's own look comes first

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37 · **Depends on:** 23.6, 23.7

## User story

As the user, when my requirement says how the app should look (its colours, light or dark, the kind of headings,
the corners, photos first), I want the generated app to look that way, not like the design data's default for the
kind of product it resembles.

## Why

Real drafts (2026-11-07) followed only the style words code recognises (`style_words`: a recipe name). The colours
always came from the design data's product match, which can be wrong: a requirement asking for a "warm" app got the
blue of a messaging product. A requirement naming "a bright orange accent on white", "a cream background and deep
brown text" or "a dark theme with an electric magenta accent" got none of it, and "photo-first" depended on the
model picking image views. A requirement in another language has no words for code to match.

## Approach

- The draft writes what the requirement says about the look as values, in `app.design.requested`
  (`AppRequestedStyle`): `accent`, `background`, `text` (`#rrggbb`), `scheme` (`light` | `dark`), `headingFont`
  (`serif`, `sans`, `geometric`, `rounded`, `display`, `mono`), `corners` (`sharp`, `rounded`, `pill`), `photos`
  (`prominent`) and `words` (the requirement's own words). Only what it states. The model reads the requirement in any
  language; prompt `draft_app@v5` adds one bullet to v4.
- Code checks each value (`complete_design`: a value that does not fit is left out with a note) and applies them over
  the design data's choice (`frontend/app/requested.py`, before the screens are planned): the accent becomes the
  primary (the kit's accent token is only a tint), the surfaces follow the background, `fix_contrast` keeps the text
  and buttons readable (a note says when it adjusted a colour), a heading face of the asked kind replaces one that is
  not, the corners set the radius, and `photos: prominent` shows every entity with an image as a media grid with a
  large image first (a board, a calendar or a feed keeps its view). One draft note says what was followed.
- The review's design panel shows "From the requirement": the words, the colours as swatches and the other values.
- `kit_design` leaves `requested` out of `app.json` (the theme and the views already carry it).

## Acceptance criteria

- [x] A requirement's colours, scheme, heading kind, corners and photo prominence reach the theme and the views, with
      readable contrast (tests on synthetic outlines: orange on white, cream and brown with serif headings, a dark
      theme; nothing requested changes nothing; values that do not fit are left out with a note).
- [x] Prompt snapshots: v5 is v4 plus the bullet; the older versions change only in the shared schema digest.
- [ ] A real draft follows its requirement's look (the bakery wholesale requirement: cream, deep brown, serif, photos).
- [ ] A Japanese requirement's look is followed too (the dental clinic: white and pale mint, soft rounded corners).

## Status

**Implemented (2026-11-07); the real drafts are next.** Known limit: no condensed face is bundled, so "bold condensed
headings" get the closest kind the model picks; adding one means a new font in the base (`make frontend-base`).
